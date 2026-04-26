import { LandingNavbar } from "@/components/shared/TopNavbar";
import HeroSection from "@/components/landing/HeroSection";
import MockupSection from "@/components/landing/MockupSection";
import FeaturesSection from "@/components/landing/FeaturesSection";
import HowItWorksSection from "@/components/landing/HowItWorksSection";
import CallToAction from "@/components/landing/CallToAction";
import Footer from "@/components/landing/Footer";

/**
 * Landing page — Server Component.
 * Only composes section components; no client-side logic lives here.
 */
export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[var(--bg)] text-[#2F4F4F]">
      <LandingNavbar />
      <HeroSection />
      <div className="bg-white mx-auto max-w-[95%] rounded-3xl mt-[-48px] z-100 relative p-0">
        <FeaturesSection />
        {/* <MockupSection /> */}
        <HowItWorksSection />
        <CallToAction />
      </div>
      <Footer />
    </main>
  );
}
