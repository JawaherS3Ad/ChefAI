# -*- coding: utf-8 -*-
# الملف: chef_backend/langgraph_core.py
from __future__ import annotations

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

# وكلاؤنا/أدواتنا القائمة (نعتمد على الملفات الموجودة لديك)
from .agents import analyze_image_api  # يغلّف vision_agent.analyze_fridge_image
from .recipe_generator import generate_recipe
from .shopping_integration import get_shopping_suggestions
from .utils import parse_vision_json, normalize_ar_basic
from .ontology import EN2AR, is_bucket, normalize_ar, UNIT_FALLBACK

# -----------------------------
# 1) حالة النظام (مرنة/اختيارية المفاتيح)
# -----------------------------
class ChefState(TypedDict, total=False):
    session_id: str
    image_base64: str

    # Vision
    vision_raw: Any
    ingredients_raw: List[Dict[str, Any]]

    # Orchestrator prep
    items_clean: List[Dict[str, Any]]
    used_items: List[Dict[str, Any]]
    uncertain_items: List[Dict[str, Any]]

    # Preferences & policy
    preferences: Dict[str, Any]
    policy: Dict[str, Any]

    # Recipe & post-processing
    recipe: Dict[str, Any]
    missing_items: List[str]
    shopping_suggestions: List[Dict[str, Any]]

    # Final
    final_payload: Dict[str, Any]

# -----------------------------
# 2) إعدادات مساعدة
# -----------------------------
CONFIDENCE_THRESHOLD: float = 0.5

def _split_used_uncertain(items: List[Dict[str, Any]], thr: float):
    used, uncertain = [], []
    for it in items:
        conf = float(it.get("confidence") or 0.0)
        (used if conf >= thr else uncertain).append(it)
    return used, uncertain

