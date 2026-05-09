import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function wordCount(text: string): string {
  if (!text) return "0 words";
  const count = text.trim().split(/\s+/).filter(word => word.length > 0).length;
  return `${count} ${count === 1 ? "word" : "words"}`;
}
