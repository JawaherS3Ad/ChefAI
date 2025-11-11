import os
import json
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

# -------------------------
# 1. إعداد النموذج من OpenRouter (Qwen)
# -------------------------

QWEN_MODELS_PRIORITY = [
    "qwen/qwen3-30b-a3b:free",
    "qwen/qwen3-14b:free",
    "qwen/qwen3-4b:free",
]

def make_llm(model_name: str) -> ChatOpenAI:
    """
    إنشاء نموذج Qwen مع ضبط معلمات أكثر استقرارًا.
    """
    return ChatOpenAI(
        model=model_name,
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        max_tokens=700,       # 🔸 الحد الأقصى للإخراج لتفادي LengthFinishReasonError
        temperature=0.3,      # 🔸 تنويع بسيط بدون خروج عن الواقعية
        response_format={"type": "json_object"}  # 🔸 يطلب JSON صِرف بدل نص حر
    )


# -------------------------
# 2. نموذج الإخراج
# -------------------------
class SuggestedRecipe(BaseModel):
    recipe_name: str = Field(description="اسم الوصفة المقترحة.")
    ingredients_needed: list[str] = Field(description="قائمة بجميع المكونات المطلوبة (الموجودة في الصورة وغير الموجودة).")
    preparation_steps: list[str] = Field(description="خطوات التحضير بالتفصيل.")
    cooking_time_minutes: int = Field(description="مدة الطهي بالدقائق.")
    cuisine_type: str = Field(description="نوع المطبخ (مثلاً: عربي، إيطالي، آسيوي).")

def get_llm_with_schema(model_name: str):
    llm = make_llm(model_name)
    return llm.with_structured_output(SuggestedRecipe)

# -------------------------
# 3. برومبت ذكي يعتمد على المكونات + التفضيلات + السياسات
# -------------------------
prompt = PromptTemplate(
    input_variables=["ingredients_json", "preferences_json", "policy_json"],
    template=(
        "You are a precise Arabic culinary assistant. Output strictly as the provided Pydantic schema.\n\n"
        "AVAILABLE INGREDIENTS (JSON):\n{ingredients_json}\n\n"
        "USER PREFERENCES (JSON):\n{preferences_json}\n\n"
        "POLICY RULES (JSON):\n{policy_json}\n\n"
        "CRITICAL RULES:\n"
        "1) Ingredient Usage:\n"
        "   - Use only available ingredients as much as possible.\n"
        "   - If you must add missing items, keep them minimal and justified; list them under 'ingredients_needed'.\n"
        "   - NEVER use generic/vague names like 'mixed vegetables', 'frozen vegetables', 'assorted sauces', 'frozen meats', 'pre-cut vegetables'.\n"
        "   - Do NOT introduce 'sauce' as a generic item unless a specific sauce exists in the available list (e.g., 'صلصة طماطم').\n\n"
        "2) Dough Policy:\n"
        "   - If policy.forbid_generic_dough is true and policy.require_baking_basics_for_dough is false:\n"
        "     do NOT propose recipes requiring generic 'dough' unless flour + water + yeast are explicitly available.\n\n"
        "3) Lettuce & Cucumber:\n"
        "   - NEVER cook lettuce (خس) or cucumber (خيار) on heat. Use them only raw/cold (salads, garnish), unless explicitly requested.\n\n"
        "4) Constraints:\n"
        "   - Respect time constraints, meal type, and servings.\n\n"
        "5) Output Format:\n"
        "   - Return ALL text fields in Arabic.\n"
        "   - Follow the SuggestedRecipe Pydantic schema EXACTLY.\n"
        "   - Be realistic with times and steps.\n"
    ),
)


# -------------------------
# 4. توليد الوصفة مع Fallback (✅ مُصلَح)
# -------------------------
def generate_recipe(payload: dict):
    """
    يحوّل المكونات + التفضيلات + السياسات إلى وصفة منظمة.
    
    Args:
        payload: dict يحتوي على {ingredients, preferences, policy}
    
    Returns:
        كائن SuggestedRecipe
    """
    # استخراج البيانات من payload
    ingredients_json = payload.get("ingredients", [])
    preferences_json = payload.get("preferences", {})
    policy_json = payload.get("policy", {})
    
    # تحويلها إلى JSON strings
    ingredients_str = json.dumps(ingredients_json, ensure_ascii=False)
    preferences_str = json.dumps(preferences_json, ensure_ascii=False)
    policy_str = json.dumps(policy_json, ensure_ascii=False)

    # بناء الرسالة
    messages = [HumanMessage(content=prompt.format(
        ingredients_json=ingredients_str,
        preferences_json=preferences_str,
        policy_json=policy_str
    ))]

    # محاولة التوليد مع fallback
    last_error = None
    for model_name in QWEN_MODELS_PRIORITY:
        try:
            llm_with_tools = get_llm_with_schema(model_name)
            return llm_with_tools.invoke(messages)
        except Exception as e:
            text = str(e).lower()
            if any(x in text for x in ("429", "rate", "temporarily", "provider returned error")):
                last_error = e
                continue
            raise
    raise RuntimeError(f"All Qwen fallback models failed. Last error: {last_error}")


# -------------------------
# 5. اختبار بسيط (✅ محدّث)
# -------------------------
if __name__ == "__main__":
    # بناء payload كامل مع policy
    sample_payload = {
        "ingredients": [
            {"name_ar": "طماطم", "quantity_estimate": 3, "unit": "حبة", "state": "طازج"},
            {"name_ar": "بيض", "quantity_estimate": 4, "unit": "حبة", "state": "طازج"},
        ],
        "preferences": {
            "meal_type": "Dinner",
            "time_limit": "30m",
            "servings": 2,
            "cuisines": ["Saudi", "Italian"]
        },
        "policy": {
            "forbid_generic_dough": True,
            "require_baking_basics_for_dough": False,
            "max_missing": 3,
            "time_limit": "30m"
        }
    }

    print("🔸 اختبار توليد وصفة من payload كامل...\n")
    result = generate_recipe(sample_payload)
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))