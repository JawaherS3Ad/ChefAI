// src/pages/generate/PantryChef.tsx
import { useState, useRef } from "react";
import { ArrowLeft, Camera, Plus, X } from "lucide-react";
import { useLocation } from "wouter";
import { useAppStore } from "../../store/app-store";
import { useToast } from "../../hooks/use-toast";
import { RecipeView } from "../../components/RecipeView";
import {
  analyzeImage,
  generateRecipe,
} from "../../integrations/api";
import type { GenerateRecipePayload } from "../../integrations/api";
import type { Preferences } from "../../store/app-store";

// ---- Helpers لتحويل تفضيلات UI إلى فورمات الباك ----

function mapMealType(mealType: string | undefined): string {
  if (!mealType) return "any";
  switch (mealType) {
    case "breakfast":
      return "breakfast";
    case "lunch":
      return "lunch";
    case "dinner":
      return "dinner";
    case "snack":
      return "snack";
    default:
      return "any";
  }
}

function mapCookingTime(cookingTime: string | undefined): string {
  switch (cookingTime) {
    case "under5":
      return "Under 5 min";
    case "around30":
      return "30 min";
    case "over30":
      return "Over 30 min";
    default:
      return "30 min";
  }
}

function mapServings(servings: string | undefined): number {
  switch (servings) {
    case "onlyMe":
      return 1;
    case "2-3":
      return 2;
    case "more3":
      return 4;
    default:
      return 2;
  }
}

function mapCuisine(cuisine: string | undefined): string {
  switch (cuisine) {
    case "italian":
      return "Italian";
    case "asian":
      return "Asian";
    case "arabic":
      return "Arabic";
    case "mexican":
      return "Mexican";
    case "indian":
      return "Indian";
    default:
      return "International";
  }
}

