# الملف: chefai/backend/langgraph_core.py
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
import json
from .agents import analyze_image_api, suggest_recipes_agent # الاستيراد من ملف agents

# ----------------- 1. تعريف حالة النظام (ChefState) -----------------
# هذه هي البيانات التي يتم تداولها بين الوكلاء في كل خطوة
class ChefState(TypedDict):
    """يمثل حالة التطبيق خلال تفاعلات المستخدم."""
    session_id: str
    image_base64: str
    ingredients: str
    suggested_recipes: List[dict]
    # macros_analysis: str # سنضيفها لاحقاً

# ----------------- 2. تعريف العقد (Nodes) -----------------

def node_analyze_ingredients(state: ChefState) -> ChefState:
    """العقدة الأولى: تحليل الصورة والحصول على المكونات."""
    ingredients = analyze_image_api(state['image_base64'], state['session_id'])
    
    # تحديث حالة النظام بالبيانات الجديدة
    return {"ingredients": ingredients}

def node_suggest_recipes(state: ChefState) -> ChefState:
    """العقدة الثانية: استخدام المكونات لاقتراح الوصفات."""
    recipe_json_str = suggest_recipes_agent(state['ingredients'])
    
    try:
        # محاولة تحليل نص JSON الذي ولده النموذج
        recipes = json.loads(recipe_json_str)
        return {"suggested_recipes": recipes}
    except json.JSONDecodeError:
        print(f"❌ خطأ في تنسيق JSON من Mixtral: {recipe_json_str}")
        return {"suggested_recipes": [{"name": "خطأ", "description": "فشل توليد الوصفات، يرجى المحاولة مرة أخرى."}]}

# ----------------- 3. بناء الرسم البياني (Graph) -----------------

def create_chef_graph():
    """ينشئ ويُجمِّع آلة الحالة (LangGraph)."""
    
    # 1. تهيئة الرسم البياني بحالة النظام المحددة
    workflow = StateGraph(ChefState)
    
    # 2. إضافة العقد (Nodes)
    workflow.add_node("analyze_ingredients", node_analyze_ingredients)
    workflow.add_node("suggest_recipes", node_suggest_recipes)
    
    # 3. تحديد المسار الأولي
    # البداية -> تحليل المكونات
    workflow.set_entry_point("analyze_ingredients")
    
    # 4. تحديد المسار بين العقد
    # تحليل المكونات -> اقتراح الوصفات
    workflow.add_edge("analyze_ingredients", "suggest_recipes")
    
    # 5. تحديد نهاية التدفق
    # اقتراح الوصفات -> نهاية التطبيق (END)
    workflow.add_edge("suggest_recipes", END)

    # تجميع وتصديق الرسم البياني
    app = workflow.compile()
    return app

# إنشاء نسخة من الرسم البياني
chef_graph = create_chef_graph()