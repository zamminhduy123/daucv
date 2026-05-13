"use client";

import { useEffect, useState } from "react";

interface Heading {
  level: number;
  text: string;
  id: string;
}

export function BlogTOC({ headings }: { headings: Heading[] }) {
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    // If no headings, do nothing
    if (headings.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Find the visible elements
        const visibleEntries = entries.filter((entry) => entry.isIntersecting);
        if (visibleEntries.length > 0) {
          // If multiple are visible, pick the first one
          setActiveId(visibleEntries[0].target.id);
        }
      },
      { 
        rootMargin: "-100px 0px -60% 0px",
        threshold: 0
      }
    );

    headings.forEach((heading) => {
      const el = document.getElementById(heading.id);
      if (el) observer.observe(el);
    });

    // Set initial active id if none is set and headings exist
    if (!activeId && headings.length > 0) {
      setActiveId(headings[0].id);
    }

    return () => observer.disconnect();
  }, [headings]);

  if (headings.length === 0) return null;

  return (
    <div className="sticky top-24 bg-white p-6 rounded-3xl shadow-sm border border-[#2F4F4F]/5">
      <h3 className="text-xl font-bold text-[#2F4F4F] mb-6">Mục lục</h3>
      <nav className="flex flex-col relative">
        {/* Faint vertical line background */}
        <div className="absolute left-[1px] top-2 bottom-2 w-[2px] bg-gray-100 rounded-full" />
        
        {headings.map((heading, i) => {
          const isActive = activeId === heading.id || (activeId === "" && i === 0);
          return (
            <a 
              key={i} 
              href={`#${heading.id}`}
              className={`
                relative py-3.5 pr-4 pl-6 text-sm transition-all duration-200 line-clamp-2
                ${heading.level === 3 ? 'ml-4' : ''}
                ${isActive ? 'text-[#2E7D32] font-semibold' : 'text-gray-500 font-medium hover:text-[#2E7D32]'}
              `}
            >
              {/* Active Indicator Line */}
              {isActive && (
                <div className="absolute left-[1px] top-2 bottom-2 w-[2px] bg-[#2E7D32] rounded-full z-10" />
              )}
              {heading.text}
            </a>
          );
        })}
      </nav>
    </div>
  );
}
