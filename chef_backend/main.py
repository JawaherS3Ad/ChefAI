# -*- coding: utf-8 -*-
# الملف: chef_backend/main.py

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------
# LangGraph Orchestrators
# ------------------------------------------------------------
from chef_backend.langgraph_core import (
    analyze_graph,
    generate_graph,
    ChefState
)

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------
from chef_backend.utils import map_ui_time_to_minutes
from chef_backend.utils import map_ui_time_to_minutes, map_servings

# ------------------------------------------------------------
# تخزين سيشنات Step1
# ------------------------------------------------------------
SESSION_STORE: Dict[str, Dict[str, Any]] = {}

# ------------------------------------------------------------
# FastAPI + CORS
# ------------------------------------------------------------
app = FastAPI(
    title="ChefAI Backend — Two-Step Orchestrator",
    version="2.2"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# Models
# ------------------------------------------------------------

# ---------- STEP 1 ----------
class AnalyzeRequest(BaseModel):
    image_base64: str


class AnalyzeResponse(BaseModel):
    session_id: str
    detected_ingredients: List[Dict[str, Any]]
    uncertain: List[Dict[str, Any]]
    notes: str
    error: Optional[str] = None


# ---------- STEP 2 ----------
class GenerateRequest(BaseModel):
    session_id: str
    meal_type: Optional[str] = None
    time_limit: Optional[str] = None    # <— raw UI value like "Under 5 min"
    servings: Optional[int] = 2
    cuisines: Optional[List[str]] = None


class GenerateResponse(BaseModel):
    recipe_name: Optional[str] = None
    preparation_steps: Optional[List[str]] = None
    ingredients_needed: Optional[List[str]] = None
    missing_items: Optional[List[str]] = None
    shopping_suggestions: Optional[List[Dict[str, Any]]] = None
    cooking_time_minutes: Optional[int] = None
    cuisine_type: Optional[str] = None
    error: Optional[str] = None


# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

# ------------------------------------------------------------
# STEP 1 — ANALYZE IMAGE
# ------------------------------------------------------------
@app.post("/api/chef/analyze", response_model=AnalyzeResponse)
async def analyze_image(req: AnalyzeRequest):

    session_id = str(uuid.uuid4())
    print(f"\n--- SESSION {session_id} — STEP 1 (Analyze) ---")

    init_state: ChefState = {
        "session_id": session_id,
        "image_base64": req.image_base64
    }

    try:
        state_out = analyze_graph.invoke(init_state)
        final = state_out.get("final_payload", {})

        if "error" in final:
            return AnalyzeResponse(
                session_id=session_id,
                detected_ingredients=[],
                uncertain=[],
                notes="",
                error=final["error"]
            )

        # حفظ بيانات Step1
        SESSION_STORE[session_id] = {
            "ingredients": final.get("detected_ingredients", []),
            "uncertain": final.get("uncertain", []),
            "notes": final.get("notes", "")
        }

        return AnalyzeResponse(
            session_id=session_id,
            detected_ingredients=final.get("detected_ingredients", []),
            uncertain=final.get("uncertain", []),
            notes=final.get("notes", "")
        )

    except Exception as e:
        print(f"❌ Error in ANALYZE step: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analyze step failed: {str(e)}"
        )


# ------------------------------------------------------------
# STEP 2 — GENERATE RECIPE
# ------------------------------------------------------------
@app.post("/api/chef/generate", response_model=GenerateResponse)
async def generate_recipe_endpoint(req: GenerateRequest):

    print(f"\n--- SESSION {req.session_id} — STEP 2 (Generate) ---")

    # تحقق من السيشن
    if req.session_id not in SESSION_STORE:
        raise HTTPException(
            status_code=400,
            detail="Invalid session_id. Run /analyze first."
        )

    stored = SESSION_STORE[req.session_id]

    # تحويل time_limit من واجهة المستخدم → دقائق
    max_minutes = map_ui_time_to_minutes(req.time_limit)

    # تجهيز الحالة لـ LangGraph (Step2)
    init_state: ChefState = {
        "session_id": req.session_id,
        "ingredients_raw": stored["ingredients"],   # نتائج Step1
        "preferences": {
            "meal_type": req.meal_type,
            "servings": map_servings(req.servings),
            "cuisines": req.cuisines or [],
        },
        "policy": {
            "max_cooking_minutes": max_minutes,
            "forbid_generic_dough": True,                  # سياسة أساسية
            "require_baking_basics_for_dough": False,
            "max_missing": 3
        }
    }

    try:
        state_out = generate_graph.invoke(init_state)
        final = state_out.get("final_payload", {})

        if "error" in final:
            return GenerateResponse(error=final["error"])

        return GenerateResponse(**final)

    except Exception as e:
        print(f"❌ Error in GENERATE step: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Generate step failed: {str(e)}"
        )


# ------------------------------------------------------------
# RUN LOCAL
# ------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 ChefAI Backend — Two-Step API Running...")
    uvicorn.run("chef_backend.main:app", host="0.0.0.0", port=8000, reload=True)
