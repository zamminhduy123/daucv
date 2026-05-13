import React from 'react';
import { Check } from 'lucide-react';

export interface ChecklistSectionProps {
  title?: string;
  items: string[];
}

export function ChecklistSection({ title, items }: ChecklistSectionProps) {
  if (!items || items.length === 0) return null;

  return (
    <div className="bg-white border border-[#2E7D32]/20 rounded-3xl p-8 my-12 shadow-sm">
      {title && <h3 className="text-xl font-bold text-[#2F4F4F] mb-6 border-none pb-0 m-0">{title}</h3>}
      <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 m-0 p-0 list-none">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-3 m-0 p-0">
            <div className="w-6 h-6 rounded-full bg-[#E8F5E9] text-[#2E7D32] flex items-center justify-center flex-shrink-0 mt-0.5">
              <Check className="w-4 h-4" />
            </div>
            <span className="text-gray-700 leading-relaxed font-medium">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
