import AppSidebar from "@/components/shared/AppSidebar";
import MobileTopNav from "@/components/shared/MobileTopNav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen w-full flex overflow-hidden">
      {/* Persistent Left Sidebar (desktop only) */}
      <AppSidebar />

      {/* Right: Main Content Area */}
      <div className="flex-1 h-full flex flex-col overflow-hidden">
        {/* Mobile top nav (hidden on desktop) */}
        <MobileTopNav />

        {/* Scrollable content */}
        <main className="flex-1 h-full overflow-y-auto bg-[#F9F9F2] p-4 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
