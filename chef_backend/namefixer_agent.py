# -*- coding: utf-8 -*-
"""
namefixer_agent: يعالج أسماء المكونات بين الرؤية والوصفة.
المنطق:
- جرّب القواميس (EN2AR + ZH2AR)
- إذا ما وجد ترجمة عربية، استخدم LLM للترجمة (اختياري، يعتمد على توفر المفاتيح)
- يعيد قائمة عناصر محدثة مع name_ar موحّد
"""

import os
from typing import List, Dict, Any

# نفس الـLLM المستخدمين عندكم (LangChain واجهة موحدة)
try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None  # لو غير متاح، نشتغل قاموس فقط

from .ontology import lookup_to_ar, is_bucket, normalize_ar
from .utils import normalize_ar_basic  # دالة تنظيف بسيطة لو عندكم

# إعدادات اختيارية للنموذج
NAMEFIXER_MODEL = os.getenv("NAMEFIXER_MODEL", "qwen/qwen-2.5-72b-instruct:free")  # غيّرها لو تبغى Qwen عبر OpenRouter
LLM_ENABLED = bool(os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"))

_llm_client = None
def _get_llm():
    global _llm_client
    if _llm_client is None and ChatOpenAI is not None and LLM_ENABLED:
        _llm_client = ChatOpenAI(model=NAMEFIXER_MODEL, temperature=0)
    return _llm_client

def _translate_with_llm(name: str) -> str:
    llm = _get_llm()
    if not llm:
        return name  # بدون LLM نعيد الاسم كما هو (سيُعالَج لاحقًا)
    prompt = f"""
أنت وكيل لغوي متخصص في ترجمة مكونات الطعام العالمية إلى العربية الفصحى.

🎯 الهدف:
تحويل أسماء المكونات التي تأتي من أنظمة رؤية (مثل "Vision Agent") إلى اسم عربي واضح،
مختصر، ودقيق من الناحية الغذائية.

⚙️ القواعد الإلزامية:
1. ترجم الاسم فقط إلى العربية الفصحى، بدون أي شرح أو توضيح إضافي.
2. لا تستخدم transliteration (لا تكتب الحروف الأجنبية بالعربية).
3. إذا الاسم بالصيني أو بالإنجليزية، فترجمه مباشرة إلى مكافئه العربي المعروف.
4. لا تضف أي رموز أو أقواس أو معاني فرعية.
5. الناتج يجب أن يكون كلمة واحدة أو كلمتين كحد أقصى (مثل "صدر دجاج" أو "فلفل رومي").
6. لو لم تعرف المعنى إطلاقًا، أعد الكلمة كما هي بدون تغيير.

📦 مثال:
输入 (input): "鸡蛋"
输出 (output): "بيض"

输入 (input): "green beans"
输出 (output): "فاصوليا خضراء"

输入 (input): "cheddar cheese"
输出 (output): "جبن شيدر"

الاسم المطلوب ترجمته: {name}
"""

    try:
        resp = llm.invoke(prompt)
        text = (getattr(resp, "content", None) or "").strip()
        return text or name
    except Exception:
        return name

def _fix_single_item(item: Dict[str, Any]) -> Dict[str, Any]:
    # حقول متوقعة من vision: name_en / name_ar / name_zh (اختياري) / confidence
    en = (item.get("name_en") or "").strip()
    zh = (item.get("name_zh") or "").strip()
    ar = (item.get("name_ar") or "").strip()

    # 1) إن كان bucket عام، لا نترجم له (يُعالج لاحقًا)
    if is_bucket(en, ar):
        return item

    # 2) إن كان name_ar موجود وواضح، طبّعه وأرجعه
    if ar:
        item["name_ar"] = normalize_ar(ar)
        return item

    # 3) جرّب lookup من القواميس (EN ثم ZH)
    mapped = lookup_to_ar(name_en=en, name_zh=zh, fallback="")
    if mapped:
        item["name_ar"] = normalize_ar(mapped)
        item["_translated_by"] = "dict"  # ← هنا يوضح أن الترجمة جاءت من القاموس
        return item

    # 4) لو ما وجد، جرّب LLM (إن متاح)
    guess = _translate_with_llm(en or zh)
    item["name_ar"] = normalize_ar_basic(normalize_ar(guess))
    item["_translated_by"] = "llm"  # ← هنا يوضح أن الترجمة جاءت من LLM
    return item


def fix_ingredients_names(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    يأخذ قائمة عناصر مثل:
    [{"name_en": "...", "name_zh": "...", "name_ar": "", "confidence": 0.83}, ...]
    ويعيدها مع name_ar ممتلئ ومطبّع قدر الإمكان.
    """
    fixed = []
    for it in items or []:
        fixed.append(_fix_single_item(dict(it)))
    return fixed
