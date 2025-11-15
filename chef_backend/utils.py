# -*- coding: utf-8 -*-
import json
import re
from typing import Any, Dict


# =====================================================================
# 1) parse_vision_json
# =====================================================================
def parse_vision_json(raw: str | Dict[str, Any]) -> Dict[str, Any]:
    """
    يحوّل خرج وكيل الرؤية إلى dict مضمون،
    حتى لو النموذج رجّع JSON داخل نص أو بين أسوار.
    """

    if isinstance(raw, dict):
        raw.setdefault("ingredients", [])
        raw.setdefault("notes", "")
        return raw

    text = str(raw or "").strip()

    # إزالة أسوار الأكواد
    text = re.sub(r"```(json)?", "", text).replace("```", "").strip()

    # محاولة استخراج JSON في النص
    try:
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            data = json.loads(text[first:last + 1])
            if isinstance(data, dict):
                data.setdefault("ingredients", [])
                data.setdefault("notes", "")
                return data
    except Exception:
        pass

    # محاولة JSON كامل
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data.setdefault("ingredients", [])
            data.setdefault("notes", "")
            return data
    except Exception:
        pass

    return {"ingredients": [], "notes": text}


# =====================================================================
# 2) normalize_ar_basic
# =====================================================================
def normalize_ar_basic(text: str) -> str:
    """تطبيع مبسط للنص العربي للمقارنة فقط."""
    if not text:
        return ""
    text = re.sub(r"[^\w\u0600-\u06FF\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه").replace("ى", "ي")
    return text.strip().lower()


# =====================================================================
# 3) NEW — mapping time_limit مباشرة من الواجهة (٣ قيم فقط)
# =====================================================================
def map_ui_time_to_minutes(time_limit: str | None) -> int:
    """
    يحوّل خيار الوقت من واجهة المستخدم إلى رقم دقائق.

    الواجهة تحتوي على ٣ خيارات فقط:
        - "Under 5 min"
        - "min 30"
        - "Over 30 min"
    """

    if not time_limit:
        return 30  # default

    t = time_limit.strip().lower()

    if "under" in t and "5" in t:
        return 5

    if "30" in t and ("min" in t or "30min" in t or "min 30" in t):
        return 30

    if "over" in t or ">" in t:
        return 45  # يمكنك تغييره لـ 60 لو تبغى

    # fallback منطقي
    return 30

# =====================================================================
# 4) map_servings — تحويل نص الواجهة إلى رقم منطقي
# =====================================================================
def map_servings(ui_value):
    """
    يقبل القيم من الفرونت سواء كانت:
    - رقم (2, 3, 4)
    - أو نص ("2 people")
    ويرجع قيمة servings رقمية متوافقة مع الباك.
    """

    if ui_value is None:
        return None

    # 🔥 إذا وصل رقم من الفرونت → نحوله لنص مثل "2 people"
    if isinstance(ui_value, (int, float)):
        ui_value = f"{int(ui_value)} people"

    # الآن نضمن أن ui_value نص، ونكمل المنطق الأصلي
    ui_value = str(ui_value)
    t = ui_value.strip().lower()

    # المنطق الأصلي كما هو (لا نغيّره)
    if t.isdigit():
        return int(t)

    # يحاول استخراج أرقام من نص مثل "serve 2", "for 3 people"
    for token in t.split():
        if token.isdigit():
            return int(token)

    return None