def _merge_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ادمج عناصر بنفس الاسم (بعد تطبيع العربي)، واجمع الكميات وخذ أعلى ثقة."""
    merged: Dict[str, Dict[str, Any]] = {}
    for it in items:
        name_ar = normalize_ar(it.get("name_ar") or "")
        if not name_ar:
            name_ar = (it.get("name_en") or "").strip().lower()
        key = name_ar or "unknown"

        try:
            qty = int(it.get("quantity_estimate") or 1)
        except Exception:
            qty = 1

        unit = it.get("unit") or UNIT_FALLBACK
        conf = float(it.get("confidence") or 0.0)

        prev = merged.get(key)
        if prev:
            prev["quantity_estimate"] += max(1, qty)
            prev["confidence"] = max(prev["confidence"], conf)
            for k in ("state", "category", "name_en", "name_ar"):
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

def _sanitize_items(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """يحذف السلال العامة، يكمّل العربي من الإنجليزي، يفرض وحدة افتراضية، ثم يدمج."""
    cleaned = []
    for it in raw_items or []:
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

def _ensure_min_used(used: List[Dict[str, Any]], uncertain: List[Dict[str, Any]], k: int = 3):
    """لو العناصر المعتمدة قليلة، نرفع أعلى غير مؤكدة حتى نصل للحد الأدنى."""
    if len(used) >= k or not uncertain:
        return used, uncertain
    uncertain_sorted = sorted(uncertain, key=lambda x: float(x.get("confidence", 0.0)), reverse=True)
    need = max(0, k - len(used))
    used += uncertain_sorted[:need]
    uncertain = uncertain_sorted[need:]
    return used, uncertain

def _apply_policy(ingredients: List[Dict[str, Any]], preferences: Dict[str, Any]) -> Dict[str, Any]:
    """سياسات العجين والوقت… (مطابقة لما في orchestrator)."""
    return {
        "forbid_generic_dough": True,
        "require_baking_basics_for_dough": any("دقيق" in (it.get("name_ar") or "") for it in ingredients) \
                                           and any("ماء" in (it.get("name_ar") or "") for it in ingredients) \
                                           and any("خميرة" in (it.get("name_ar") or "") for it in ingredients),
        "max_missing": 3,
        "time_limit": (preferences or {}).get("time_limit"),
    }

def _similar(a: str, b: str) -> float:
    a = normalize_ar_basic(a)
    b = normalize_ar_basic(b)
    if not a or not b:
        return 0.0
    common = sum(1 for ch in set(a) if ch in b)
    return common / max(len(set(a)), len(set(b)))


def _estimate_missing(available_used: List[Dict[str, Any]], recipe_ingredients: List[str]) -> List[str]:
    avail = [normalize_ar_basic(it.get("name_ar", "")) for it in (available_used or [])]
    missing = []
    for need in recipe_ingredients or []:
        base = normalize_ar_basic(need)
        # موجود إذا أي عنصر متاح يتشابه ≥ 0.75
        present = any(_similar(base, a) >= 0.75 for a in avail if a)
        if not base or not present:
            missing.append(need)
    return missing


# -----------------------------
# 3) عقد الرسم البياني
# -----------------------------


def node_vision(state: ChefState) -> ChefState:
    print(f"🔹 [DEBUG] Executing node: analyze_ingredients")
    try:
        vision_raw = analyze_image_api(state["image_base64"], state.get("session_id", ""))
        if not vision_raw:
            vision_raw = {"ingredients": []}
    except Exception as e:
        print(f"⚠️ Vision agent failed: {e}")
        vision_raw = {"ingredients": []}

    # ✅ فحص عدم وجود مكونات
    if not vision_raw.get("ingredients"):
        return {"vision_raw": vision_raw, "error": "لم يتم اكتشاف أي مكونات. يرجى رفع صورة واضحة للثلاجة."}

    if not vision_raw or len(vision_raw.get("ingredients", [])) == 0:
        return {"error": "لم يتم اكتشاف أي مكونات. يرجى رفع صورة واضحة للثلاجة."}
    
    return {"vision_raw": vision_raw}




def node_namefixer(state: ChefState) -> ChefState:
    print(f"🔹 [DEBUG] Executing node: node_namefixer")
    """NameFixer خفيف: يضمن تعبئة العربية من EN2AR عند اللزوم."""
    parsed = parse_vision_json(state["vision_raw"])
    items = parsed.get("ingredients", []) or []
    for it in items:
        if not (it.get("name_ar") or "").strip():
            en = (it.get("name_en") or "").strip().lower()
            if en in EN2AR:
                it["name_ar"] = EN2AR[en]
            else:
                it["name_ar"] = it.get("name_en") or ""
    return {"ingredients_raw": items}

def node_prepare(state: ChefState) -> ChefState:
    print(f"🔹 [DEBUG] Executing node: node_prepare")
    """تنظيف + دمج + تقسيم ثقة + سياسة."""
    items_clean = _sanitize_items(state["ingredients_raw"])
    used, uncertain = _split_used_uncertain(items_clean, CONFIDENCE_THRESHOLD)
    used, uncertain = _ensure_min_used(used, uncertain, k=3)
    prefs = state.get("preferences", {}) or {}
    policy = _apply_policy(used, prefs)
    return {
        "items_clean": items_clean,
        "used_items": used,
        "uncertain_items": uncertain,
        "policy": policy,
        "preferences": prefs,
    }

def node_generate_recipe(state: ChefState) -> ChefState:
    print(f"🔹 [DEBUG] Executing node: node_generate_recipe")
    if state.get("error"):  # ✅ لو في خطأ سابق، لا نولد وصفة
        return {"recipe": {}}
    payload = {
        "ingredients": state.get("used_items", []),
        "preferences": state.get("preferences", {}),
        "policy": state.get("policy", {}),
    }
    suggested = generate_recipe(payload)
    recipe_dict = suggested.model_dump()
    return {"recipe": recipe_dict}

def node_missing_and_shop(state: ChefState) -> ChefState:
    print(f"🔹 [DEBUG] Executing node: node_missing_shopping")
    if state.get("error"):  # ✅ لو في خطأ، ما في نواقص/تسوّق
        return {"missing_items": [], "shopping_suggestions": []}
    needed = (state.get("recipe") or {}).get("ingredients_needed") or []
    missing = _estimate_missing(state.get("used_items", []), needed)
    shop = get_shopping_suggestions(missing)
    return {"missing_items": missing, "shopping_suggestions": shop}

def node_assemble(state: ChefState) -> ChefState:
    print(f"🔹 [DEBUG] Executing node: node_assemble_result")
    
    # لو في error رجّع رسالة واضحة
    if "error" in state:
        final = {"error": state["error"]}
        return {"final_payload": final}
    
    # باقي الحقول المعتادة
    final = {
        "detected_ingredients": {
            "used": state.get("used_items", []),
            "uncertain": state.get("uncertain_items", []),
            "notes": state.get("vision_notes", "")
        },
        "preferences": state.get("preferences", {}),
        "policy": state.get("policy", {}),
        "suggested_recipe": state.get("recipe", {}),
        "missing_items": state.get("missing_items", []),  # ✅ عدّلناها
        "shopping_suggestions": state.get("shopping_suggestions", []),  # ✅ عدّلناها
        "meta": {"confidence_threshold": CONFIDENCE_THRESHOLD},
    }
    return {"final_payload": final}


    final = {
        "detected_ingredients": {
            "used": state.get("used_items", []),
            "uncertain": state.get("uncertain_items", []),
        },
        "preferences": state.get("preferences", {}),
        "policy": state.get("policy", {}),
        "suggested_recipe": state.get("recipe", {}),
        "missing_items": state.get("missing_items", []),
        "shopping_suggestions": state.get("shopping_suggestions", []),
        "meta": {"confidence_threshold": CONFIDENCE_THRESHOLD},
    }
    return {"final_payload": final}


# -----------------------------
# 4) بناء وتجميع الرسم البياني
# -----------------------------
def create_chef_graph():
    g = StateGraph(ChefState)

    # nodes
    g.add_node("vision", node_vision)
    g.add_node("namefixer", node_namefixer)
    g.add_node("prepare", node_prepare)
    g.add_node("generate", node_generate_recipe)
    g.add_node("post", node_missing_and_shop)
    g.add_node("assemble", node_assemble)

    # flow
    g.set_entry_point("vision")
    g.add_edge("vision", "namefixer")
    g.add_edge("namefixer", "prepare")
    g.add_edge("prepare", "generate")
    g.add_edge("generate", "post")
    g.add_edge("post", "assemble")
    g.add_edge("assemble", END)

    return g.compile()

# نسخة جاهزة للاستخدام في FastAPI
chef_graph = create_chef_graph()
