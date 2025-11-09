from langchain_huggingface import HuggingFaceEndpoint

import os
import json

# ----------------- الإعدادات -----------------
HF_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACEHUB_API_TOKEN") 

llm_hf = None
try:
    if not HUGGINGFACE_TOKEN:
        raise ValueError("HUGGINGFACEHUB_API_TOKEN غير موجود.")

    llm_hf = HuggingFaceEndpoint(
        repo_id=HF_MODEL,
        # *** التعديل: تمرير temperature فقط وإزالة max_length ***
        temperature=0.5, 
        # (تم حذف max_length للتخلص من الخطأ)
        huggingfacehub_api_token=HUGGINGFACE_TOKEN
    )
    print(f"✅ تم تهيئة الوكيل السحابي: {HF_MODEL} بنجاح.")
except Exception as e:
    print(f"❌ فشل تهيئة HuggingFaceEndpoint: {e}. ")
    llm_hf = None
    print(f"✅ تم تهيئة الوكيل السحابي: {HF_MODEL}")
except Exception as e:
    # طباعة الخطأ الذي تم إثارته أو أي خطأ آخر
    print(f"❌ فشل تهيئة HuggingFaceHub: {e}. تأكد من وجود مفتاح API صالح.")
    llm_hf = None

# ----------------- الوكلاء (Agents) -----------------

def analyze_image_api(image_base64: str, session_id: str) -> str:
    """[وكيل وهمي مؤقتاً] (نفس الكود السابق)"""
    print(f"--- [Agent: Analyze_Ingredients] --- جاري تحليل الصورة لـ Session: {session_id}")
    return "لقد تم التعرف على المكونات التالية: بيض، طماطم، بصل، بعض الخضروات الورقية."

def suggest_recipes_agent(ingredients: str) -> str:
    """[وكيل الوصفات] يستخدم Mistral السحابي لاقتراح وصفات."""
    if not llm_hf:
        return json.dumps([{"name": "خطأ", "description": "خدمة Hugging Face غير متصلة. المفتاح غير صالح."}])
    
    print("--- [Agent: Suggest_Recipes] --- Mistral السحابي جاري توليد الوصفات...")
    
    prompt = f"""
    أنت مساعد شيف ماهر. بناءً على المكونات التالية: "{ingredients}".
    اقترح ثلاث (3) وصفات مختلفة. يجب أن ترد فقط بقائمة JSON تتكون من مصفوفة (Array) من ثلاثة كائنات (Objects).
    يجب أن يحتوي كل كائن على: "name" (اسم الوصفة) و "description" (وصف موجز).
    
    مثال تنسيق الرد:
    [
        {{"name": "شكشوكة تقليدية", "description": "وصفة شهيرة بالبيض المطبوخ في صلصة الطماطم الحارة."}},
        ...
    ]
    """
    
    response = llm_hf.invoke(prompt)
    
    print("--- [Agent: Suggest_Recipes] --- تم توليد الوصفات عبر الكلاود.")
    return response.strip()