import os
import base64
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

def _image_part(image: str):
    """
    تحويل الصورة إلى صيغة مناسبة للإرسال
    image قد يكون:
    1) base64 ببادئة data:image
    2) رابط http/https
    3) مسار ملف محلي
    """
    if image.startswith("data:image"):
        return {"type": "image_url", "image_url": image}
    if image.startswith("http://") or image.startswith("https://"):
        return {"type": "image_url", "image_url": image}
    # مسار محلي → حوله إلى base64
    with open(image, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = "jpeg" if image.lower().endswith((".jpg", ".jpeg")) else "png"
    return {"type": "image_url", "image_url": f"data:image/{ext};base64,{b64}"}

# البرومبت المحسّن والدقيق
PROMPT_VISION = (
    "You are a precise food vision assistant. You will be given ONE image of a fridge or ingredients.\n"
    "STRICT RULES:\n"
    "1) Output valid JSON ONLY. No explanations, no code fences, no prose.\n"
    "2) Include ONLY edible items (ignore shelves/containers as independent items).\n"
    "3) For each item, return BOTH English and Arabic names:\n"
    "   - name_en: REQUIRED, specific (e.g., 'green bell pepper', 'broccoli', 'beef cubes').\n"
    "   - name_ar: Arabic equivalent if confident, else empty string ''.\n"
    "4) If an item is inside a recognizable package (e.g., egg carton), set inferred=true and a suitable confidence.\n"
    "5) Fields per item: name_en, name_ar, quantity_estimate (int), unit ('حبة'/'حزمة'/'جم'/'مل'), "
    "   state ('طازج'/'مجمد'/'مطبوخ'/'مخلل'/'معلّب'), category ('خضار'/'فواكه'/'بروتين'/'نشويات'/'ألبان'/'بهارات'/'مشروبات'/'أخرى'), "
    "   confidence (0..1), inferred (bool).\n"
    "6) FORBIDDEN generic buckets unless SPECIFIC type is known: "
    "[\"mixed vegetables\", \"cut vegetables\", \"frozen vegetables\", \"mixed fruits\", \"frozen meats\", \"sauces\"]. "
    "Use specific names instead.\n"
    "7) Merge duplicates internally: do not repeat the same ingredient, sum quantities.\n"
    "8) Max 20 items, prioritize cooking-relevant ones (proteins/starches/vegetables).\n"
    "9) Keep the JSON concise: maximum 10 ingredients. Do not include repeated or decorative items."
    "OUTPUT JSON SHAPE:\n"
    "{ \"ingredients\": [ { \"name_en\": \"tomato\", \"name_ar\": \"طماطم\", \"quantity_estimate\": 3, \"unit\": \"حبة\", "
    "\"state\": \"طازج\", \"category\": \"خضار\", \"confidence\": 0.92, \"inferred\": false } ], "
    "\"notes\": \"short notes if needed\" }\n"
    "Return VALID JSON ONLY."
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
