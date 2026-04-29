import { Clock } from "lucide-react";

export default function HistoryPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="w-16 h-16 bg-[var(--primary)]/10 rounded-2xl flex items-center justify-center mb-4">
        <Clock size={32} className="text-[var(--primary)]" />
      </div>
      <h1 className="font-heading font-bold text-2xl text-[#2F4F4F] mb-2">Lịch sử</h1>
      <p className="text-gray-500 text-sm max-w-sm">
        Tính năng đang được phát triển. Hãy quay lại sớm nhé! 🌱
      </p>
    </div>
  );
}
