# -*- coding: utf-8 -*-
"""
vision_agent.py
---------------
وكيل الرؤية الرئيسي في ChefAI.

الفكرة:
- نستخدم نموذج Qwen-VL عبر OpenRouter
- نمرر برومبت صيني (لأن النموذج صيني ويكون أدق وأقل هلوسة)
- نطلب منه إخراج JSON منظم يحتوي قائمة ingredients + notes
- الإخراج يُمرر لاحقًا إلى:
    - parse_vision_json في utils
    - ثم NameFixer + Orchestrator في Step 1
"""

import os
import base64
from typing import Dict, Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


# -------------------------------------------------------------
#  تجهيز الصورة (URL / base64 / ملف محلي)
# -------------------------------------------------------------
def _image_part(image: str) -> Dict[str, Any]:
    """
    تحويل الصورة إلى صيغة مناسبة للإرسال إلى النموذج.
    image يمكن أن يكون:
    1) data:image base64
    2) base64 خام
    3) رابط http/https
    4) مسار ملف محلي
    """
    # حالة 1: data:image
    if image.startswith("data:image"):
        return {"type": "image_url", "image_url": image}

    # حالة 2: رابط
    if image.startswith("http://") or image.startswith("https://"):
        return {"type": "image_url", "image_url": image}

    # حالة 3: base64 خام (طويلة + ليست مسار)
    if len(image) > 500 and not os.path.exists(image):
        return {"type": "image_url", "image_url": f"data:image/png;base64,{image}"}

    # حالة 4: ملف محلي
    with open(image, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = "jpeg" if image.lower().endswith((".jpg", ".jpeg")) else "png"
    return {"type": "image_url", "image_url": f"data:image/{ext};base64,{b64}"}


# -------------------------------------------------------------
#  البرومبت الصيني
# -------------------------------------------------------------
PROMPT_VISION = """
你是一位精确的食材视觉助手。你将收到一张冰箱或食材的图片。你的主要目标是准确识别所有可食用项，并严格遵守 JSON 输出格式。

【严格规则】
1. 只输出 JSON。不要添加任何解释、代码块或多余的文字。
2. 只包括可食用的项目（忽略包装、容器、架子）。
3. 输出最多 10 个项目，优先选择蛋白质、淀粉和主要蔬菜。
4. 必须使用下面定义的字段和类型。
5. "name_en" 字段可以使用英文或中文食材名，但尽量使用模型最有信心的标注。
6. 置信度：如果不确定（例如食材被遮挡或很模糊），请设置 "confidence" 低于 0.5。

【输出 JSON 字段和约束】
对于每个食材，请提供以下字段：
- "name_en": 食材名称（如 "tomato" 或 "番茄"）
- "name_ar": 空字符串 ""（由下游代理处理）
- "quantity_estimate": 大致数量 (int)
- "unit": 单位（例如 "piece", "bundle", "gram"）
- "state": 状态（例如 "fresh", "cooked", "canned"）
- "category": 类别（例如 "vegetable", "fruit", "protein"）
- "confidence": 置信度 (0.0 到 1.0)
- "inferred": 布尔值（如果项目在封闭包装中则为 true）

【输出 JSON 示例】
{
  "ingredients": [
    {
      "name_en": "tomato",
      "name_ar": "",
      "quantity_estimate": 3,
      "unit": "piece",
      "state": "fresh",
      "category": "vegetable",
      "confidence": 0.92,
      "inferred": false
    },
    {
      "name_en": "egg",
      "name_ar": "",
      "quantity_estimate": 6,
      "unit": "piece",
      "state": "fresh",
      "category": "protein",
      "confidence": 0.95,
      "inferred": true
    }
  ],
  "notes": "short notes if needed"
}

请现在只输出 JSON。
"""


# -------------------------------------------------------------
#  وكيل الرؤية الأساسي
# -------------------------------------------------------------
def _get_vision_llm() -> ChatOpenAI:
    """
    تهيئة Qwen-VL عبر OpenRouter (أو المفتاح المتوفر).
    """
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("لم يتم ضبط OPENROUTER_API_KEY أو OPENAI_API_KEY في متغيرات البيئة.")

    llm = ChatOpenAI(
        model="qwen/qwen2.5-vl-32b-instruct:free",
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=api_key,
        temperature=0.2,
        max_tokens=900,
        model_kwargs={
            "response_format": {"type": "json_object"}
        },
    )
    return llm


def analyze_fridge_image(image: str):
    """
    يحلل صورة (ثلاجة/مكونات) ويعيد **نص JSON** أو كائن JSON من النموذج.
    هذا الناتج سيتكفّل به لاحقًا:
    - parse_vision_json في utils
    - ثم NameFixer + Orchestrator
    """
    llm = _get_vision_llm()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT_VISION},
                _image_part(image),
            ],
        }
    ]

    try:
        result = llm.invoke(messages)
        content = getattr(result, "content", None)
        return content if content is not None else result
    except Exception as e:
        print(f"⚠️ Vision model error: {e}")
        return '{"ingredients": [], "notes": "vision model failed"}'


# -------------------------------------------------------------
#  اختبار محلي بسيط
# -------------------------------------------------------------
if __name__ == "__main__":
    print("🔹 اختبار وكيل الرؤية (Qwen2.5-VL)...")
    sample_path = "example_fridge.jpg"
    out = analyze_fridge_image(sample_path)
    print(out)
