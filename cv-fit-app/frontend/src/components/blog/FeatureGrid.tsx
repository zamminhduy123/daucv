import React from 'react';
import * as LucideIcons from 'lucide-react';

export interface Feature {
  icon: string;
  title: string;
  description: string;
}

export interface FeatureGridProps {
  title?: string;
  features: Feature[];
}

export function FeatureGrid({ title = "AI giúp tối ưu CV như thế nào?", features }: FeatureGridProps) {
  if (!features || features.length === 0) return null;

  return (
    <div className="my-12">
      {title && <h3 className="text-2xl font-bold text-[#2F4F4F] mb-8 text-center">{title}</h3>}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {features.map((feature, i) => {
          // Dynamic icon resolution
          const IconComponent = (LucideIcons as any)[feature.icon] || LucideIcons.CheckCircle;
          
          return (
            <div key={i} className="bg-white border border-[#2F4F4F]/5 rounded-3xl p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-[#E8F5E9] text-[#2E7D32] rounded-2xl flex items-center justify-center mb-6">
                <IconComponent className="w-8 h-8" />
              </div>
              <h4 className="text-lg font-bold text-[#2F4F4F] mb-3">{feature.title}</h4>
              <p className="text-gray-600 text-sm leading-relaxed m-0">{feature.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
