# -*- coding: utf-8 -*-
# الملف: chef_backend/langgraph_core.py
from __future__ import annotations

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from .agents import analyze_image_api
from .recipe_generator import generate_recipe
from .shopping_integration import get_shopping_suggestions
from .utils import parse_vision_json, normalize_ar_basic
from .ontology import EN2AR, is_bucket, normalize_ar, UNIT_FALLBACK
from .namefixer_agent import fix_ingredients_names


# ============================================================
# 1) تعريف الحالة العامة (State)
# ============================================================
class ChefState(TypedDict, total=False):
    session_id: str
    image_base64: str

    # Vision
    vision_raw: Any
    ingredients_raw: List[Dict[str, Any]]

    # Clean / split
    items_clean: List[Dict[str, Any]]
    used_items: List[Dict[str, Any]]
    uncertain_items: List[Dict[str, Any]]

    # Preferences + Policy
    preferences: Dict[str, Any]
    policy: Dict[str, Any]

    # Recipe
    recipe: Dict[str, Any]

    # Missing
    missing_items: List[str]
    shopping_suggestions: List[Dict[str, Any]]

    # Final
    final_payload: Dict[str, Any]
    error: str


# ============================================================
# 2) Helpers
# ============================================================
CONFIDENCE_THRESHOLD = 0.5


def _split_used_uncertain(items, thr):
    used, uncertain = [], []
    for it in items:
        c = float(it.get("confidence") or 0.0)
        (used if c >= thr else uncertain).append(it)
    return used, uncertain


def _merge_items(items):
    merged = {}
    for it in items:
        name_ar = normalize_ar(it.get("name_ar") or "")
        if not name_ar:
            name_ar = (it.get("name_en") or "").strip().lower()

        key = name_ar or "unknown"
        qty = int(it.get("quantity_estimate") or 1)
        unit = it.get("unit") or UNIT_FALLBACK
        conf = float(it.get("confidence") or 0.0)

        prev = merged.get(key)
        if prev:
            prev["quantity_estimate"] += max(1, qty)
            prev["confidence"] = max(prev["confidence"], conf)
        else:
            it2 = dict(it)
            it2["name_ar"] = normalize_ar(it2.get("name_ar") or "")
            if not it2["name_ar"] and it2.get("name_en"):
                it2["name_ar"] = EN2AR.get(
                    it2["name_en"].strip().lower(), ""
                )
            it2["unit"] = unit
            it2["quantity_estimate"] = max(1, qty)
            it2["confidence"] = conf
            merged[key] = it2

    return list(merged.values())


def _sanitize_items(raw_items):
    cleaned = []
    for it in raw_items or []:
        name_en = (it.get("name_en") or "").strip()
        name_ar = (it.get("name_ar") or "").strip()

        if is_bucket(name_en, name_ar):
            continue

        if not name_ar and name_en:
            ar = EN2AR.get(name_en.lower(), "")
            if ar:
                it["name_ar"] = ar

        if not it.get("unit"):
            it["unit"] = UNIT_FALLBACK

        cleaned.append(it)

    return _merge_items(cleaned)


def _estimate_missing(available_used, recipe_ingredients):
    avail = [normalize_ar_basic(it.get("name_ar", "")) for it in (available_used or [])]
    missing = []

    for need in (recipe_ingredients or []):
        base = normalize_ar_basic(need)
        present = any(base in a or a in base for a in avail if a)
        if not base or not present:
            missing.append(need)

    return missing


# ============================================================
# 3) Nodes
# ============================================================

# ---------- A) Vision
def node_vision(state: ChefState) -> ChefState:
    print("🔹 [INFO] node_vision")
    try:
        raw = analyze_image_api(state["image_base64"], state.get("session_id"))
    except Exception as e:
        return {"error": f"فشل تحليل الصورة: {e}"}

    if not raw or not raw.get("ingredients"):
        return {"error": "لم يتم اكتشاف أي مكونات في الصورة."}

    return {"vision_raw": raw}


# ---------- B) NameFixer
def node_namefixer(state: ChefState) -> ChefState:
    print("🔹 [INFO] node_namefixer")
    parsed = parse_vision_json(state["vision_raw"])
    items = parsed.get("ingredients", []) or []
    fixed = fix_ingredients_names(items)
    return {"ingredients_raw": fixed}


