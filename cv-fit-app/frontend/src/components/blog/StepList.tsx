import React from 'react';

export interface Step {
  title: string;
  description: string;
  image?: string;
}

export interface StepListProps {
  title?: string;
  steps: Step[];
}

export function StepList({ title = "3 bước nâng cấp CV với Đậu", steps }: StepListProps) {
  if (!steps || steps.length === 0) return null;

  return (
    <div className="my-12">
      {title && <h3 className="text-2xl font-bold text-[#2F4F4F] mb-8">{title}</h3>}
      <div className="flex flex-col gap-6">
        {steps.map((step, i) => (
          <div key={i} className="bg-[#F9F9F2] border border-[#2F4F4F]/5 rounded-3xl p-6 md:p-8 shadow-sm flex flex-col md:flex-row items-center gap-8">
            <div className="flex-1 flex gap-6">
              <div className="w-12 h-12 flex-shrink-0 bg-[#2E7D32] text-white rounded-full flex items-center justify-center font-bold text-xl shadow-sm mt-1">
                {i + 1}
              </div>
              <div>
                <h4 className="text-xl font-bold text-[#2F4F4F] mb-3 mt-0">{step.title}</h4>
                <p className="text-gray-600 leading-relaxed m-0">{step.description}</p>
              </div>
            </div>
            {step.image && (
              <div className="w-full md:w-1/3 aspect-video md:aspect-[4/3] rounded-2xl overflow-hidden shadow-sm flex-shrink-0">
                <img src={step.image} alt={step.title} className="w-full h-full object-cover" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
