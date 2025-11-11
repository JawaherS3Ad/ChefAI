# -*- coding: utf-8 -*-
"""
Orchestrator: يربط رؤية الصورة ← استخراج المكونات ← توليد الوصفة
- تصفية المكونات حسب الثقة (threshold = 0.5)
- حساب العناصر الناقصة بشكل مبسّط
- تخزين النتيجة في cache/
- Logs عربية ملوّنة لسهولة التتبع
- مُهيّأ مستقبلاً للتحويل إلى LangGraph (Nodes/Edges)
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# وكلاؤنا
from chef_backend.vision_agent import analyze_fridge_image
from chef_backend.recipe_generator import generate_recipe
from chef_backend.ontology import is_bucket, normalize_ar, EN2AR, UNIT_FALLBACK
from chef_backend.shopping_integration import get_shopping_suggestions

# -----------------------------
# إعدادات عامة
# -----------------------------
CONFIDENCE_THRESHOLD = 0.5
CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# ألوان بسيطة للّوجز (ANSI)
C = {
    "blue": "\033[94m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "reset": "\033[0m",
    "bold": "\033[1m",
}

# قاموس ترجمة بسيط (fallback للعرض)
EN_AR_DICT = {
    "tomato": "طماطم",
    "green bell pepper": "فلفل أخضر",
    "red bell pepper": "فلفل أحمر",
    "broccoli": "بروكلي",
    "green beans": "فاصوليا خضراء",
    "potato": "بطاطس",
    "egg": "بيض",
    "beef cubes": "لحم مقطّع",
    "minced beef": "لحم مفروم",
    "chicken breast": "صدر دجاج",
    "ketchup": "كاتشب",
    "mustard": "خردل",
    "tomato sauce": "صلصة طماطم",
    "yogurt": "زبادي",
    "cucumber": "خيار",
    "lettuce": "خس",
    "carrot": "جزر",
    "onion": "بصل",
}

# -----------------------------
# أدوات مساعدة
# -----------------------------
def _parse_vision_output(raw: str | Dict[str, Any]) -> Dict[str, Any]:
    """يحوّل خرج وكيل الرؤية (نص/JSON) إلى dict مضمون حتى لو كان داخل ```json ...```."""
    if isinstance(raw, str) and len(raw) > 20000:
        raw = raw[:20000]

    if isinstance(raw, dict):
        return raw

    text = str(raw).strip()

    # 1) إزالة أسوار الأكواد (``` ... ```)
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # 2) محاولة التقاط أكبر كتلة JSON
    try:
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            candidate = text[first:last+1]
            return json.loads(candidate)
    except Exception:
        pass

    # 3) محاولة مباشرة
    try:
        return json.loads(text)
    except Exception:
        return {"ingredients": [], "notes": text}


def _normalize_name(name_ar: str) -> str:
    """تطبيع بسيط لاسم المكوّن للمقارنة."""
    name = re.sub(r"\(.*?\)", "", name_ar or "")
    name = re.sub(r"[^\w\u0600-\u06FF\s]", "", name)
    return re.sub(r"\s+", " ", name).strip().lower()


def _split_used_uncertain(items: List[Dict[str, Any]], thr: float) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """تقسيم المكونات حسب عتبة الثقة."""
    used, uncertain = [], []
    for it in items:
        conf = float(it.get("confidence", 0.0) or 0.0)
        (used if conf >= thr else uncertain).append(it)
    return used, uncertain


def _merge_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ادمج العناصر المتطابقة (بعد تطبيع الاسم العربي)، واجمع الكميات وخذ أعلى ثقة."""
    merged = {}
    for it in items:
        name_ar = normalize_ar(it.get("name_ar") or "")
        if not name_ar:
            name_ar = (it.get("name_en") or "").strip().lower()
        key = name_ar or "unknown"

        qty = int(it.get("quantity_estimate") or 1)
        unit = it.get("unit") or UNIT_FALLBACK
        conf = float(it.get("confidence") or 0.0)

        prev = merged.get(key)
        if prev:
            prev["quantity_estimate"] += max(1, qty)
            prev["confidence"] = max(prev["confidence"], conf)
            # احتفظ بأول قيم غير فارغة
            for k in ("state", "category"):
                if not prev.get(k) and it.get(k):
                    prev[k] = it[k]
            prev["inferred"] = prev.get("inferred", False) or bool(it.get("inferred", False))
        else:
            it2 = dict(it)
            it2["name_ar"] = normalize_ar(it2.get("name_ar") or "")
            if not it2["name_ar"] and it2.get("name_en"):
                it2["name_ar"] = EN2AR.get(it2["name_en"].strip().lower(), it2["name_ar"])
            it2["unit"] = unit
            it2["quantity_estimate"] = max(1, qty)
            it2["confidence"] = conf
            merged[key] = it2
    return list(merged.values())


