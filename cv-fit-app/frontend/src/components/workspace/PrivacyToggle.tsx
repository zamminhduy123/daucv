"use client";

import { Eye, EyeOff } from "lucide-react";

/**
 * v1 privacy toggle. Renders as an eye icon button; toggles a field's
 * `hidden` flag on the in-memory draft. buildCVHtml and canonical export
 * skip hidden content, so this is the single control for "show / hide".
 */
export default function PrivacyToggle({
  hidden,
  onToggle,
  label,
  disabled = false,
}: {
  hidden: boolean;
  onToggle: (next: boolean) => void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      aria-pressed={hidden}
      aria-label={hidden ? `Hiện ${label || "trường này"}` : `Ẩn ${label || "trường này"}`}
      title={hidden ? "Hiện trường này" : "Ẩn trường này khỏi CV"}
      disabled={disabled}
      onClick={() => onToggle(!hidden)}
      className={`inline-flex items-center justify-center rounded-lg p-1.5 transition-colors ${
        hidden
          ? "text-amber-600 hover:bg-amber-50"
          : "text-gray-400 hover:bg-gray-100"
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {hidden ? <EyeOff size={15} /> : <Eye size={15} />}
    </button>
  );
}