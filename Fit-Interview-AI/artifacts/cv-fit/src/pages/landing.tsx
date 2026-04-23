import { useLocation } from "wouter";
import { ArrowUpRight, Sparkles, FileText, MessageSquare, ChevronRight, Check } from "lucide-react";

export default function Landing() {
  const [, setLocation] = useLocation();

  const goToApp = () => setLocation("/app");

  return (
    <div className="min-h-screen bg-[#F5F2EA] text-[#1A1A1A]" style={{ fontFamily: "Inter, sans-serif" }}>
      {/* NAV */}
      <header className="max-w-7xl mx-auto px-8 lg:px-12 pt-8 pb-4 flex items-center justify-between">
        <div className="text-2xl font-serif font-medium tracking-tight" style={{ fontFamily: "'Playfair Display', Georgia, serif" }}>
          CVFit
        </div>
        <nav className="hidden md:flex items-center gap-10 text-sm font-medium text-[#1A1A1A]">
          <a href="#benefits" className="hover-elevate px-3 py-2 rounded-md">Benefits</a>
          <a href="#how" className="hover-elevate px-3 py-2 rounded-md">How it works</a>
          <a href="#features" className="hover-elevate px-3 py-2 rounded-md">Features</a>
          <a href="#contact" className="hover-elevate px-3 py-2 rounded-md">Contact</a>
        </nav>
        <button
          onClick={goToApp}
          data-testid="button-nav-cta"
          className="inline-flex items-center gap-2 bg-[#3F4E1F] text-[#F5F2EA] px-5 py-2.5 rounded-full text-sm font-medium hover:bg-[#2F3B17] transition-colors"
        >
          Get Started
          <ArrowUpRight className="w-4 h-4" />
        </button>
      </header>

      {/* HERO */}
      <section className="max-w-[1100px] mx-auto px-8 lg:px-12 pt-20 pb-8 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#C8D6B0] bg-[#E8EFD5]/50 text-xs font-mono text-[#3F4E1F] mb-10">
          <span className="text-[#7A8A4F]">▸</span> AI-powered career edge
        </div>
        <h1
          className="font-serif font-normal leading-[0.95] tracking-[-0.03em] text-[#0F0F0F]"
          style={{
            fontFamily: "'Playfair Display', Georgia, serif",
            fontSize: "clamp(3rem, 9vw, 8rem)",
          }}
        >
          Land <span className="text-[#3F4E1F] italic">the</span> role.
        </h1>
        <p className="mt-8 text-lg md:text-xl text-[#3A3A3A] max-w-2xl mx-auto leading-relaxed">
          Upload your CV and a job description — our AI scores your fit, rewrites your resume to match,
          and runs a realistic mock interview so you walk in ready.
        </p>
        <div className="mt-10 flex justify-center">
          <button
            onClick={goToApp}
            data-testid="button-hero-cta"
            className="inline-flex items-center gap-2 bg-[#3F4E1F] text-[#F5F2EA] px-7 py-4 rounded-full text-base font-medium hover:bg-[#2F3B17] transition-colors shadow-sm"
          >
            Try it free
            <ArrowUpRight className="w-5 h-5" />
          </button>
        </div>
        <p className="mt-5 text-sm text-[#5A5A5A]">
          No signup. Or <a href="#how" className="underline underline-offset-4 hover:text-[#3F4E1F]">see how it works</a>
        </p>
      </section>

      {/* DEVICE MOCKUP */}
      <section className="max-w-7xl mx-auto px-8 lg:px-12 pt-8 pb-24 relative">
        <div className="relative">
          {/* Soft sage background panel */}
          <div className="absolute inset-x-0 bottom-0 h-[55%] bg-[#B8C49B] rounded-[36px]" />
          <div className="relative pt-12 px-6 md:px-16 pb-12">
            {/* Browser-style device frame */}
            <div className="rounded-2xl overflow-hidden shadow-2xl border border-black/5 bg-white">
              {/* Window chrome */}
              <div className="bg-[#F1ECE0] px-4 py-3 flex items-center gap-2 border-b border-black/5">
                <div className="flex gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-[#E8B4B4]" />
                  <span className="w-3 h-3 rounded-full bg-[#E8DFB4]" />
                  <span className="w-3 h-3 rounded-full bg-[#B8C49B]" />
                </div>
                <div className="flex-1 mx-6 bg-white rounded-md px-3 py-1 text-xs text-[#5A5A5A] font-mono">
                  cvfit.app/results
                </div>
              </div>
              {/* App preview */}
              <div className="p-8 md:p-12 grid md:grid-cols-12 gap-8 bg-white min-h-[420px]">
                <div className="md:col-span-5 flex flex-col justify-center">
                  <p className="text-xs uppercase tracking-[0.2em] text-[#5A5A5A] mb-3">Match score</p>
                  <div
                    className="font-serif font-normal leading-none text-[#3F4E1F] mb-4"
                    style={{
                      fontFamily: "'Playfair Display', Georgia, serif",
                      fontSize: "clamp(4rem, 9vw, 8rem)",
                    }}
                  >
                    87<span className="text-[#B8C49B]">%</span>
                  </div>
                  <p className="text-base text-[#3A3A3A] leading-relaxed">
                    Strong fit for <span className="text-[#0F0F0F] font-medium">Senior Frontend Engineer</span>.
                    Three skills to highlight before applying.
                  </p>
                </div>
                <div className="md:col-span-7 flex flex-col justify-center gap-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-[#5A5A5A] mb-1">Skills detected</p>
                  {[
                    { skill: "React & TypeScript", on: true },
                    { skill: "System design", on: true },
                    { skill: "Vietnamese & English fluency", on: true },
                    { skill: "GraphQL — to add", on: false },
                    { skill: "AWS deployment — to add", on: false },
                  ].map((s) => (
                    <div
                      key={s.skill}
                      className={`flex items-center gap-3 px-4 py-3 rounded-full border text-sm ${
                        s.on
                          ? "bg-[#E8EFD5] border-[#C8D6B0] text-[#2F3B17]"
                          : "bg-[#F5F2EA] border-black/10 text-[#5A5A5A]"
                      }`}
                    >
                      <span
                        className={`w-5 h-5 rounded-full flex items-center justify-center ${
                          s.on ? "bg-[#3F4E1F] text-white" : "bg-white border border-black/10"
                        }`}
                      >
                        {s.on && <Check className="w-3 h-3" strokeWidth={3} />}
                      </span>
                      {s.skill}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* BENEFITS / 3-UP */}
      <section id="benefits" className="max-w-7xl mx-auto px-8 lg:px-12 py-20">
        <div className="grid md:grid-cols-12 gap-8 items-start mb-16">
          <div className="md:col-span-5">
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#3F4E1F] mb-4">
              What you get
            </p>
            <h2
              className="font-serif font-normal leading-[1.05] tracking-[-0.02em] text-[#0F0F0F]"
              style={{
                fontFamily: "'Playfair Display', Georgia, serif",
                fontSize: "clamp(2.5rem, 5vw, 4.5rem)",
              }}
            >
              Built for serious candidates.
            </h2>
          </div>
          <p className="md:col-span-6 md:col-start-7 text-lg text-[#3A3A3A] leading-relaxed md:pt-8">
            Every feature is designed around one goal — turning your application into an interview, and
            your interview into an offer.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: Sparkles,
              title: "Match score",
              body: "Get a precise 0-100 score showing how well your CV aligns with the job, plus the exact skills you're missing.",
            },
            {
              icon: FileText,
              title: "Tailored CV",
              body: "Your resume rewritten to highlight the strengths that matter for this specific role — printable and ATS-friendly.",
            },
            {
              icon: MessageSquare,
              title: "Mock interview",
              body: "Practice with an AI interviewer that asks questions drawn from the actual JD. Voice input supported in Vietnamese & English.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="bg-white rounded-3xl p-8 border border-black/5 hover:shadow-md transition-shadow"
            >
              <div className="w-12 h-12 rounded-full bg-[#E8EFD5] flex items-center justify-center mb-6">
                <f.icon className="w-5 h-5 text-[#3F4E1F]" />
              </div>
              <h3 className="text-xl font-medium mb-3 text-[#0F0F0F]">{f.title}</h3>
              <p className="text-[#5A5A5A] leading-relaxed">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="max-w-7xl mx-auto px-8 lg:px-12 py-20">
        <div className="bg-[#3F4E1F] rounded-[36px] p-10 md:p-16 text-[#F5F2EA]">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#C8D6B0] mb-4">
            How it works
          </p>
          <h2
            className="font-serif font-normal leading-[1.05] tracking-[-0.02em] mb-12 max-w-3xl"
            style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontSize: "clamp(2.25rem, 4.5vw, 3.75rem)",
            }}
          >
            Three steps. Ten minutes.
          </h2>

          <div className="grid md:grid-cols-3 gap-10 md:gap-6">
            {[
              { n: "01", t: "Upload your CV", d: "Drop in your PDF resume. We extract the text right in your browser." },
              { n: "02", t: "Paste the JD", d: "Add the job description for the role you're targeting." },
              { n: "03", t: "Get your edge", d: "Receive your score, tailored CV, and start an interview practice session." },
            ].map((s) => (
              <div key={s.n} className="border-t border-[#C8D6B0]/30 pt-6">
                <div className="text-[#C8D6B0] font-mono text-sm mb-4">{s.n}</div>
                <h3 className="text-2xl font-medium mb-3">{s.t}</h3>
                <p className="text-[#D8E0C0] leading-relaxed">{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA STRIP */}
      <section id="contact" className="max-w-7xl mx-auto px-8 lg:px-12 py-24">
        <div className="text-center max-w-3xl mx-auto">
          <h2
            className="font-serif font-normal leading-[1.05] tracking-[-0.02em] mb-8 text-[#0F0F0F]"
            style={{
              fontFamily: "'Playfair Display', Georgia, serif",
              fontSize: "clamp(2.75rem, 6vw, 5rem)",
            }}
          >
            Ready when you are.
          </h2>
          <p className="text-lg text-[#3A3A3A] mb-10 leading-relaxed">
            No signup. No credit card. Upload, analyze, and ace your next interview.
          </p>
          <button
            onClick={goToApp}
            data-testid="button-footer-cta"
            className="inline-flex items-center gap-2 bg-[#3F4E1F] text-[#F5F2EA] px-8 py-4 rounded-full text-base font-medium hover:bg-[#2F3B17] transition-colors shadow-sm"
          >
            Start now
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="max-w-7xl mx-auto px-8 lg:px-12 py-10 border-t border-black/10 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-[#5A5A5A]">
        <div className="font-serif text-lg text-[#1A1A1A]" style={{ fontFamily: "'Playfair Display', Georgia, serif" }}>
          CVFit
        </div>
        <div>© 2026 CVFit. Built for the Vietnamese job market.</div>
      </footer>
    </div>
  );
}
