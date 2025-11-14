# -*- coding: utf-8 -*-
"""
namefixer_agent:
-----------------
وكيل متخصص في توحيد أسماء المكونات القادمة من Vision Agent.

المهام:
1. استخدام القواميس: EN2AR + ZH2AR (عبر lookup_to_ar)
2. إذا لم تتوفر نتيجة → استخدام LLM للترجمة (اختياري)
3. تنظيف وتطبيع name_ar
4. إضافة metadata: _translated_by = dict / llm / passthrough / bucket

هذا الوكيل يعمل فقط داخل Step1 Orchestrator.
"""

import os
from typing import List, Dict, Any

from langchain_core.messages import HumanMessage

# LLM (اختياري)
try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None

# أدوات وبيانات
from .ontology import lookup_to_ar, is_bucket, normalize_ar
from .utils import normalize_ar_basic

# إعدادات عامة
NAMEFIXER_MODEL = os.getenv("NAMEFIXER_MODEL", "qwen/qwen-2.5-72b-instruct:free")
LLM_ENABLED = bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"))

_llm_client = None


# -------------------------------------------------------------
#  تهيئة LLM
# -------------------------------------------------------------
def _get_llm():
    """تهيئة LLM واحد فقط (Singleton)"""
    global _llm_client
    if _llm_client is None and ChatOpenAI is not None and LLM_ENABLED:
        _llm_client = ChatOpenAI(
            model=NAMEFIXER_MODEL,
            temperature=0,
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        )
    return _llm_client


def _translate_with_llm(name: str) -> str:
    """ترجمة احترافية عبر LLM في حال فشل القواميس."""

    llm = _get_llm()
    if not llm:
        return name

    prompt = (
        "ترجم اسم المكون التالي من أي لغة (إنجليزي/صيني) إلى العربية الفصحى فقط.\n"
        "بدون شرح، بدون تنسيق، بدون transliteration.\n"
        f"الاسم المطلوب ترجمته: {name}"
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        out = (getattr(response, "content", None) or "").strip()
        return out or name
    except Exception:
        return name


# -------------------------------------------------------------
#  معالجة عنصر واحد
# -------------------------------------------------------------
def _fix_single_item(item: Dict[str, Any]) -> Dict[str, Any]:
    it = dict(item)

    en = (it.get("name_en") or "").strip()
    zh = (it.get("name_zh") or en).strip()
    ar = (it.get("name_ar") or "").strip()

    # 1) bucket → نرجعه كما هو
    if is_bucket(en, ar):
        it["_translated_by"] = "bucket"
        return it

    # 2) إذا عربي جاهز
    if ar:
        it["name_ar"] = normalize_ar(ar)
        it["_translated_by"] = "passthrough"
        return it

    # 3) جرّب قاموس lookup (يعتمد على EN2AR و ZH2AR)
    mapped = lookup_to_ar(name_en=en, name_zh=zh, fallback=None)
    if mapped:
        it["name_ar"] = normalize_ar(mapped)
        it["_translated_by"] = "dict"
        return it

    # 4) fallback LLM فقط لو فشل كل شيء
    guess = _translate_with_llm(en or zh)

    # ✨ مهم: normalize_ar (وليس normalize_ar_basic)
    # لأننا نريد اسمًا عربيًا طبيعيًا، وليس نسخة مبسّطة للمقارنة
    it["name_ar"] = normalize_ar(guess)
    it["_translated_by"] = "llm"
    return it


# -------------------------------------------------------------
#  الواجهة الرئيسية
# -------------------------------------------------------------
def fix_ingredients_names(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    يعالج قائمة عناصر Vision ويعيدها مع name_ar موحّد.
    """
    fixed = []

    for it in items or []:
        # إن لم يوجد name_zh → نستخدم name_en (الذي أحياناً يحتوي صيني)
        if "name_zh" not in it:
            it["name_zh"] = it.get("name_en", "")

        fixed.append(_fix_single_item(dict(it)))

    return fixed
