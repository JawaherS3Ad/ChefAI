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
        "أنت مساعد طبخ عربي محترف ودقيق للغاية.\n"
        "مهمتك إنشاء وصفة عربية واقعية تعتمد على المكونات المتوفرة حرفياً.\n"
        "يجب الالتزام الكامل بالـ Pydantic Schema المسمى SuggestedRecipe.\n\n"

        "🔶 المكونات المتاحة (JSON) — هذه هي المكونات التي يجب أن تُبنى عليها الوصفة:\n"
        "{ingredients_json}\n\n"

        "🔶 تفضيلات المستخدم (JSON):\n"
        "{preferences_json}\n\n"

        "🔶 سياسات التحضير (JSON):\n"
        "{policy_json}\n\n"

        "⏱ وقت الطهي الأقصى المسموح هو: {max_minutes} دقيقة.\n\n"

        "=============================================\n"
        "❗❗ تعليمات إلزامية وصارمة جداً (ممنوع تجاوزها):\n"
        "1) يجب أن يحتوي حقل ingredients_needed على *كل المكونات المتاحة* الواردة في ingredients_json.\n"
        "   - إن كان للمكون كمية، يجب ذكرها.\n"
        "   - إن لم يكن له كمية، ضع \"1\" كوحدة افتراضية.\n"
        "   - إن لم يكن له وحدة، ضع \"حبة\".\n"
        "   - إن كان الاسم العربي موجودًا استخدمه، وإلا استخدم الاسم الإنجليزي.\n"
        "2) ممنوع أن يكون حقل ingredients_needed فارغًا تحت أي ظرف.\n"
        "3) أي مكون غير متوفر وتحتاجه الوصفة يجب إضافته في missing_items وليس في ingredients_needed.\n"
        "4) يجب أن تتطابق الوصفة مع meal_type بدقة.\n"
        "5) يجب احترام عدد الحصص (servings) وتوزيع الكميات بشكل منطقي.\n"
        "6) cuisines يجب أن تنعكس بوضوح في أسلوب الطبخ والمكونات.\n"
        "7) ممنوع استخدام أسماء عامة مثل: \"خضروات متنوعة\" أو \"صلصات\".\n"
        "8) الخس والخيار لا يتم طبخهما — قد تستخدم كإضافة جانبية فقط.\n"
        "9) الإخراج يجب أن يكون بالعربية بالكامل.\n"
        "10) يجب الالتزام التام ببنية SuggestedRecipe التالية:\n"
        "   • recipe_name\n"
        "   • ingredients_needed (يجب أن يحتوي على جميع المكونات المتاحة)\n"
        "   • preparation_steps\n"
        "   • cooking_time_minutes\n"
        "   • cuisine_type\n"
        "   • missing_items\n"
        "   • shopping_suggestions\n"
        "=============================================\n\n"

        "أنت الآن جاهز لإنشاء وصفة مثالية تعتمد على كل المكونات المذكورة.\n"
        "أعد الإخراج بصيغة JSON فقط بدون أي شرح إضافي."
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