def sanitize_items(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """يحذف السلال العامة، يكمّل العربي من الإنجليزي، يفرض وحدة افتراضية، ثم يدمج التكرارات."""
    cleaned = []
    for it in raw_items:
        name_en = (it.get("name_en") or "").strip()
        name_ar = (it.get("name_ar") or "").strip()
        if is_bucket(name_en, name_ar):
            continue
        if not name_ar and name_en:
            ar = EN2AR.get(name_en.lower(), "")
            if ar:
                it["name_ar"] = ar
        if not it.get("unit"):
            it["unit"] = UNIT_FALLBACK
        cleaned.append(it)
    return _merge_items(cleaned)


def _estimate_missing(available_used: List[Dict[str, Any]], recipe_ingredients: List[str]) -> List[str]:
    """مقارنة بسيطة: إن لم يوجد المكوّن باسمه (بعد التطبيع) ضمن المتاح → اعتبره ناقصاً."""
    available_names = {_normalize_name(it.get("name_ar", "")) for it in available_used}
    missing = []
    for needed in recipe_ingredients or []:
        base = _normalize_name(needed)
        if not base or all((base not in n and n not in base) for n in available_names):
            missing.append(needed)
    return missing


def _save_cache(payload: Dict[str, Any]) -> str:
    """حفظ النتيجة في ملف JSON بالكاش."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = CACHE_DIR / f"run_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)


def _fill_missing_ar_names(items: List[Dict[str, Any]]) -> None:
    """لو العربي فاضي نكمّله من EN_AR_DICT (fallback خفيف للعرض)."""
    for it in items:
        name_ar = (it.get("name_ar") or "").strip()
        if not name_ar:
            en = (it.get("name_en") or "").strip().lower()
            if en in EN_AR_DICT:
                it["name_ar"] = EN_AR_DICT[en]
            else:
                it["name_ar"] = it.get("name_en") or ""


# -----------------------------
# سياسات "العجين" والقواعد الإضافية
# -----------------------------
def _has_baking_basics(items: List[Dict[str, Any]]) -> bool:
    """تحقق من توفر مكونات الخبز الأساسية (دقيق + ماء + خميرة)."""
    names = {(it.get("name_ar") or "").strip() for it in items}
    return any("دقيق" in n for n in names) and any("ماء" in n for n in names) and any("خميرة" in n for n in names)


def apply_recipe_policy(payload: Dict[str, Any]) -> Dict[str, Any]:
    """تطبيق سياسات الوصفة (منع العجين العام، الحد الأقصى للمكونات الناقصة، إلخ)."""
    prefs = payload.get("preferences") or {}
    payload["policy"] = {
        "forbid_generic_dough": True,
        "require_baking_basics_for_dough": _has_baking_basics(payload.get("ingredients", [])),
        "max_missing": 3,
        "time_limit": prefs.get("time_limit"),
    }
    return payload


# -----------------------------
# الواجهة الرئيسية للأوركستريتور
# -----------------------------
def process_recipe_request(
    image: str,
    *,
    meal_type: str | None = None,
    time_limit: str | None = None,
    servings: int | None = None,
    cuisines: List[str] | None = None
) -> Dict[str, Any]:
    """
    يدير التدفق الكامل: صورة → مكونات (مصفّاة) → وصفة → نواقص → JSON نهائي.
    
    Args:
        image: مسار صورة / رابط / base64 (مدعوم في vision_agent)
        meal_type, time_limit, servings, cuisines: تفضيلات المستخدم (اختيارية)
    
    Returns:
        dict منظم جاهز للـ Frontend
    """
    
    print(f"{C['blue']}{C['bold']}🧠 المرحلة 1: تحليل الصورة واستخراج المكونات...{C['reset']}")
    vision_raw = analyze_fridge_image(image)
    from chef_backend.utils import parse_vision_json
    vision = parse_vision_json(vision_raw)


    items = vision.get("ingredients", []) or []
    # اكتمال العربي من القاموس عند الحاجة
    _fill_missing_ar_names(items)
    # تنظيف/دمج/توحيد
    items = sanitize_items(items)
    # تقسيم حسب الثقة (low-conf تروح لقائمة uncertain)
    used_items, uncertain_items = _split_used_uncertain(items, CONFIDENCE_THRESHOLD)

    # fallback بسيط لو used قليلة جدًا
    if len(used_items) < 3 and uncertain_items:
        uncertain_sorted = sorted(uncertain_items, key=lambda x: float(x.get("confidence", 0.0)), reverse=True)
        need = max(0, 3 - len(used_items))
        used_items += uncertain_sorted[:need]
        uncertain_items = uncertain_sorted[need:]

    print(f"{C['green']}✅ اكتُشِف {len(items)} عنصرًا. المُعتمد: {len(used_items)}، غير المؤكد: {len(uncertain_items)}.{C['reset']}")

    # نبني حمولة المولّد + نحقن السياسة
    payload_for_recipe = {
        "ingredients": used_items,
        "preferences": {
            "meal_type": meal_type,
            "time_limit": time_limit,
            "servings": servings,
            "cuisines": cuisines,
        }
    }
    payload_for_recipe = apply_recipe_policy(payload_for_recipe)

    print(f"{C['blue']}{C['bold']}🍳 المرحلة 2: توليد الوصفة بناءً على المكونات والتفضيلات...{C['reset']}")
    suggested = generate_recipe(payload_for_recipe)  # Pydantic model
    recipe_dict = suggested.model_dump()

    print(f"{C['blue']}{C['bold']}🧮 المرحلة 3: حساب العناصر الناقصة...{C['reset']}")
    needed = recipe_dict.get("ingredients_needed") or []
    missing = _estimate_missing(used_items, needed)

    # 🛒 المرحلة 4: اقتراحات الشراء (HungryStation Placeholder)
    shopping_suggestions = get_shopping_suggestions(missing)

    # بناء النتيجة النهائية
    final = {
        "detected_ingredients": {
            "used": used_items,
            "uncertain": uncertain_items,
            "notes": vision.get("notes", "")
        },
        "preferences": payload_for_recipe["preferences"],
        "suggested_recipe": recipe_dict,
        "missing_items": missing,
        "shopping_suggestions": shopping_suggestions,
        "nutrition_info": None,
        "meta": {
            "confidence_threshold": CONFIDENCE_THRESHOLD,
            "cache_saved_at": None,
        }
    }

    cache_path = _save_cache(final)
    final["meta"]["cache_saved_at"] = cache_path

    if missing:
        print(f"{C['yellow']}⚠️ عناصر ناقصة: {len(missing)} — {', '.join(missing)}{C['reset']}")
    print(f"{C['green']}{C['bold']}🍽️ النتيجة النهائية جاهزة — حُفظت في: {cache_path}{C['reset']}")

    return final


    cache_path = _save_cache(final)
    final["meta"]["cache_saved_at"] = cache_path

    if missing:
        print(f"{C['yellow']}⚠️ عناصر ناقصة: {len(missing)} — {', '.join(missing)}{C['reset']}")
    print(f"{C['green']}{C['bold']}🍽️ النتيجة النهائية جاهزة — حُفظت في: {cache_path}{C['reset']}")

    return final

# -----------------------------
# واجهات LangGraph التوافقية (alias)
# -----------------------------
def analyze_image_api(image_base64: str, session_id: str):
    """واجهة بسيطة لتحليل الصورة (LangGraph-compatible)."""
    return analyze_fridge_image(image_base64)

def suggest_recipes_agent(ingredients_json: dict):
    """واجهة بسيطة لتوليد الوصفة (LangGraph-compatible)."""
    return generate_recipe(ingredients_json)

# -----------------------------
# اختبار محلي سريع
# -----------------------------
if __name__ == "__main__":
    # مثال تشغيل: مرّري صورة حقيقية لديك (ملف/رابط/بِـيس64)
    SAMPLE_IMAGE = "fridge.jpg"  # عدّليها إذا لزم
    result = process_recipe_request(
        SAMPLE_IMAGE,
        meal_type="Dinner",
        time_limit="30m",
        servings=2,
        cuisines=["Saudi", "Italian"]
    )
    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))