export const PantryChef = () => {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<"upload" | "preferences" | "recipe">(
    "upload"
  );
  const [isScanning, setIsScanning] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [newIngredientName, setNewIngredientName] = useState("");

  const ingredients = useAppStore((state) => state.ingredients);
  const addIngredient = useAppStore((state) => state.addIngredient);
  const removeIngredient = useAppStore((state) => state.removeIngredient);
  const clearIngredients = useAppStore((state) => state.clearIngredients);
  const preferences = useAppStore((state) => state.preferences);
  const setPreferences = useAppStore((state) => state.setPreferences);
  const currentRecipe = useAppStore((state) => state.currentRecipe);
  const setCurrentRecipe = useAppStore((state) => state.setCurrentRecipe);
  const sessionId = useAppStore((state) => state.sessionId);
  const setSessionId = useAppStore((state) => state.setSessionId);

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsScanning(true);

    try {
      // 1) تحويل الصورة إلى base64 (data URL)
      const reader = new FileReader();
      reader.readAsDataURL(file);

      await new Promise<void>((resolve, reject) => {
        reader.onload = () => resolve();
        reader.onerror = () => reject(reader.error);
      });

      const imageData = reader.result as string;

      // 2) استدعاء الباك إند /api/chef/analyze
      const analyzeResult = await analyzeImage(imageData);
      console.log("ANALYZE RESULT >>>", analyzeResult);

      if (
        !analyzeResult.detected_ingredients ||
        analyzeResult.detected_ingredients.length === 0
      ) {
        throw new Error("No ingredients detected");
      }

      // 3) حفظ session_id في Zustand
      setSessionId(analyzeResult.session_id);

      // 4) تنظيف المكونات القديمة
      clearIngredients();

      // 5) تحويل مخرجات الباك إلى شكل يناسب الستور
      analyzeResult.detected_ingredients.forEach((ing, index) => {
        const displayName =
          ing.name_ar ||
          ing.name_en ||
          ing.name ||
          `Ingredient ${index + 1}`;

        const qtyNumber =
          typeof ing.quantity_estimate === "string"
            ? parseFloat(ing.quantity_estimate)
            : ing.quantity_estimate ?? undefined;

        addIngredient({
          id: crypto.randomUUID(),
          name: displayName,
          quantity:
            typeof qtyNumber === "number" && !Number.isNaN(qtyNumber)
              ? qtyNumber
              : undefined,
          unit: ing.unit ?? undefined,
        });
      });

      toast({
        title: "Ingredients Detected!",
        description: `Found ${analyzeResult.detected_ingredients.length} ingredients`,
      });

      setStep("preferences");
    } catch (error) {
      console.error("Ingredient detection error:", error);
      toast({
        title: "Scan Failed",
        description:
          error instanceof Error
            ? error.message
            : "Could not detect ingredients. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsScanning(false);
    }
  };

  const handleAddManualIngredient = () => {
    if (!newIngredientName.trim()) return;

    addIngredient({
      id: crypto.randomUUID(),
      name: newIngredientName.trim(),
    });

    setNewIngredientName("");
  };

  const handleGenerateRecipe = async () => {
    if (!sessionId) {
      toast({
        title: "No session",
        description: "Please scan your ingredients first.",
        variant: "destructive",
      });
      return;
    }

    setIsGenerating(true);

    try {
      const payload: GenerateRecipePayload = {
        session_id: sessionId,
        meal_type: mapMealType(preferences.mealType),
        time_limit: mapCookingTime(preferences.cookingTime),
        servings: mapServings(preferences.servings),
        cuisines: [mapCuisine(preferences.cuisine)],
      };

      const recipeData = await generateRecipe(payload);

      if (!recipeData.recipe_name) {
        throw new Error("No recipe generated");
      }

      const finalRecipe = {
        id: crypto.randomUUID(),
        type: "PANTRY" as const,
        title: recipeData.recipe_name,
        description: `وصفة ${
          recipeData.cuisine_type || ""
        } محضّرة من مكونات ثلاجتك`,
        ingredients: recipeData.ingredients_needed.map((ing, idx) => {
          const name =
            ing.name_ar || ing.name_en || ing.name || `Ingredient ${idx + 1}`;

          const qty =
            typeof ing.quantity_estimate === "string"
              ? ing.quantity_estimate
              : ing.quantity_estimate != null
              ? String(ing.quantity_estimate)
              : "";

          const unit = ing.unit || "";
          const amount = `${qty} ${unit}`.trim() || "حسب الرغبة";

          return { name, amount };
        }),
        instructions: recipeData.preparation_steps || [],
        prepTimeMinutes: recipeData.cooking_time_minutes || 30,
        servings: payload.servings,
        calories: 0,
      };

      setCurrentRecipe(finalRecipe);
      useAppStore.getState().incrementRecipesGenerated();
      useAppStore.getState().addGeneratedRecipeId(recipeData.recipe_name);
      setStep("recipe");

      toast({
        title: "Recipe Generated!",
        description: "Your delicious recipe is ready",
      });
    } catch (error) {
      console.error("Recipe generation error:", error);
      toast({
        title: "Generation Failed",
        description:
          error instanceof Error
            ? error.message
            : "Could not generate recipe. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  if (step === "recipe" && currentRecipe) {
    return (
      <RecipeView
        recipe={currentRecipe}
        onBack={() => setStep("preferences")}
        onNewRecipe={handleGenerateRecipe}
        type="pantry"
      />
    );
  }

  return (
    <div className="min-h-screen pb-32 pt-4 px-4">
      <div className="max-w-md mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={() =>
              step === "preferences" ? setStep("upload") : setLocation("/generate")
            }
            className="ios-button p-2 bg-muted"
          >
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-2xl font-bold">Pantry Chef</h1>
        </div>

        {step === "upload" && (
          <div className="space-y-4">
            <div className="ios-card p-8 text-center space-y-4">
              <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-primary to-primary-light flex items-center justify-center">
                <Camera size={40} className="text-white" />
              </div>

              <div className="space-y-2">
                <h3 className="text-xl font-semibold">Scan Your Ingredients</h3>
                <p className="text-sm text-muted-foreground">
                  Take a photo of your ingredients and I'll detect them for you
                </p>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleImageUpload}
                className="hidden"
              />

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isScanning}
                className="ios-button bg-primary text-primary-foreground px-8 py-4 text-lg w-full"
              >
                {isScanning ? "Scanning..." : "Upload / Take Photo"}
              </button>

              <button
                onClick={() => setStep("preferences")}
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Skip photo, add ingredients manually
              </button>
            </div>
          </div>
        )}

        {step === "preferences" && (
          <div className="space-y-6">
            {/* Ingredients List */}
            <div className="ios-card p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Ingredients</h3>
                {ingredients.length > 0 && (
                  <button
                    onClick={clearIngredients}
                    className="text-xs text-destructive hover:underline"
                  >
                    Clear all
                  </button>
                )}
              </div>

              <div className="space-y-2">
                {ingredients.map((ing) => (
                  <div
                    key={ing.id}
                    className="flex items-center justify-between bg-muted rounded-xl px-4 py-3"
                  >
                    <span className="font-medium">
                      {ing.name}
                      {ing.quantity &&
                        ` (${ing.quantity} ${ing.unit || ""})`}
                    </span>
                    <button
                      onClick={() => removeIngredient(ing.id)}
                      className="text-destructive hover:bg-destructive/10 rounded-full p-1"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={newIngredientName}
                  onChange={(e) => setNewIngredientName(e.target.value)}
                  onKeyPress={(e) =>
                    e.key === "Enter" && handleAddManualIngredient()
                  }
                  placeholder="Add ingredient..."
                  className="flex-1 px-4 py-3 rounded-xl border border-input bg-background"
                />
                <button
                  onClick={handleAddManualIngredient}
                  className="ios-button bg-primary text-primary-foreground px-4"
                >
                  <Plus size={20} />
                </button>
              </div>
            </div>

            {/* Meal Type */}
            <div className="ios-card p-4 space-y-4">
              <h3 className="font-semibold">Meal Type</h3>
              <div className="flex gap-2">
                {[
                  { value: "breakfast", label: "Breakfast" },
                  { value: "lunch", label: "Lunch" },
                  { value: "dinner", label: "Dinner" },
                  { value: "snack", label: "Snack" },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() =>
                      setPreferences({ mealType: option.value as Preferences["mealType"] })
                    }
                    className={`ios-button flex-1 py-2 ${
                      preferences.mealType === option.value
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Cooking Time */}
            <div className="ios-card p-4 space-y-4">
              <h3 className="font-semibold">Cooking Time</h3>
              <div className="flex gap-2">
                {[
                  { value: "under5", label: "Under 5 min" },
                  { value: "around30", label: "Around 30 min" },
                  { value: "over30", label: "Over 30 min" },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() =>
                      setPreferences({
                        cookingTime: option.value as Preferences["cookingTime"],
                      })
                    }
                    className={`ios-button flex-1 py-2 text-sm ${
                      preferences.cookingTime === option.value
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Servings */}
            <div className="ios-card p-4 space-y-4">
              <h3 className="font-semibold">Servings</h3>
              <div className="flex gap-2">
                {[
                  { value: "onlyMe", label: "Only Me" },
                  { value: "2-3", label: "2-3" },
                  { value: "more3", label: "More than 3" },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() =>
                      setPreferences({
                        servings: option.value as Preferences["servings"],
                      })
                    }
                    className={`ios-button flex-1 py-2 ${
                      preferences.servings === option.value
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Cuisine */}
            <div className="ios-card p-4 space-y-4">
              <h3 className="font-semibold">Cuisine</h3>
              <select
                value={preferences.cuisine}
                onChange={(e) =>
                  setPreferences({
                    cuisine: e.target.value as Preferences["cuisine"],
                  })
                }
                className="w-full px-4 py-3 rounded-xl border border-input bg-background"
              >
                <option value="italian">Italian</option>
                <option value="asian">Asian</option>
                <option value="arabic">Arabic</option>
                <option value="mexican">Mexican</option>
                <option value="indian">Indian</option>
              </select>
            </div>

            <button
              onClick={handleGenerateRecipe}
              disabled={isGenerating || ingredients.length === 0}
              className="ios-button bg-primary text-primary-foreground px-8 py-4 text-lg w-full disabled:opacity-50"
            >
              {isGenerating ? "Generating..." : "Generate Recipe"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
