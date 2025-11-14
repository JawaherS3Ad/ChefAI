# -*- coding: utf-8 -*-
"""
Recipe Generator Agent (Step2 — LLM Generator Only)
--------------------------------------------------
هذا الملف مسؤول حصرياً عن توليد الوصفات.
LangGraph يقوم بجميع الـ orchestration الخارجي.

وظائف هذا الوكيل:
1. استقبال ingredients + preferences + policy.
2. استخدام max_cooking_minutes الجاهزة من LangGraph (وليس من UI).
3. بناء برومبت ذكي ومتغير.
4. توليد JSON مطابق لـ SuggestedRecipe عبر سلسلة Qwen (fallback).
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate


# -------------------------------------------------------------
# 1) Priority Model List (Fallback)
# -------------------------------------------------------------
QWEN_MODELS_PRIORITY = [
    "qwen/qwen3-30b-a3b:free",
    "qwen/qwen3-14b:free",
    "qwen/qwen3-4b:free",
]


def make_llm(model_name: str) -> ChatOpenAI:
    """تهيئة LLM للاستخدام مع OpenRouter."""
    return ChatOpenAI(
        model=model_name,
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        max_tokens=700,
        temperature=0.3,
        response_format={"type": "json_object"},  # خروج JSON حصراً
    )


# -------------------------------------------------------------
# 2) SuggestedRecipe Schema
# -------------------------------------------------------------
class SuggestedRecipe(BaseModel):
    recipe_name: str = Field(description="اسم الوصفة.")
    ingredients_needed: list[str] = Field(description="المكونات المطلوبة.")
    preparation_steps: list[str] = Field(description="خطوات التحضير.")
    cooking_time_minutes: int = Field(description="مدة الطبخ بالدقائق.")
    cuisine_type: str = Field(description="نوع المطبخ.")


def get_llm_with_schema(model_name: str):
    return make_llm(model_name).with_structured_output(SuggestedRecipe)


# -------------------------------------------------------------
# 3) Intelligent Prompt Template
# -------------------------------------------------------------
prompt = PromptTemplate(
    input_variables=[
        "ingredients_json",
        "preferences_json",
        "policy_json",
        "max_minutes",
    ],
    template=(
        "أنت مساعد طبخ عربي محترف.\n"
        "مهمتك إنشاء وصفة مطابقة تماماً للـPydantic Schema.\n\n"

        "المكونات المتاحة (JSON):\n{ingredients_json}\n\n"
        "تفضيلات المستخدم:\n{preferences_json}\n\n"
        "السياسات:\n{policy_json}\n\n"

        "الحد الأقصى المسموح لوقت الطهي هو: {max_minutes} دقيقة.\n"
        "يجب أن تكون الوصفة قابلة للطهي خلال هذا الوقت فعلياً.\n\n"

        "قوانين صارمة:\n"
        "• لا تستخدم مكونات غير متوفرة إلا عند الضرورة القصوى.\n"
        "• المكونات الناقصة تُضاف في ingredients_needed.\n"
        "• ممنوع استخدام أسماء عامة مثل: mixed vegetables / sauces / frozen meats.\n"
        "• الخس والخيار لا يتم طبخهما مطلقاً.\n"
        "• يجب احترام الوقت ونوع الوجبة وعدد الحصص.\n"
        "• الإخراج يجب أن يكون بالعربية تماماً.\n"
        "• الالتزام الكامل بشكل SuggestedRecipe.\n"
    ),
)


# -------------------------------------------------------------
# 4) Main Generation Function
# -------------------------------------------------------------
def generate_recipe(payload: dict) -> SuggestedRecipe:
    """
    توليد وصفة كاملة باستخدام Qwen:
    - ingredients: أسماء عربية موحدة ومؤكدّة
    - preferences: meal_type، time_limit، cuisines ...
    - policy: تحتوي على max_cooking_minutes
    """

    ingredients_json = json.dumps(payload.get("ingredients", []), ensure_ascii=False)
    preferences_json = json.dumps(payload.get("preferences", {}), ensure_ascii=False)
    policy_json = json.dumps(payload.get("policy", {}), ensure_ascii=False)

    # 🔥 هذه النقطة كانت الخلل
    max_minutes = payload.get("policy", {}).get("max_cooking_minutes", 30)

    message = HumanMessage(
        content=prompt.format(
            ingredients_json=ingredients_json,
            preferences_json=preferences_json,
            policy_json=policy_json,
            max_minutes=max_minutes,
        )
    )

    last_error = None

    # سلسلة fallback
    for model_name in QWEN_MODELS_PRIORITY:
        try:
            llm = get_llm_with_schema(model_name)
            return llm.invoke([message])

        except Exception as e:
            # Rate-limit → ننتقل للنموذج التالي
            if "429" in str(e) or "rate" in str(e).lower():
                last_error = e
                continue
            raise

    raise RuntimeError(f"All Qwen models failed. Last error: {last_error}")


# -------------------------------------------------------------
# 5) Local Test
# -------------------------------------------------------------
if __name__ == "__main__":
    sample_payload = {
        "ingredients": [
            {"name_ar": "بيض", "quantity_estimate": 2},
            {"name_ar": "طماطم", "quantity_estimate": 1},
        ],
        "preferences": {
            "meal_type": "Dinner",
            "cuisines": ["Arabic"],
            "servings": 1,
        },
        "policy": {
            "max_cooking_minutes": 15,
            "forbid_generic_dough": True,
            "require_baking_basics_for_dough": False,
            "max_missing": 3,
        },
    }

    result = generate_recipe(sample_payload)
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
