"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { Check, AlertCircle, Download, MessageSquare } from "lucide-react";

interface Experience {
  company: string;
  role: string;
  bullet_points: string[];
}

interface TailoredCV {
  name: string;
  summary: string;
  experience: Experience[];
  education: string;
  skills: string[];
}

function CircleProgress({ score }: { score: number }) {
  const r = 72;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  return (
    <svg width="180" height="180" className="progress-ring">
      <circle cx="90" cy="90" r={r} fill="none" stroke="rgba(152,193,142,0.2)" strokeWidth="12" />
      <circle
        cx="90" cy="90" r={r} fill="none"
        stroke="var(--primary)" strokeWidth="12"
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round"
      />
      <text x="90" y="90" textAnchor="middle" dominantBaseline="middle" style={{ fontFamily: "Quicksand,sans-serif", fontSize: 44, fill: "#2F4F4F", fontWeight: 700 }}>{score}%</text>
    </svg>
  );
}

export default function ResultsPage() {
  const router = useRouter();

  const [result] = useState(() => {
    if (typeof window === "undefined") return null;
    const raw = sessionStorage.getItem("cvfit_result");
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  });

  useEffect(() => {
    if (!result) router.push("/app");
  }, [result, router]);

  const handlePrint = () => window.print();

  if (!result) return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F9F9F2", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3, borderColor: "rgba(152,193,142,0.2)", borderTopColor: "var(--primary)" }} />
    </div>
  );

  const { match_score, missing_skills, tailored_cv } = result;
  
  let scoreLabel = "Có hội ĐẬU lớn! 🎯";
  let scoreColor = "var(--primary)";
  if (match_score >= 85) {
      scoreLabel = "Khả năng ĐẬU cực cao 🚀";
  } else if (match_score >= 60) {
      scoreLabel = "Cơ hội tốt để ĐẬU ✅";
  } else {
      scoreLabel = "Đậu cần cải thiện thêm 📝";
      scoreColor = "#B22222";
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F9F9F2", color: "#2F4F4F" }}>
      {/* NAV */}
      <header style={{ maxWidth: 1400, margin: "0 auto", padding: "1.5rem 3rem", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(47,79,79,0.08)" }} className="no-print">
        <Link href="/" className="font-heading" style={{ fontSize: "1.75rem", fontWeight: 700, textDecoration: "none", color: "#2F4F4F", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Image src="/main-icon.webp" alt="Đậu" width={32} height={32} /> Đậu
        </Link>
        <Link href="/app" style={{ fontSize: "0.875rem", color: "#5A6D6D", textDecoration: "none", fontWeight: 500 }}>← Làm lại</Link>
      </header>

      <main style={{ maxWidth: 940, margin: "0 auto", padding: "3rem 2rem" }}>
        {/* SCORE SECTION */}
        <div className="fade-up no-print" style={{ backgroundColor: "white", borderRadius: 24, padding: "3rem", border: "1px solid rgba(47,79,79,0.06)", marginBottom: "2rem", display: "flex", alignItems: "center", gap: "4rem", boxShadow: "0 8px 32px rgba(47,79,79,0.04)" }}>
          <CircleProgress score={match_score} />
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: "0.8rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--primary)", marginBottom: "0.5rem" }}>Tỷ lệ ĐẬU dự kiến</p>
            <h2 className="font-heading" style={{ fontSize: "2.25rem", fontWeight: 700, color: scoreColor, marginBottom: "0.75rem" }}>{scoreLabel}</h2>
            <p style={{ color: "#5A6D6D", lineHeight: 1.7, fontSize: "1.05rem" }}>
              {match_score >= 75
                ? "Bạn đã gieo mầm rất tốt! Chỉ cần một vài bước chăm sóc kỹ lưỡng nữa là có thể gặt hái thư mời làm việc."
                : "Cần thêm một chút phân bón cho các kỹ năng còn thiếu để mầm non sự nghiệp của bạn có thể vươn xa hơn."}
            </p>
          </div>
        </div>

        {/* MISSING SKILLS */}
        {missing_skills.length > 0 && (
          <div className="no-print" style={{ backgroundColor: "white", borderRadius: 24, padding: "2.5rem", border: "1px solid rgba(178,34,34,0.1)", marginBottom: "2rem", boxShadow: "0 8px 32px rgba(178,34,34,0.03)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.5rem" }}>
              <AlertCircle size={22} color="#B22222" />
              <h3 className="font-heading" style={{ fontWeight: 700, color: "#2F4F4F", fontSize: "1.25rem" }}>Kỹ năng bạn cần &#34;xào nấu&#34; lại</h3>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
              {missing_skills.map((skill : string) => (
                <span key={skill} style={{ padding: "0.5rem 1.125rem", borderRadius: 12, backgroundColor: "rgba(178,34,34,0.06)", border: "1px solid rgba(178,34,34,0.15)", color: "#B22222", fontSize: "0.95rem", fontWeight: 600 }}>
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* TAILORED CV PREVIEW */}
        <div style={{ backgroundColor: "white", borderRadius: 24, padding: "4rem", border: "1px solid rgba(47,79,79,0.06)", marginBottom: "2rem", boxShadow: "0 8px 32px rgba(47,79,79,0.04)" }}>
          {/* Print actions */}
          <div className="no-print" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "3rem" }}>
            <div>
                <h3 className="font-heading" style={{ fontWeight: 700, color: "#2F4F4F", fontSize: "1.5rem" }}>CV Tối ưu từ Bé Đậu</h3>
                <p style={{ color: "#5A6D6D", fontSize: "0.9rem", marginTop: "0.25rem" }}>Đã được tinh chỉnh để tăng tỷ lệ ĐẬU</p>
            </div>
            <button onClick={handlePrint} className="btn-green" style={{ border: "none", cursor: "pointer" }}>
              <Download size={18} /> Xuất PDF
            </button>
          </div>

          {/* CV CONTENT — printable */}
          <div id="cv-print" style={{ fontFamily: "'Inter', sans-serif" }}>
            <h1 style={{ fontSize: "2.5rem", fontWeight: 700, color: "#2F4F4F", marginBottom: "0.5rem", fontFamily: "Quicksand" }}>{tailored_cv.name}</h1>
            <p style={{ color: "#5A6D6D", lineHeight: 1.7, marginBottom: "2rem", fontSize: "1rem" }}>{tailored_cv.summary}</p>
            <hr style={{ borderColor: "rgba(47,79,79,0.08)", marginBottom: "2rem" }} />

            {tailored_cv.experience.length > 0 && (
              <div style={{ marginBottom: "2rem" }}>
                <h2 style={{ fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--primary)", marginBottom: "1.5rem" }}>Kinh nghiệm làm việc</h2>
                {tailored_cv.experience.map((exp : Experience, i : number) => (
                  <div key={i} style={{ marginBottom: "2rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                      <h3 style={{ fontWeight: 700, color: "#2F4F4F", fontSize: "1.1rem" }}>{exp.role}</h3>
                      <span style={{ fontSize: "0.95rem", color: "#5A6D6D", fontWeight: 500 }}>{exp.company}</span>
                    </div>
                    <ul style={{ marginTop: "0.75rem", paddingLeft: "1.5rem" }}>
                      {exp.bullet_points.map((bp : string, j : number) => (
                        <li key={j} style={{ color: "#2F4F4F", lineHeight: 1.7, fontSize: "0.95rem", marginBottom: "0.5rem" }}>{bp}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
                {tailored_cv.skills.length > 0 && (
                  <div>
                    <h2 style={{ fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--primary)", marginBottom: "1rem" }}>Kỹ năng chuyên môn</h2>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                      {tailored_cv.skills.map((s : string) => (
                        <span key={s} style={{ padding: "0.4rem 1rem", borderRadius: 12, backgroundColor: "rgba(152,193,142,0.1)", border: "1px solid rgba(152,193,142,0.2)", color: "#2F4F4F", fontSize: "0.9rem", fontWeight: 500, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <Check size={14} color="var(--primary)" strokeWidth={3} />{s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {tailored_cv.education && (
                  <div>
                    <h2 style={{ fontSize: "0.85rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--primary)", marginBottom: "1rem" }}>Học vấn</h2>
                    <p style={{ color: "#2F4F4F", fontSize: "0.95rem", lineHeight: 1.6 }}>{tailored_cv.education}</p>
                  </div>
                )}
            </div>
          </div>
        </div>

        {/* INTERVIEW CTA */}
        <div className="no-print" style={{ textAlign: "center", padding: "2rem" }}>
          <Link
            href="/interview"
            className="btn-green"
            style={{ padding: "1.25rem 3rem", fontSize: "1.15rem" }}
          >
            <MessageSquare size={22} /> Luyện tập cùng Bé Đậu
          </Link>
          <p style={{ marginTop: "1.5rem", fontSize: "1rem", color: "#5A6D6D" }}>Tập dợt trước giờ G với AI chuyên sâu</p>
        </div>
      </main>

      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { background: white; }
          #cv-print { padding: 0; }
        }
      `}</style>
    </div>
  );
}
