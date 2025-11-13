import os
import base64
import io
from PIL import Image
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def _image_part(image: str):
    """
    تحويل الصورة إلى صيغة مناسبة للإرسال
    image قد يكون:
    1) base64 ببادئة data:image
    2) base64 خام بدون بادئة
    3) رابط http/https
    4) مسار ملف محلي
    """
    # 🧠 الحالة 1: data:image
    if image.startswith("data:image"):
        return {"type": "image_url", "image_url": image}

    # 🧠 الحالة 2: base64 خام (من Swagger)
    if len(image) > 500 and not os.path.exists(image) and not image.startswith("http"):
        # نضيف البادئة المناسبة
        return {"type": "image_url", "image_url": f"data:image/png;base64,{image}"}

    # 🧠 الحالة 3: رابط
    if image.startswith("http://") or image.startswith("https://"):
        return {"type": "image_url", "image_url": image}

    # ✅ إصلاح سريع: لو النص Base64 خام بدون data:image
    if len(image) > 500 and not os.path.exists(image):
        return {"type": "image_url", "image_url": f"data:image/png;base64,{image}"}


    # 🧠 الحالة 4: ملف محلي
    with open(image, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = "jpeg" if image.lower().endswith((".jpg", ".jpeg")) else "png"
    return {"type": "image_url", "image_url": f"data:image/{ext};base64,{b64}"}


# البرومبت المحسّن والدقيق
PROMPT_VISION = (
    """
你是一位精确的食材视觉助手。你将收到一张冰箱或食材的图片。你的主要目标是准确识别所有可食用项，并严格遵守 JSON 输出格式。

【严格规则】
1. **只输出 JSON**。不要添加任何解释、代码块或多余的文字。
2. **只包括可食用的项目**（忽略包装、容器、架子）。
3. **输出最多 10 个项目**，优先选择蛋白质、淀粉和主要蔬菜。
4. **必须使用 Pydantic Schema 的字段和类型**。
5. **语言要求：** "name_en" 字段必须使用**中文**（例如 '番茄', '鸡蛋', '黄瓜'）**，
但请仍然将所有项目放在顶级 JSON 字段 "ingredients" 中。
6. **置信度：** 如果不确定（例如 العناصر مخفية أو غير واضحة），请设置 "confidence" 低于 0.5。

【输出 JSON 字段和约束】
对于每个食材，请提供以下字段，字段名和类型必须严格遵守：
- "name_en": 具体的英文名称（例如 'green bell pepper', 'egg'）
- "name_ar": **空字符串 ""**（由下游代理处理）
- "quantity_estimate": 大致数量 (int)
- "unit": 单位（例如 'piece', 'bundle', 'gram'）
- "state": 状态（例如 'fresh', 'cooked', 'canned'）
- "category": 类别（例如 'vegetable', 'fruit', 'protein'）
- "confidence": 置信度 (0.0 到 1.0)
- "inferred": 布尔值（如果项目在封闭包装中则为 true）

【输出 JSON 示例 - 严格遵守此格式】
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
      "name_en": "eggs",
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

请现在输出 JSON。
"""
)





def analyze_fridge_image(image: str) -> str:
    """
    يحلل صورة (مثلاً ثلاجة أو مكونات)
    ويستخرج قائمة المكونات الظاهرة فيها بصيغة JSON منظمة.
    
    Args:
        image: مسار الصورة (ملف محلي، رابط URL، أو base64)
    
    Returns:
        نص JSON يحتوي على المكونات المكتشفة
    """
    llm = ChatOpenAI(
    model="qwen/qwen2.5-vl-32b-instruct:free",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.environ["OPENAI_API_KEY"],
    temperature=0.2,
    max_tokens=900,  # ✅ رجّعناه هنا عادي ورفعنا الحد
    model_kwargs={
        "response_format": {"type": "json_object"}  # ✅ بقي هنا فقط
    },
)


    
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": PROMPT_VISION},
            _image_part(image),
        ],
    }]
    
    try:
        result = llm.invoke(messages)
        return result.content if hasattr(result, "content") else result
    except Exception as e:
        if "LengthFinishReasonError" in str(type(e)):
            print("⚠️ النموذج تجاوز الحدّ – سيتم قص الناتج وإصلاح JSON تلقائيًا.")
            partial = getattr(e, "completion", None)
        if partial and hasattr(partial, "choices"):
            text = partial.choices[0].message.get("content", "")
            # نحاول استخراج JSON صالح
            from chef_backend.utils import parse_vision_json
            return parse_vision_json(text)
    raise

# مثال اختبار محلي
if __name__ == "__main__":
    print("🔹 اختبار نموذج الرؤية (Qwen2.5-VL)...\n")
    ingredients_text = analyze_fridge_image("example_fridge.jpg")
    print("المكونات المكتشفة:", ingredients_text)


def analyze_and_suggest(image: str):
    """
    يحلل الصورة أولاً ثم يولد وصفة
    
    Args:
        image: مسار الصورة (ملف محلي، رابط URL، أو base64)
    """
    ingredients_text = analyze_fridge_image(image)
    print("🔹 المكونات المكتشفة:", ingredients_text)
