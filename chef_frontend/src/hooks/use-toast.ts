// src/hooks/use-toast.ts
import { toast as sonnerToast } from "sonner";

export function useToast() {
  return {
    toast: (opts: {
      title?: string;
      description?: string;
      variant?: "default" | "destructive";
    }) => {
      sonnerToast(opts.title || "", {
        description: opts.description,
        className:
          opts.variant === "destructive"
            ? "bg-destructive text-destructive-foreground"
            : "",
      });
    },
  };
}