# ---------- C) Prepare Step1
def node_prepare_analysis(state: ChefState) -> ChefState:
    print("🔹 [INFO] node_prepare_analysis")

    items_clean = _sanitize_items(state["ingredients_raw"])
    used, uncertain = _split_used_uncertain(items_clean, CONFIDENCE_THRESHOLD)

    if len(used) < 1 and uncertain:
        used.append(uncertain.pop(0))

    return {
        "items_clean": items_clean,
        "used_items": used,
        "uncertain_items": uncertain
    }


# ---------- D) Prepare Step2
def node_prepare_generation(state: ChefState) -> ChefState:
    print("🔹 [INFO] node_prepare_generation")

    raw = state.get("ingredients_raw", [])
    items_clean = _sanitize_items(raw)
    used, uncertain = _split_used_uncertain(items_clean, CONFIDENCE_THRESHOLD)

    return {
        "items_clean": items_clean,
        "used_items": used,
        "uncertain_items": uncertain
    }


# ---------- E) Recipe Generation
def node_generate_recipe(state: ChefState) -> ChefState:
    print("🔹 [INFO] node_generate_recipe")

    if state.get("error"):
        return {"recipe": {}}

    payload = {
        "ingredients": state.get("used_items", []),
        "preferences": state.get("preferences", {}),
        "policy": state.get("policy", {})
    }

    try:
        suggested = generate_recipe(payload)
        return {"recipe": suggested.model_dump()}

    except Exception as e:
        return {"error": f"فشل توليد الوصفة: {e}"}


# ---------- F) Missing Items + Shopping
def node_missing_and_shop(state: ChefState) -> ChefState:
    print("🔹 [INFO] node_missing_and_shop")

    recipe = state.get("recipe", {})
    needed = recipe.get("ingredients_needed") or []

    missing = _estimate_missing(state.get("used_items", []), needed)
    suggestions = get_shopping_suggestions(missing)

    return {
        "missing_items": missing,
        "shopping_suggestions": suggestions
    }


# ---------- G) Final assembly Step1
def node_assemble_analyze(state: ChefState) -> ChefState:
    print("🔹 [INFO] node_assemble_analyze")

    if state.get("error"):
        return {"final_payload": {"error": state["error"]}}

    return {
        "final_payload": {
            "detected_ingredients": state.get("used_items", []),
            "uncertain": state.get("uncertain_items", []),
            "notes": "Image analyzed successfully."
        }
    }


# ---------- H) Final assembly Step2
def node_assemble_generate(state: ChefState) -> ChefState:
    print("🔹 [INFO] node_assemble_generate")

    if state.get("error"):
        return {"final_payload": {"error": state["error"]}}

    recipe = state.get("recipe", {})

    return {
        "final_payload": {
            "recipe_name": recipe.get("recipe_name"),
            "preparation_steps": recipe.get("preparation_steps", []),
            "ingredients_needed": recipe.get("ingredients_needed", []),
            "missing_items": state.get("missing_items", []),
            "shopping_suggestions": state.get("shopping_suggestions", []),
            "cooking_time_minutes": recipe.get("cooking_time_minutes"),
            "cuisine_type": recipe.get("cuisine_type")
        }
    }


# ============================================================
# 4) Graphs
# ============================================================
def create_analyze_graph():
    g = StateGraph(ChefState)

    g.add_node("vision", node_vision)
    g.add_node("namefixer", node_namefixer)
    g.add_node("prepare", node_prepare_analysis)
    g.add_node("assemble", node_assemble_analyze)

    g.set_entry_point("vision")
    g.add_edge("vision", "namefixer")
    g.add_edge("namefixer", "prepare")
    g.add_edge("prepare", "assemble")
    g.add_edge("assemble", END)

    return g.compile()


def create_generate_graph():
    g = StateGraph(ChefState)

    g.add_node("prepare", node_prepare_generation)
    g.add_node("generate", node_generate_recipe)
    g.add_node("miss", node_missing_and_shop)
    g.add_node("assemble", node_assemble_generate)

    g.set_entry_point("prepare")
    g.add_edge("prepare", "generate")
    g.add_edge("generate", "miss")
    g.add_edge("miss", "assemble")
    g.add_edge("assemble", END)

    return g.compile()


# ============================================================
# 5) جاهز للتشغيل
# ============================================================
analyze_graph = create_analyze_graph()
generate_graph = create_generate_graph()
