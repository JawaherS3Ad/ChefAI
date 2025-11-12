# -*- coding: utf-8 -*-
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from chef_backend.vision_agent import analyze_fridge_image
from chef_backend.utils import parse_vision_json
from chef_backend.ontology import is_bucket, normalize_ar, EN2AR, UNIT_FALLBACK
from chef_backend.recipe_generator import generate_recipe
from chef_backend.shopping_integration import get_shopping_suggestions

CONFIDENCE_THRESHOLD = 0.5

class ChefState(TypedDict, total=False):
    session_id: str
    image: str                 # path/url/base64
    ingredients: List[Dict[str, Any]]
    uncertain: List[Dict[str, Any]]
    preferences: Dict[str, Any]
    policy: Dict[str, Any]
    recipe: Dict[str, Any]
    missing: List[str]
    shopping: List[Dict[str, Any]]

# --- utils صغيرة (من orchestrator الحالي) ---
def _split_used_uncertain(items, thr):
    used, unc = [], []
    for it in items:
        (used if float(it.get("confidence", 0.0)) >= thr else unc).append(it)
    return used, unc

def _sanitize(items):
    cleaned=[]
    for it in items:
        ne=(it.get("name_en") or "").strip()
        na=(it.get("name_ar") or "").strip()
        if is_bucket(ne, na):
            continue
        if not na and ne:
            it["name_ar"]=EN2AR.get(ne.lower(), na)
        if not it.get("unit"):
            it["unit"]=UNIT_FALLBACK
        it["name_ar"]=normalize_ar(it.get("name_ar") or "")
        cleaned.append(it)
    # دمج بسيط حسب الاسم العربي
    by={}
    for it in cleaned:
        k=it.get("name_ar") or (it.get("name_en") or "unknown").lower()
        prev=by.get(k)
        if prev:
            prev["quantity_estimate"]=prev.get("quantity_estimate",1)+max(1,int(it.get("quantity_estimate",1)))
            prev["confidence"]=max(prev.get("confidence",0.0), float(it.get("confidence",0)))
        else:
            by[k]=it
    return list(by.values())

def _estimate_missing(available_used, needed):
    names={ (it.get("name_ar") or "").strip().lower() for it in available_used }
    miss=[]
    for n in (needed or []):
        b=(n or "").strip().lower()
        if not b or all((b not in a and a not in b) for a in names):
            miss.append(n)
    return miss

# --- NODES ---
def node_vision(state: ChefState) -> ChefState:
    raw = analyze_fridge_image(state["image"])
    vis = parse_vision_json(raw)
    items = _sanitize(vis.get("ingredients", []) or [])
    used, unc = _split_used_uncertain(items, CONFIDENCE_THRESHOLD)
    return {"ingredients": used, "uncertain": unc}

def node_policy(state: ChefState) -> ChefState:
    ing = state.get("ingredients", [])
    has_dough = any("دقيق" in (i.get("name_ar") or "") for i in ing) \
             and any("ماء"  in (i.get("name_ar") or "") for i in ing) \
             and any("خميرة" in (i.get("name_ar") or "") for i in ing)
    return {"policy": {
        "forbid_generic_dough": True,
        "require_baking_basics_for_dough": has_dough,
        "max_missing": 3,
        "time_limit": (state.get("preferences") or {}).get("time_limit")
    }}

def node_generate_recipe(state: ChefState) -> ChefState:
    payload = {
        "ingredients": state.get("ingredients", []),
        "preferences": state.get("preferences", {}),
        "policy": state.get("policy", {})
    }
    suggested = generate_recipe(payload).model_dump()
    return {"recipe": suggested}

def node_missing_and_shop(state: ChefState) -> ChefState:
    recipe = state.get("recipe", {})
    need = recipe.get("ingredients_needed") or []
    miss = _estimate_missing(state.get("ingredients", []), need)
    shop = get_shopping_suggestions(miss) if miss else []
    return {"missing": miss, "shopping": shop}

def build_graph():
    g = StateGraph(ChefState)
    g.add_node("vision", node_vision)
    g.add_node("policy", node_policy)
    g.add_node("generate", node_generate_recipe)
    g.add_node("missing_shop", node_missing_and_shop)

    g.set_entry_point("vision")
    g.add_edge("vision", "policy")
    g.add_edge("policy", "generate")
    g.add_edge("generate", "missing_shop")
    g.add_edge("missing_shop", END)
    return g.compile()

chef_graph = build_graph()
