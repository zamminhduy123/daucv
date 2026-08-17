import { toast as sonnerToast } from "sonner"

export function useToast() {
  const toast = ({ title, description, variant, ...props }: { title?: string; description?: string; variant?: string; [key: string]: unknown }) => {
    if (variant === "destructive") {
      return sonnerToast.error(title, {
        description,
        ...props,
      })
    }
    return sonnerToast(title, {
      description,
      ...props,
    })
  }

  return {
    toast,
    dismiss: (id?: string) => sonnerToast.dismiss(id),
    toasts: [] // Not fully implementing the state for now as sonner handles it
  }
}
