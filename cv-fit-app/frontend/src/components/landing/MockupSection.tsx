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
    <section className="max-w-7xl mx-auto relative px-4 sm:px-6 lg:px-12 pb-16 pt-8 md:pb-24 max-md:overflow-hidden">
      {/* Green glow background */}
      <div
        className="absolute rounded-[32px] w-full left-0 right-0 max-sm:hidden"
        style={{
          inset: "auto 0 0 0", height: "65%",
          backgroundColor: "var(--primary)", opacity: 0.15,
        }}
      />
      <div
        className="absolute rounded-[32px] w-[120%] -left-[10%] max-sm:block hidden"
        style={{
          inset: "auto 0 0 0", height: "60%",
          backgroundColor: "var(--primary)", opacity: 0.15,
        }}
      />

      {/* Card */}
      <div className="relative md:p-8 lg:p-12 py-4">
        <div
          className="bg-white rounded-3xl overflow-hidden"
          style={{
            boxShadow: "0 32px 80px rgba(47,79,79,0.15)",
            border: "1px solid rgba(47,79,79,0.05)",
          }}
        >
          {/* Browser chrome */}
          <div
            className="flex items-center gap-2.5 border-b border-black/5 px-4 py-3"
            style={{ backgroundColor: "#F1F1F1" }}
          >
            <div className="flex gap-1.5 shrink-0">
              {["#FF5F57", "#FFBD2E", "#28C840"].map((c) => (
                <span
                  key={c}
                  className="block w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full"
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
            <div className="flex-1 max-w-[400px] mx-auto bg-white rounded-md text-[10px] sm:text-xs text-center text-[#5A6D6D] py-1 px-3 truncate">
              dau.ai/results
            </div>
          </div>

          {/* App preview */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16 p-6 sm:p-10 lg:p-16 min-h-[auto] md:min-h-[460px]">
            {/* Score column */}
            <div className="flex flex-col justify-center text-center md:text-left">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--primary)] mb-4">
                Tỷ lệ ĐẬU của bạn
              </p>
              <div
                className="font-heading font-bold text-[#2F4F4F] mb-6 leading-none"
                style={{ fontSize: "clamp(3.5rem,10vw,8rem)" }}
              >
                87<span style={{ color: "var(--primary)" }}>%</span>
              </div>
              <p className="text-[#5A6D6D] leading-relaxed text-[0.95rem] md:text-[1.1rem]">
                CV của bạn cực kỳ tiềm năng cho vị trí{" "}
                <strong className="text-[#2F4F4F]">Kỹ sư Frontend</strong>.
                Chỉ cần bổ sung 2 từ khóa vàng!
              </p>
            </div>

            {/* Skills column */}
            <div className="flex flex-col justify-center gap-3 md:gap-4">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#5A6D6D] mb-1 md:mb-2 text-center md:text-left">
                Kỹ năng &quot;Bean&quot; phát hiện
              </p>
              {SKILLS.map((s) => (
                <div
                  key={s.skill}
                  className="flex items-start md:items-center gap-3 lg:gap-4 rounded-2xl text-xs sm:text-sm font-medium p-3 lg:p-4"
                  style={{
                    backgroundColor: s.on ? "rgba(152,193,142,0.1)" : "#F9F9F2",
                    border: `1px solid ${s.on ? "var(--primary)" : "rgba(0,0,0,0.1)"}`,
                    color: s.on ? "#2F4F4F" : "#5A6D6D",
                  }}
                >
                  <span
                    className="flex items-center justify-center w-5 h-5 sm:w-6 sm:h-6 rounded-full shrink-0 text-white mt-0.5 md:mt-0"
                    style={{
                      backgroundColor: s.on ? "var(--primary)" : "white",
                      border: s.on ? "none" : "1px solid rgba(0,0,0,0.1)",
                    }}
                  >
                    {s.on && <Check className="w-3 h-3 sm:w-3.5 sm:h-3.5" strokeWidth={3} />}
                  </span>
                  <span className="leading-tight md:leading-normal">{s.skill}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
