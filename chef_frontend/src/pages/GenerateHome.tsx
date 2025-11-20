import { useLocation } from 'wouter';
import { ChefHat, Sparkles } from 'lucide-react';

export const GenerateHome = () => {
  const [, setLocation] = useLocation();

  return (
    <div className="min-h-screen pb-32 pt-8 px-4">
      <div className="max-w-md mx-auto space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-primary-light bg-clip-text text-transparent">
            Let's Cook Something Amazing
          </h1>
          <p className="text-muted-foreground">Choose your cooking style</p>
        </div>

        <div className="space-y-4">
          <button
            onClick={() => setLocation('/generate/pantry')}
            className="w-full ios-card p-6 text-left transition-transform active:scale-[0.98] hover:shadow-lg"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary to-primary-light flex items-center justify-center flex-shrink-0">
                <ChefHat className="text-white" size={24} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-bold mb-1">Pantry Chef</h3>
                <p className="text-sm text-muted-foreground">
                  Generate recipes using your ingredients
                </p>
              </div>
            </div>
          </button>

          <button
            onClick={() => setLocation('/generate/creative')}
            className="w-full ios-card p-6 text-left transition-transform active:scale-[0.98] hover:shadow-lg"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-secondary to-accent flex items-center justify-center flex-shrink-0">
                <Sparkles className="text-white" size={24} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-bold mb-1">Creative Chef</h3>
                <p className="text-sm text-muted-foreground">
                  Turn your dreams into delicious recipes
                </p>
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
};
