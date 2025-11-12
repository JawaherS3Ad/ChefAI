# الملف: chefai/backend/main.py (النسخة المعدلة - LangGraph مع Shopping Agent)
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from dotenv import load_dotenv 

load_dotenv()

# ✅ استيراد LangGraph Core
from chef_backend.langgraph_core import chef_graph, ChefState

app = FastAPI(title="ChefAI Core", version="1.0 - LangGraph Integrated with Shopping")

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# نموذج الإدخال
class StartInput(BaseModel):
    image_base64: str
    meal_type: Optional[str] = None
    time_limit: Optional[str] = None
    servings: Optional[int] = None
    cuisines: Optional[List[str]] = None

# نموذج الإخراج
class ChefOutput(BaseModel):
    session_id: str
    recipe: Optional[Dict[str, Any]] = None
    missing_items: Optional[List[str]] = None
    shopping_suggestions: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


@app.post("/api/chef/start", response_model=ChefOutput)
async def start_chef_session(inp: StartInput):
    session_id = str(uuid.uuid4())
    print(f"\n--- [Session: {session_id}] --- بدأت جلسة جديدة.")

    init: ChefState = {
        "session_id": session_id,
        "image_base64": inp.image_base64,
        "preferences": {
            "meal_type": inp.meal_type,
            "time_limit": inp.time_limit,
            "servings": inp.servings,
            "cuisines": inp.cuisines or []
        }
    }

    try:
        # ✅ التصحيح هنا
        final_state = chef_graph.invoke(init)
        fp = final_state.get("final_payload", {})

        return {
            "session_id": session_id,
            **fp
            }
    
    except Exception as e:
        print(f"❌ خطأ فادح في تدفق LangGraph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"فشل في تشغيل نظام الذكاء الاصطناعي: {str(e)}"
        )

if __name__ == "__main__":
    print("🚀 جاري إطلاق خادم ChefAI FastAPI والتحقق من LangGraph...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
