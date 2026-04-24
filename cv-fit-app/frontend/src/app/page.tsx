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
    <main className="min-h-screen bg-[#F9F9F2] text-[#2F4F4F]">
      <LandingNavbar />
      <HeroSection />
      <MockupSection />
      <FeaturesSection />
      <HowItWorksSection />
      <CallToAction />
      <Footer />
    </main>
  );
}
