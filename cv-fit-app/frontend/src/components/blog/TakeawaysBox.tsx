import React from 'react';
import { CheckCircle2 } from 'lucide-react';

export interface TakeawaysBoxProps {
  takeaways: string[];
}

export function TakeawaysBox({ takeaways }: TakeawaysBoxProps) {
  if (!takeaways || takeaways.length === 0) return null;

  return (
    <div className="bg-[#E8F5E9]/50 border border-[#2E7D32]/20 rounded-2xl p-6 md:p-8 my-10">
      <h3 className="text-xl font-bold text-[#2F4F4F] mb-6 flex items-center gap-2 m-0 border-none pb-0">
        <CheckCircle2 className="w-6 h-6 text-[#2E7D32]" />
        Những ý chính bạn sẽ nhận được
      </h3>
      <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 m-0 p-0 list-none">
        {takeaways.map((takeaway, i) => (
          <li key={i} className="flex items-start gap-3 text-gray-700 m-0 p-0">
            <div className="w-1.5 h-1.5 rounded-full bg-[#2E7D32] mt-2.5 flex-shrink-0" />
            <span className="font-medium leading-snug">{takeaway}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
