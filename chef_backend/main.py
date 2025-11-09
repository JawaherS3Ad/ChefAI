# الملف: chefai/backend/main.py (النسخة النهائية لهذه المرحلة)
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid # لتوليد أرقام تعريف فريدة للجلسة

# هذا السطر ضروري لقراءة المفتاح من ملف .env
from dotenv import load_dotenv 
load_dotenv() 


# استيراد LangGraph Core ووكلاء LLM (العقل المدبر)
from .langgraph_core import chef_graph, ChefState # ChefState لتعريف حالة الإدخال
# لن نستخدم Ollama مباشرة هنا، بل سنستخدمه عبر LangGraph

# ----------------- الإعدادات العامة ونماذج البيانات -----------------
app = FastAPI(title="ChefAI Core", version="1.0 - LangGraph Integrated")

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# نموذج الإدخال لنقطة النهاية /start
class StartInput(BaseModel):
    """البيانات المتوقعة عند بدء الجلسة (الصورة المُلتقطة)."""
    image_base64: str

# نموذج الإخراج المتوقع
class ChefOutput(BaseModel):
    session_id: str
    suggested_recipes: List[Dict[str, str]]
    status_message: str

# ----------------- نقطة النهاية الرئيسية (ابدأ) -----------------

@app.post("/api/chef/start", response_model=ChefOutput)
async def start_chef_session(input_data: StartInput):
    """
    يبدأ جلسة شيف جديدة: يتلقى الصورة ويُطلق تدفق LangGraph لتحليلها واقتراح الوصفات.
    """
    # 1. توليد مُعرّف جلسة فريد (مهم لعمليات التخزين المؤقت لاحقًا)
    session_id = str(uuid.uuid4())
    print(f"\n--- [Session: {session_id}] --- بدأت جلسة جديدة.")

    # 2. إعداد الحالة الأولية لتشغيل LangGraph
    initial_state = ChefState(
        session_id=session_id,
        image_base64=input_data.image_base64,
        ingredients="", # سيتعبأ بواسطة أول وكيل
        suggested_recipes=[], # سيتعبأ بواسطة وكيل الوصفات
    )

    try:
        # 3. تشغيل تدفق LangGraph
        # .invoke() تدير تدفق العمل بالكامل من البداية للنهاية
        final_state = chef_graph.invoke(initial_state)

        # 4. بناء الرد النهائي
        return ChefOutput(
            session_id=session_id,
            suggested_recipes=final_state.get('suggested_recipes', []),
            status_message="تم تحليل الصورة واقتراح الوصفات بنجاح."
        )

    except Exception as e:
        print(f"❌ خطأ فادح في تدفق LangGraph: {e}")
        # التعامل مع الأخطاء وإرسال استجابة 500
        raise HTTPException(
            status_code=500,
            detail=f"فشل في تشغيل نظام الذكاء الاصطناعي: {str(e)}"
        )

# ----------------- تشغيل الخادم -----------------

if __name__ == "__main__":
    print("🚀 جاري إطلاق خادم ChefAI FastAPI والتحقق من LangGraph...")
    # الأمر الصحيح للتشغيل مع Uvicorn:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)