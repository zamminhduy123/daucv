"use client";

import { CheckCircle2 } from "lucide-react";
import { CV_DESIGNS } from "@/lib/cv-designs";
import type { CVDesign } from "@/types";

function DesignThumbnail({ design }: { design: CVDesign }) {
  if (design === "modern_professional") {
    return <div className="flex h-36 w-full overflow-hidden rounded-xl border border-[#6A9B5E]/15 bg-white shadow-inner shadow-gray-100/70">
      <div className="flex w-[32%] flex-col bg-[#6A9B5E] px-3 py-3 text-white">
        <div className="mb-3 h-8 w-8 rounded-full border border-white/70 bg-white/15" />
        <div className="mb-3 space-y-1.5"><div className="h-2.5 w-11/12 rounded-sm bg-white" /><div className="h-1.5 w-8/12 rounded-sm bg-white/70" /></div>
        <div className="space-y-1.5"><div className="h-1 w-full rounded-sm bg-white/55" /><div className="h-1 w-10/12 rounded-sm bg-white/55" /><div className="h-1 w-9/12 rounded-sm bg-white/55" /></div>
        <div className="mt-auto flex flex-wrap gap-1"><div className="h-2.5 w-8 rounded-full bg-white/20" /><div className="h-2.5 w-10 rounded-full bg-white/20" /></div>
      </div>
      <div className="w-[68%] space-y-3 px-4 py-3">{["w-16", "w-12", "w-14"].map((width, index) => <div key={index}><div className={`mb-1.5 h-1.5 rounded-sm bg-[#6A9B5E] ${width}`} /><div className="space-y-1"><div className="h-1 w-full rounded-sm bg-gray-200" /><div className="h-1 w-11/12 rounded-sm bg-gray-200" />{index === 0 && <div className="h-1 w-4/5 rounded-sm bg-gray-200" />}</div></div>)}</div>
    </div>;
  }

  if (design === "compact") {
    return <div className="h-36 w-full overflow-hidden rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-inner shadow-gray-100/60">
      <div className="mb-2 space-y-1"><div className="flex items-end justify-between gap-3"><div className="h-2.5 w-2/5 rounded-sm bg-gray-800" /><div className="h-1 w-1/3 rounded-sm bg-gray-300" /></div><div className="h-1 w-full bg-[#4A90A4]" /></div>
      <div className="space-y-1.5">{["w-16", "w-10", "w-12", "w-14"].map((width, index) => <div key={index} className="border-l-2 border-[#4A90A4] pl-2"><div className={`mb-1 h-1.5 rounded-sm bg-gray-700 ${width}`} />{index === 1 ? <div className="grid grid-cols-3 gap-1">{Array.from({ length: 6 }).map((_, chip) => <div key={chip} className="h-2 rounded-full bg-gray-100" />)}</div> : <div className="space-y-0.5"><div className="h-0.5 w-full rounded-sm bg-gray-200" /><div className="h-0.5 w-10/12 rounded-sm bg-gray-200" /></div>}</div>)}</div>
    </div>;
  }

  return <div className="h-36 w-full overflow-hidden rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-inner shadow-gray-100/60">
    <div className="mb-2 space-y-1.5"><div className="mx-auto h-2.5 w-3/5 rounded-sm bg-gray-500" /><div className="mx-auto h-1.5 w-2/5 rounded-sm bg-gray-200" /></div><div className="mb-3 h-px w-full bg-gray-300" />
    <div className="space-y-3">{["w-16", "w-12", "w-14"].map((width, index) => <div key={index}><div className="mb-1 flex items-center gap-2"><div className={`h-1.5 rounded-sm bg-gray-700 ${width}`} /><div className="h-px flex-1 bg-gray-300" /></div><div className="space-y-1 pl-1"><div className="h-1 w-full rounded-sm bg-gray-200" /><div className="h-1 w-10/12 rounded-sm bg-gray-200" />{index === 0 && <div className="h-1 w-4/5 rounded-sm bg-gray-200" />}</div></div>)}</div>
  </div>;
}

export default function CVDesignSelector({ selected, onChange, disabled = false }: { selected: CVDesign; onChange: (design: CVDesign) => void; disabled?: boolean }) {
  return <div className="grid gap-3 md:grid-cols-3">
    {CV_DESIGNS.map((design) => <button key={design.value} type="button" onClick={() => onChange(design.value)} disabled={disabled} aria-pressed={selected === design.value} className={`group relative rounded-2xl border bg-white p-3 text-left transition-all hover:shadow-lg disabled:cursor-wait disabled:opacity-70 ${selected === design.value ? "border-[#6A9B5E] shadow-md ring-2 ring-[#6A9B5E]" : "border-gray-100 hover:border-gray-200"}`}>
      {selected === design.value && <CheckCircle2 size={20} className="absolute right-3 top-3 fill-[#6A9B5E] text-white" />}
      <DesignThumbnail design={design.value} />
      <h3 className="mt-3 text-sm font-black">{design.label}</h3>
      <p className="mt-1 text-[11px] font-medium leading-relaxed text-gray-500">{design.description}</p>
    </button>)}
  </div>;
}
