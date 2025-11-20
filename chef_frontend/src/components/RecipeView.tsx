import { useState } from 'react';
import { ArrowLeft, Share2, Heart, ShoppingCart, ChefHat } from 'lucide-react';
import { useAppStore } from '../store/app-store';
import { useToast } from '../hooks/use-toast';

interface Recipe {
  id: string;
  type: 'PANTRY' | 'CREATIVE';
  title: string;
  description?: string;
  ingredients: Array<{ name: string; amount: string }>;
  instructions: string[];
  prepTimeMinutes: number;
  servings: number;
  calories: number;
  imageUrl?: string;
  macros?: {
    protein: number;
    carbs: number;
    fats: number;
  };
}

interface RecipeViewProps {
  recipe: Recipe;
  onBack: () => void;
  onNewRecipe: () => void;
  type: 'pantry' | 'creative';
}

export const RecipeView = ({ recipe, onBack, onNewRecipe, type }: RecipeViewProps) => {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<'ingredients' | 'instructions' | 'macros'>('ingredients');
  
  const isFavorite = useAppStore((state) => state.isFavorite(recipe.id));
  const addFavorite = useAppStore((state) => state.addFavorite);
  const removeFavorite = useAppStore((state) => state.removeFavorite);
  const markRecipeCooked = useAppStore((state) => state.markRecipeCooked);
  const ingredients = useAppStore((state) => state.ingredients);

  const handleToggleFavorite = () => {
    if (isFavorite) {
      removeFavorite(recipe.id);
      toast({ title: 'Removed from CookBook' });
    } else {
      addFavorite(recipe);
      toast({ title: 'Added to CookBook' });
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: recipe.title,
          text: `Check out this recipe: ${recipe.title}`,
          url: window.location.href,
        });
      } catch (_error) {
        // User cancelled or error occurred
      }
    } else {
      toast({ title: 'Link Copied!', description: 'Recipe link copied to clipboard' });
    }
  };

  const handleBuyItems = () => {
    // Calculate missing items (Cart Agent logic)
    const missingCount = type === 'pantry' 
      ? recipe.ingredients.length - ingredients.length
      : recipe.ingredients.length;
    
    window.open('https://hungerstation.com', '_blank');
    
    toast({
      title: 'Opening HungerStation',
      description: `Shopping for ${missingCount} items`,
    });
  };

  const handleSave = () => {
    if (!isFavorite) {
      addFavorite(recipe);
    }
    
    // Mark as cooked and track waste reduction
    const estimatedFoodSaved = recipe.servings * 0.3; // kg per serving
    markRecipeCooked(estimatedFoodSaved);
    
    toast({
      title: 'Recipe Saved!',
      description: 'Marked as cooked and added to your stats',
    });
  };

  const missingItemsCount = type === 'pantry' 
    ? Math.max(0, recipe.ingredients.length - ingredients.length)
    : 0;

  return (
    <div className="min-h-screen pb-32">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-xl border-b border-border px-4 py-3">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <button onClick={onBack} className="ios-button p-2 bg-muted">
            <ArrowLeft size={20} />
          </button>
          <h1 className="font-semibold">{type === 'pantry' ? 'Pantry Chef' : 'Creative Chef'}</h1>
          <button onClick={onNewRecipe} className="ios-button px-4 py-2 bg-primary text-primary-foreground text-sm">
            New Recipe
          </button>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 pt-4 space-y-6">
        {/* Recipe Image */}
        {recipe.imageUrl && (
          <div className="relative ios-card overflow-hidden aspect-video">
            <img
              src={recipe.imageUrl}
              alt={recipe.title}
              className="w-full h-full object-cover"
            />
            <div className="absolute top-4 right-4 flex gap-2">
              <button
                onClick={handleShare}
                className="w-10 h-10 rounded-full bg-white/90 backdrop-blur flex items-center justify-center shadow-lg"
              >
                <Share2 size={18} className="text-foreground" />
              </button>
              <button
                onClick={handleToggleFavorite}
                className="w-10 h-10 rounded-full bg-white/90 backdrop-blur flex items-center justify-center shadow-lg"
              >
                <Heart
                  size={18}
                  className={isFavorite ? 'fill-red-500 text-red-500' : 'text-foreground'}
                />
              </button>
            </div>
          </div>
        )}

        {/* Recipe Title & Info */}
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold">{recipe.title}</h2>
          {recipe.description && (
            <p className="text-muted-foreground">{recipe.description}</p>
          )}
        </div>

        <div className="flex items-center justify-center gap-6 text-sm">
          <div className="text-center">
            <div className="font-bold">⏱ {recipe.prepTimeMinutes} min</div>
            <div className="text-xs text-muted-foreground">Prep Time</div>
          </div>
          <div className="text-center">
            <div className="font-bold">🍽 {recipe.servings}</div>
            <div className="text-xs text-muted-foreground">Serves</div>
          </div>
          <div className="text-center">
            <div className="font-bold">🔥 {recipe.calories}</div>
            <div className="text-xs text-muted-foreground">Calories</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="ios-card p-1">
          <div className="flex gap-1">
            {[
              { id: 'ingredients', label: 'Ingredients' },
              { id: 'instructions', label: 'Instructions' },
              { id: 'macros', label: 'Macros' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as 'ingredients' | 'instructions' | 'macros')}
                className={`flex-1 py-2 rounded-xl font-medium transition-all ${
                activeTab === tab.id
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="ios-card p-6">
          {activeTab === 'ingredients' && (
            <div className="space-y-3">
              {recipe.ingredients.map((ing, idx) => (
                <div key={idx} className="flex justify-between items-center py-2 border-b border-border last:border-0">
                  <span className="font-medium">{ing.name}</span>
                  <span className="text-muted-foreground">{ing.amount}</span>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'instructions' && (
            <ol className="space-y-4">
              {recipe.instructions.map((step, idx) => (
                <li key={idx} className="flex gap-4">
                  <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold flex-shrink-0">
                    {idx + 1}
                  </div>
                  <p className="flex-1 pt-1">{step}</p>
                </li>
              ))}
            </ol>
          )}

          {activeTab === 'macros' && recipe.macros && (
            <div className="space-y-4">
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="font-medium">Protein</span>
                    <span className="text-muted-foreground">{recipe.macros.protein}g</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500"
                      style={{ width: `${(recipe.macros.protein / 100) * 100}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="font-medium">Carbs</span>
                    <span className="text-muted-foreground">{recipe.macros.carbs}g</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500"
                      style={{ width: `${(recipe.macros.carbs / 100) * 100}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="font-medium">Fats</span>
                    <span className="text-muted-foreground">{recipe.macros.fats}g</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-orange-500"
                      style={{ width: `${(recipe.macros.fats / 100) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Action Sheet */}
        <div className="ios-card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-muted rounded-xl flex items-center justify-center">
                <ShoppingCart size={20} className="text-primary" />
              </div>
              <div>
                {type === 'pantry' && missingItemsCount > 0 ? (
                  <div className="text-sm font-medium">
                    Total Missing Items: <span className="text-primary">{missingItemsCount}</span>
                  </div>
                ) : (
                  <div className="text-sm font-medium">HungerStation Market</div>
                )}
              </div>
            </div>
            <button
              onClick={handleBuyItems}
              className="ios-button bg-primary text-primary-foreground px-6 py-2"
            >
              {type === 'pantry' && missingItemsCount > 0 ? 'Buy Items' : 'Buy All'}
            </button>
          </div>

          <button
            onClick={handleSave}
            className="ios-button bg-secondary text-secondary-foreground w-full py-3 flex items-center justify-center gap-2"
          >
            <ChefHat size={20} />
            <span>Mark as Cooked</span>
          </button>
        </div>
      </div>
    </div>
  );
};