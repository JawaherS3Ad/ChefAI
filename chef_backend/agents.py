# -*- coding: utf-8 -*-
"""
agents.py — Adapter Layer فقط
------------------------------
طبقة وسيطة صغيرة وخفيفة.
لا يوجد هنا أي منطق Orchestration ولا تنظيف ولا دمج.

- VisionAdapter → يستدعي VisionAgent ويرجع raw output بشكل مضمون.
- NameFixerAdapter → يستدعي NameFixer بدون أي تجهيز إضافي.

جميع عمليات Step1 + Step2 تُدار بالكامل داخل langgraph_core.py.
"""

from __future__ import annotations
from typing import Dict, Any, List

from chef_backend.vision_agent import analyze_fridge_image
from chef_backend.namefixer_agent import fix_ingredients_names
from chef_backend.utils import parse_vision_json


# -------------------------------------------------------------
# Vision Adapter
# -------------------------------------------------------------
def analyze_image_api(image_base64: str, session_id: str) -> Dict[str, Any]:
    """
    غلاف آمن لاستدعاء VisionAgent.
    يرجع دائماً dict مضمون يحتوي:
    - ingredients: List
    - notes: str
    حتى لو فشل النموذج أو رجّع نص أو JSON غير مكتمل.
    """
    try:
        raw = analyze_fridge_image(image_base64)
    except Exception as e:
        print(f"⚠️ VisionAdapter Error: {e}")
        return {"ingredients": [], "notes": "Vision error"}

    # parse_vision_json يتكفل بكل الحالات:
    # - dict
    # - string json
    # - fenced codeblocks
    # - incomplete json
    parsed = parse_vision_json(raw)

    # تأكيد وجود الحقول
    parsed.setdefault("ingredients", [])
    parsed.setdefault("notes", "")

    return parsed


# -------------------------------------------------------------
# NameFixer Adapter
# -------------------------------------------------------------
def namefixer_api(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    غلاف بسيط لتشغيل NameFixer فقط.
    بدون Cleaning أو Merging أو إعادة هيكلة.
    """
    try:
        # NameFixer يتوقع name_en و name_zh على الأقل
        for it in items:
            if "name_zh" not in it:
                it["name_zh"] = it.get("name_en", "")

        return fix_ingredients_names(items)

    except Exception as e:
        print(f"⚠️ NameFixerAdapter Error: {e}")
        return items
