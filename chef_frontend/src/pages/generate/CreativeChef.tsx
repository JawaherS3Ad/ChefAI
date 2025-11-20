import { useState } from "react";
import { ArrowLeft, Sparkles } from "lucide-react";
import { useLocation } from "wouter";
import { useAppStore } from "../../store/app-store";
import { useToast } from "../../hooks/use-toast";
import { RecipeView } from "../../components/RecipeView";

export const CreativeChef = () => {
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  const [step, setStep] = useState<"input" | "recipe">("input");
  const [dream, setDream] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  const preferences = useAppStore((state) => state.preferences);
  const setPreferences = useAppStore((state) => state.setPreferences);
  const currentRecipe = useAppStore((state) => state.currentRecipe);
  const setCurrentRecipe = useAppStore((state) => state.setCurrentRecipe);

  const handleGenerateCreativeRecipe = async () => {
    if (!dream.trim()) {
      toast({
        title: "Describe Your Dream",
        description: "Please tell me about your dream dish",
        variant: "destructive",
      });
      return;
    }

    setIsGenerating(true);

    try {
      // ديمو بسيط بدون استدعاء باك إند
      await new Promise((r) => setTimeout(r, 1200));

      const demoRecipe = {
        id: crypto.randomUUID(),
        type: "CREATIVE" as const,
        title: "Dreamy Flying Carpet Dinner",
        description: dream,
        ingredients: [
          { name: "Saffron rice", amount: "2 cups" },
          { name: "Grilled chicken", amount: "300 g" },
          { name: "Roasted vegetables", amount: "1 tray" },
        ],
        instructions: [
          "Cook the saffron rice until fluffy.",
          "Grill the chicken with warm spices.",
          "Roast mixed vegetables until caramelized.",
          "Serve everything on one big sharing plate and enjoy.",
        ],
        prepTimeMinutes: 35,
        servings: preferences.servings === "onlyMe" ? 1 : 3,
        calories: 650,
      };

      setCurrentRecipe(demoRecipe);
      useAppStore.getState().incrementRecipesGenerated();
      setStep("recipe");

      toast({
        title: "Dream Recipe Created!",
        description: "This is a demo recipe (frontend-only).",
      });
    } catch (error) {
      console.error("Creative demo error:", error);
      toast({
        title: "Generation Failed",
        description: "Could not generate demo recipe.",
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
        onBack={() => setStep("input")}
        onNewRecipe={handleGenerateCreativeRecipe}
        type="creative"
      />
    );
  }

  return (
    <div className="min-h-screen pb-32 pt-4 px-4">
      <div className="max-w-md mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setLocation("/generate")}
            className="ios-button p-2 bg-muted"
          >
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-2xl font-bold">Creative Chef (Demo)</h1>
        </div>

        <div className="space-y-6">
          {/* Dream Input */}
          <div className="ios-card p-8 space-y-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-secondary to-accent flex items-center justify-center">
              <Sparkles size={32} className="text-white" />
            </div>

            <div className="space-y-2 text-center">
              <h3 className="text-xl font-semibold">Describe Your Dream</h3>
              <p className="text-sm text-muted-foreground">
                This screen is a demo only. The real backend magic is on Pantry
                Chef.
              </p>
            </div>

            <textarea
              value={dream}
              onChange={(e) => setDream(e.target.value)}
              placeholder="E.g., A dinner on a flying carpet at sunset..."
              className="w-full px-4 py-3 rounded-xl border border-input bg-background min-h-[120px] resize-none"
            />
          </div>

          {/* Preferences (بس الوقت + الأشخاص مثل قبل) */}
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
                      cookingTime: option.value as any,
                    })
                  }
                  className={`ios-button flex-1 py-2 text-sm ${
                    preferences.cookingTime === option.value
                      ? "bg-secondary text-secondary-foreground"
                      : "bg-muted"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

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
                    setPreferences({ servings: option.value as any })
                  }
                  className={`ios-button flex-1 py-2 ${
                    preferences.servings === option.value
                      ? "bg-secondary text-secondary-foreground"
                      : "bg-muted"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleGenerateCreativeRecipe}
            disabled={isGenerating || !dream.trim()}
            className="ios-button bg-gradient-to-r from-secondary to-accent text-white px-8 py-4 text-lg w-full disabled:opacity-50"
          >
            {isGenerating ? "Creating Magic..." : "Generate Dream Recipe"}
          </button>
        </div>
      </div>
    </div>
  );
};
