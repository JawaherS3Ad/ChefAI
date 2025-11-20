// src/store/app-store.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";


interface Ingredient {
  id: string;
  name: string;
  quantity?: number;
  unit?: string;
}

interface Recipe {
  id: string;
  type: "PANTRY" | "CREATIVE";
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

interface Preferences {
  mealType: "breakfast" | "lunch" | "dinner" | "snack";
  cookingTime: "under5" | "around30" | "over30";
  servings: "onlyMe" | "2-3" | "more3";
  cuisine: "italian" | "asian" | "arabic" | "mexican" | "indian";
}

interface AppState {
  // Ingredients
  ingredients: Ingredient[];
  addIngredient: (ingredient: Ingredient) => void;
  removeIngredient: (id: string) => void;
  updateIngredient: (id: string, updates: Partial<Ingredient>) => void;
  clearIngredients: () => void;

  // Preferences
  preferences: Preferences;
  setPreferences: (prefs: Partial<Preferences>) => void;

  // Current Recipe
  currentRecipe: Recipe | null;
  setCurrentRecipe: (recipe: Recipe | null) => void;

  // Session from backend
  sessionId: string | null;
  setSessionId: (id: string | null) => void;

  // Favorites
  favorites: Recipe[];
  addFavorite: (recipe: Recipe) => void;
  removeFavorite: (id: string) => void;
  isFavorite: (id: string) => boolean;

  // Achievements
  stats: {
    recipesGenerated: number;
    recipesCooked: number;
    foodSavedKg: number;
    co2SavedKg: number;
  };
  incrementRecipesGenerated: () => void;
  markRecipeCooked: (foodSavedKg: number) => void;

  // Session tracking for unique recipe generation
  generatedRecipeIds: string[];
  addGeneratedRecipeId: (id: string) => void;
  clearGeneratedRecipeIds: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Ingredients
      ingredients: [],
      addIngredient: (ingredient) =>
        set((state) => ({ ingredients: [...state.ingredients, ingredient] })),
      removeIngredient: (id) =>
        set((state) => ({
          ingredients: state.ingredients.filter((i) => i.id !== id),
        })),
      updateIngredient: (id, updates) =>
        set((state) => ({
          ingredients: state.ingredients.map((i) =>
            i.id === id ? { ...i, ...updates } : i
          ),
        })),
      clearIngredients: () => set({ ingredients: [] }),

      // Preferences
      preferences: {
        mealType: "dinner",
        cookingTime: "around30",
        servings: "onlyMe",
        cuisine: "italian",
      },
      setPreferences: (prefs) =>
        set((state) => ({
          preferences: { ...state.preferences, ...prefs },
        })),

      // Current Recipe
      currentRecipe: null,
      setCurrentRecipe: (recipe) => set({ currentRecipe: recipe }),

      // Backend Session
      sessionId: null,
      setSessionId: (id) => set({ sessionId: id }),

      // Favorites
      favorites: [],
      addFavorite: (recipe) =>
        set((state) => {
          if (!state.favorites.find((f) => f.id === recipe.id)) {
            return { favorites: [...state.favorites, recipe] };
          }
          return state;
        }),
      removeFavorite: (id) =>
        set((state) => ({
          favorites: state.favorites.filter((f) => f.id !== id),
        })),
      isFavorite: (id) => get().favorites.some((f) => f.id === id),

      // Achievements
      stats: {
        recipesGenerated: 0,
        recipesCooked: 0,
        foodSavedKg: 0,
        co2SavedKg: 0,
      },
      incrementRecipesGenerated: () =>
        set((state) => ({
          stats: {
            ...state.stats,
            recipesGenerated: state.stats.recipesGenerated + 1,
          },
        })),
      markRecipeCooked: (foodSavedKg) =>
        set((state) => ({
          stats: {
            ...state.stats,
            recipesCooked: state.stats.recipesCooked + 1,
            foodSavedKg: state.stats.foodSavedKg + foodSavedKg,
            co2SavedKg: state.stats.co2SavedKg + foodSavedKg * 2.5,
          },
        })),

      // Session tracking
      generatedRecipeIds: [],
      addGeneratedRecipeId: (id) =>
        set((state) => ({
          generatedRecipeIds: [...state.generatedRecipeIds, id],
        })),
      clearGeneratedRecipeIds: () => set({ generatedRecipeIds: [] }),
    }),
    {
      name: "chefai-storage",
      partialize: (state) => ({
        favorites: state.favorites,
        stats: state.stats,
        preferences: state.preferences,
      }),
    }
  )
);
export type { Preferences };
