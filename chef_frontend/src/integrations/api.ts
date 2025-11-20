// src/integrations/api.ts

// ---- أنواع البيانات القادمة من الباك إند ----

export interface BackendIngredient {
  name_en?: string;
  name_ar?: string;
  name?: string;
  quantity_estimate?: string | number | null;
  unit?: string | null;
  state?: string | null;
  category?: string | null;
  confidence?: number | null;
  inferred?: boolean | null;
}

export interface AnalyzeResponse {
  session_id: string;
  detected_ingredients: BackendIngredient[];
  uncertain: BackendIngredient[];
  notes: string;
}

export interface GenerateRecipePayload {
  session_id: string;
  meal_type: string;    // "breakfast" | "lunch" | ...
  time_limit: string;   // "Under 5 min" | "30 min" | "Over 30 min"
  servings: number;     // 1..5
  cuisines: string[];   // ["Asian", "Arabic", ...]
}

export interface ShoppingSuggestion {
  item: string;
  quantity: number;
  unit: string;
  vendor: string;
  estimated_price: number;
  product_url: string;
}

export interface GenerateRecipeResponse {
  recipe_name: string;
  ingredients_needed: BackendIngredient[];
  preparation_steps: string[];
  cooking_time_minutes: number;
  cuisine_type: string;
  missing_items: string[];
  shopping_suggestions: ShoppingSuggestion[];
}

// ---- استدعاءات فعلية للباك إند ----

const API_BASE_URL =
  "https://triumphant-kindness-production.up.railway.app/api";

export async function analyzeImage(
  image_base64: string
): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE_URL}/chef/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_base64 }),
  });

  if (!res.ok) {
    throw new Error("Analyze failed");
  }

  return res.json();
}

export async function generateRecipe(
  payload: GenerateRecipePayload
): Promise<GenerateRecipeResponse> {
  const res = await fetch(`${API_BASE_URL}/chef/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Generate failed");
  }

  return res.json();
}
