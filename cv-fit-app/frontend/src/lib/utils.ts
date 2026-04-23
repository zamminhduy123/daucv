import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Utility that merges Tailwind classes safely. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format a word count from a string. */
export function wordCount(text: string): string {
  const n = text.split(/\s+/).filter(Boolean).length;
  return n === 0 ? "Chưa có nội dung" : `${n} từ`;
}

/** Clamp a number between min and max. */
export function clamp(val: number, min: number, max: number): number {
  return Math.min(Math.max(val, min), max);
}
