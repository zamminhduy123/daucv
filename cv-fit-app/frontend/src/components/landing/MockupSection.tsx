import { Check } from "lucide-react";
import type { SkillBadge } from "@/types";

const SKILLS: SkillBadge[] = [
  { skill: "React & TypeScript", on: true },
  { skill: "Thiết kế hệ thống", on: true },
  { skill: "Tiếng Anh chuyên ngành", on: true },
  { skill: "GraphQL — cần thêm ngay", on: false },
];

export default function MockupSection() {
  return (
    <section
      className="max-w-7xl mx-auto relative"
      style={{ padding: "2rem 3rem 6rem" }}
    >
      {/* Green glow background */}
      <div
        className="absolute rounded-[32px]"
        style={{
          inset: "auto 0 0 0", height: "55%",
          backgroundColor: "#98C18E", opacity: 0.15,
        }}
      />

      {/* Card */}
      <div className="relative" style={{ padding: "3rem 4rem" }}>
        <div
          className="bg-white rounded-3xl overflow-hidden"
          style={{
            boxShadow: "0 32px 80px rgba(47,79,79,0.15)",
            border: "1px solid rgba(47,79,79,0.05)",
          }}
        >
          {/* Browser chrome */}
          <div
            className="flex items-center gap-2.5 border-b border-black/5"
            style={{ backgroundColor: "#F1F1F1", padding: "12px 18px" }}
          >
            <div className="flex gap-1.5">
              {["#FF5F57", "#FFBD2E", "#28C840"].map((c) => (
                <span
                  key={c}
                  className="block w-3 h-3 rounded-full"
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
            <div
              className="flex-1 bg-white rounded-md text-xs text-center text-[#5A6D6D]"
              style={{ margin: "0 24px", padding: "4px 14px" }}
            >
              dau.ai/results
            </div>
          </div>

          {/* App preview */}
          <div
            className="grid gap-16"
            style={{
              gridTemplateColumns: "1fr 1fr",
              padding: "4rem",
              minHeight: 460,
            }}
          >
            {/* Score column */}
            <div className="flex flex-col justify-center">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#98C18E] mb-4">
                Tỷ lệ ĐẬU của bạn
              </p>
              <div
                className="font-heading font-bold text-[#2F4F4F] mb-6 leading-none"
                style={{ fontSize: "clamp(5rem,10vw,8rem)" }}
              >
                87<span style={{ color: "#98C18E" }}>%</span>
              </div>
              <p className="text-[#5A6D6D] leading-relaxed" style={{ fontSize: "1.1rem" }}>
                CV của bạn cực kỳ tiềm năng cho vị trí{" "}
                <strong className="text-[#2F4F4F]">Kỹ sư Frontend</strong>.
                Chỉ cần bổ sung 2 từ khóa vàng!
              </p>
            </div>

            {/* Skills column */}
            <div className="flex flex-col justify-center gap-4">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#5A6D6D] mb-2">
                Kỹ năng &quot;Bean&quot; phát hiện
              </p>
              {SKILLS.map((s) => (
                <div
                  key={s.skill}
                  className="flex items-center gap-4 rounded-2xl text-sm font-medium"
                  style={{
                    padding: "1rem 1.25rem",
                    backgroundColor: s.on ? "rgba(152,193,142,0.1)" : "#F9F9F2",
                    border: `1px solid ${s.on ? "#98C18E" : "rgba(0,0,0,0.1)"}`,
                    color: s.on ? "#2F4F4F" : "#5A6D6D",
                  }}
                >
                  <span
                    className="flex items-center justify-center w-6 h-6 rounded-full shrink-0 text-white"
                    style={{
                      backgroundColor: s.on ? "#98C18E" : "white",
                      border: s.on ? "none" : "1px solid rgba(0,0,0,0.1)",
                    }}
                  >
                    {s.on && <Check size={14} strokeWidth={3} />}
                  </span>
                  {s.skill}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
