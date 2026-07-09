"use client";

import React, { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { requestManualPaymentAPI } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { CheckCircle, ArrowLeft, Landmark, Copy, Check, ShieldCheck, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";
import { Suspense } from "react";

interface PaymentDetails {
  success: boolean;
  bank_id: string;
  bank_account: string;
  bank_account_name: string;
  amount: number;
  description: string;
  qr_url: string;
}

function CheckoutContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { refreshCredits } = useAuth();
  
  const packageId = searchParams.get("package_id");
  const [loading, setLoading] = useState(true);
  const [paymentInfo, setPaymentInfo] = useState<PaymentDetails | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (!packageId) {
      toast.error("Không tìm thấy gói tín dụng được chọn.");
      router.replace("/app/billing");
      return;
    }

    const fetchPaymentDetails = async () => {
      try {
        const data = await requestManualPaymentAPI(packageId);
        setPaymentInfo(data);
      } catch (err: any) {
        console.error(err);
        toast.error(err.message || "Không thể khởi tạo mã QR thanh toán. Vui lòng thử lại.");
        router.replace("/app/billing");
      } finally {
        setLoading(false);
      }
    };

    fetchPaymentDetails();
  }, [packageId, router]);

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    toast.success("Đã sao chép vào bộ nhớ tạm!");
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleTransferred = () => {
    setConfirming(true);
    // Simulate short network delay to give a premium feel
    setTimeout(() => {
      toast.success("Yêu cầu duyệt của bạn đã được gửi thành công! Admin sẽ duyệt nạp tiền trong vài phút.");
      refreshCredits();
      router.replace("/app/billing?success=true");
    }, 1200);
  };

  const formatVND = (value: number) => {
    return new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
    }).format(value);
  };

  if (loading) {
    return (
      <div className="min-h-screen w-full bg-[#FAFBF9] flex flex-col items-center justify-center font-sans">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-semibold text-[#5A6D6D]">Đang khởi tạo mã QR chuyển khoản...</p>
        </div>
      </div>
    );
  }

  if (!paymentInfo) return null;

  return (
    <div className="min-h-screen w-full bg-[#FAFBF9] flex flex-col font-sans text-[#2F4F4F]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-[#2F4F4F]/10 py-4 px-6 flex items-center justify-between shrink-0 sticky top-0 z-50">
        <Link
          href="/app/billing"
          className="flex items-center gap-2 text-sm font-semibold text-[#5A6D6D] hover:text-[#1A2D2D] transition-colors"
        >
          <ArrowLeft size={16} />
          Quay lại gói dịch vụ
        </Link>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
          <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 px-3 py-1 rounded-full uppercase tracking-wider">
            Thanh toán an toàn VietQR
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-4 md:p-8 flex flex-col md:flex-row gap-8 items-stretch justify-center">
        {/* Left Card: VietQR Code display */}
        <div className="flex-1 bg-white border border-[#2F4F4F]/10 rounded-3xl p-6 md:p-8 shadow-[0_4px_24px_rgba(47,79,79,0.03)] flex flex-col items-center justify-center text-center">
          <div className="w-12 h-12 bg-emerald-50 rounded-full flex items-center justify-center text-[var(--primary)] mb-4">
            <Landmark size={24} />
          </div>
          <h2 className="text-xl font-heading font-black text-[#1A2D2D] mb-1">
            Quét mã VietQR để thanh toán
          </h2>
          <p className="text-xs md:text-sm text-[#5A6D6D] mb-6 max-w-md leading-relaxed font-medium">
            Mở ứng dụng ngân hàng bất kỳ trên điện thoại của bạn, chọn quét mã QR chuyển khoản và quét ảnh dưới đây.
          </p>

          {/* QR Code Container */}
          <div className="relative w-64 h-64 border-2 border-dashed border-[#2F4F4F]/10 rounded-2xl p-4 mb-5 flex items-center justify-center bg-[#FAFBF9]">
            {/* Corner Scanner lines */}
            <div className="absolute top-0 left-0 w-6 h-6 border-t-4 border-l-4 border-[var(--primary)] rounded-tl-lg"></div>
            <div className="absolute top-0 right-0 w-6 h-6 border-t-4 border-r-4 border-[var(--primary)] rounded-tr-lg"></div>
            <div className="absolute bottom-0 left-0 w-6 h-6 border-b-4 border-l-4 border-[var(--primary)] rounded-bl-lg"></div>
            <div className="absolute bottom-0 right-0 w-6 h-6 border-b-4 border-r-4 border-[var(--primary)] rounded-br-lg"></div>
            
            {/* Real QR image dynamically loaded */}
            <img 
              src={paymentInfo.qr_url} 
              alt="Mã chuyển khoản VietQR" 
              className="w-full h-full object-contain rounded-lg shadow-xs"
            />
          </div>

          <div className="flex items-center gap-2 bg-[#F0FAF5] border border-emerald-100 text-emerald-800 px-4 py-2.5 rounded-xl text-xs font-semibold max-w-md">
            <ShieldCheck size={14} className="shrink-0 text-emerald-600" />
            Hệ thống sẽ tự động cập nhật số dư ví sau khi duyệt.
          </div>
        </div>

        {/* Right Card: Transfer info */}
        <div className="w-full md:w-96 bg-white border border-[#2F4F4F]/10 rounded-3xl p-6 md:p-8 shadow-[0_4px_24px_rgba(47,79,79,0.03)] flex flex-col justify-between">
          <div className="space-y-6">
            <h3 className="text-lg font-heading font-black text-[#1A2D2D] border-b border-[#2F4F4F]/5 pb-3">
              Thông tin chuyển khoản
            </h3>

            {/* Info details */}
            <div className="space-y-4">
              <div>
                <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider block mb-1.5">Ngân hàng</span>
                <span className="text-sm font-bold text-[#2F4F4F] flex items-center justify-between">
                  Techcombank (TCB)
                  <span className="text-xs bg-[#FAFBF9] border border-gray-200 px-2 py-0.5 rounded-md font-semibold text-gray-500">Mạng lưới Napas</span>
                </span>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider block mb-1.5">Số tài khoản</span>
                <span className="text-sm font-mono font-bold text-[#2F4F4F] flex items-center justify-between bg-[#FAFBF9] px-3 py-2 rounded-xl border border-gray-100">
                  {paymentInfo.bank_account}
                  <button 
                    onClick={() => copyToClipboard(paymentInfo.bank_account, "account")}
                    className="text-gray-400 hover:text-[#2F4F4F] transition-colors cursor-pointer"
                  >
                    {copiedField === "account" ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
                  </button>
                </span>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider block mb-1.5">Chủ tài khoản</span>
                <span className="text-sm font-bold text-[#2F4F4F]">
                  {paymentInfo.bank_account_name}
                </span>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider block mb-1.5">Số tiền chuyển</span>
                <span className="text-xl font-heading font-black text-[var(--primary)]">
                  {formatVND(paymentInfo.amount)}
                </span>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider block mb-1.5">Nội dung ghi chú</span>
                <span className="text-xs font-mono font-bold text-[#2F4F4F] flex items-center justify-between bg-yellow-50/50 p-2.5 rounded-xl border border-yellow-100/70">
                  <span className="truncate mr-2 text-yellow-800">{paymentInfo.description}</span>
                  <button 
                    onClick={() => copyToClipboard(paymentInfo.description, "memo")}
                    className="text-yellow-600 hover:text-yellow-800 transition-colors cursor-pointer shrink-0"
                  >
                    {copiedField === "memo" ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
                  </button>
                </span>
              </div>
            </div>
          </div>

          {/* Action Simulation Section */}
          <div className="mt-8 border-t border-[#2F4F4F]/5 pt-6 space-y-3">
            <div className="flex items-start gap-2 text-amber-600 bg-amber-50/50 border border-amber-100 p-3 rounded-2xl mb-2">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <p className="text-[10px] font-medium leading-relaxed">
                Vui lòng điền chính xác nội dung ghi chú chuyển khoản ở trên để admin nhận diện và duyệt nạp tiền nhanh nhất.
              </p>
            </div>
            
            <button
              onClick={handleTransferred}
              disabled={confirming}
              className="w-full py-3.5 px-4 bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white font-heading font-extrabold rounded-2xl flex items-center justify-center gap-2 cursor-pointer transition-all duration-300 shadow-md shadow-[var(--primary)]/10 disabled:opacity-50"
            >
              <CheckCircle size={16} />
              {confirming ? "Đang xử lý..." : "Tôi đã chuyển khoản thành công"}
            </button>

            <button
              onClick={() => router.replace("/app/billing")}
              disabled={confirming}
              className="w-full py-3 px-4 bg-white hover:bg-slate-50 text-gray-500 font-semibold border border-gray-200 rounded-2xl flex items-center justify-center gap-2 cursor-pointer transition-all duration-300 text-xs disabled:opacity-50"
            >
              Hủy thanh toán
            </button>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-xs text-gray-400 shrink-0 border-t border-[#2F4F4F]/10 bg-white">
        © 2026 Đậu CV. Giao dịch được bảo mật và phê duyệt thủ công an toàn.
      </footer>
    </div>
  );
}

export default function CheckoutPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-full bg-[#FAFBF9] flex flex-col items-center justify-center font-sans">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm font-semibold text-[#5A6D6D]">Đang tải thông tin thanh toán...</p>
          </div>
        </div>
      }
    >
      <CheckoutContent />
    </Suspense>
  );
}
