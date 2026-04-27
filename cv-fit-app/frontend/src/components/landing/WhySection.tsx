import Image from "next/image";
import { ArrowRight, FileX2, Leaf, MessageCircleMore, MicOff } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function WhySection() {
  return (
    <section id="tai-sao-can-dau" className="max-w-7xl mx-auto px-4 sm:px-6 py-16 md:py-20">
      <div className="mb-12 text-center">
        <Leaf className="mx-auto h-6 w-6 text-(--primary) mb-2" />
        <h2 className='font-heading font-bold text-[#2F4F4F] text-3xl md:text-4xl mb-4'>Tại sao bạn cần Đậu?</h2>
        <div className="mx-auto mt-4 h-1.5 w-32 rounded-full bg-(--primary)/70" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="relative overflow-hidden bg-linear-to-br from-[#FFF6F3] to-[#FFF9F7] border border-[#F7D9D2] rounded-3xl p-8 shadow-[0_10px_30px_rgba(47,79,79,0.07)]">
          <CardHeader className="p-0 pr-24 sm:pr-28">
            <div className="w-12 h-12 rounded-2xl bg-white text-[#F05B42] border border-[#F8DBD4] shadow-sm flex items-center justify-center mb-5">
              <FileX2 size={24} strokeWidth={2.1} />
            </div>
            <CardTitle className="text-xl font-bold text-[#2F4F4F] mb-3">
              70% CV bị loại bởi hệ thống ATS
            </CardTitle>
          </CardHeader>

          <CardContent className="p-0 pt-4">
            <p className="text-sm text-gray-600 leading-relaxed mb-8">
              Nhà tuyển dụng và hệ thống tự động (ATS) quét CV của bạn theo từ khóa trong Job
              Description. Một chiếc CV &quot;dùng chung cho mọi công ty&quot; sẽ khiến bạn trượt ngay từ
              vòng duyệt hồ sơ, dù bạn rất giỏi.
            </p>

            <div className="mt-7 rounded-3xl border border-[#F5CEC6] bg-white/85 p-5 flex items-center gap-3 shadow-[0_4px_20px_rgba(240,91,66,0.08)]">
              <ArrowRight className="w-6 h-6 mt-0.5 text-[#F05B42] shrink-0" />
              <p className="text-sm font-bold text-[#D8482E] leading-snug">
                Tối ưu CV theo từng JD giúp tăng 300% cơ hội qua vòng hồ sơ.
              </p>
            </div>
          </CardContent>

          <div className="absolute top-7 right-6">
            <div className="relative w-24 h-24 sm:w-28 sm:h-28">
              <Image src="/cry.webp" alt="Bé Đậu phân tích CV" fill className="object-contain" />
            </div>
          </div>

          <FileX2 className="absolute top-9 right-32 h-10 w-10 text-[#F3BCAF] opacity-40" />
        </Card>

        <Card className="relative overflow-hidden bg-linear-to-br from-[#F4FBF5] to-[#F8FCF8] border border-[#DDEAD9] rounded-3xl p-8 shadow-[0_10px_30px_rgba(47,79,79,0.07)]">
          <CardHeader className="p-0 pr-24 sm:pr-28">
            <div className="w-12 h-12 rounded-2xl bg-white text-[#5B9144] border border-[#DCEAD7] shadow-sm flex items-center justify-center mb-5">
              <MicOff size={24} strokeWidth={2.1} />
            </div>
            <CardTitle className="text-xl font-bold text-[#2F4F4F] mb-3">
              Áp lực tâm lý trong phòng phỏng vấn
            </CardTitle>
          </CardHeader>

          <CardContent className="p-0 pt-4">
            <p className="text-sm text-gray-600 leading-relaxed mb-8">
              Lý thuyết là một chuyện, nhưng khi đối diện với HR, áp lực sẽ khiến bạn quên sạch
              những gì muốn nói. Việc thiếu luyện tập thực tế khiến bạn mất điểm ở những câu hỏi
              tình huống.
            </p>

            <div className="mt-7 rounded-3xl border border-[#D7E8D3] bg-white/85 p-5 flex items-center gap-3 shadow-[0_4px_20px_rgba(86,145,68,0.08)]">
              <ArrowRight className="w-6 h-6 mt-0.5 text-[#4F883B] shrink-0" />
              <p className="text-sm font-bold text-[#3C7C2C] leading-snug">
                Phỏng vấn thử nhiều lần tạo &quot;trí nhớ cơ bắp&quot;, giúp bạn tự tin phản xạ tự nhiên.
              </p>
            </div>
          </CardContent>

          <div className="absolute top-7 right-6">
            <div className="relative w-24 h-24 sm:w-28 sm:h-28">
              <Image src="/call.webp" alt="Bé Đậu luyện phỏng vấn" fill className="object-contain" />
            </div>
          </div>

          <MessageCircleMore className="absolute top-10 -scale-x-100 right-36 h-9 w-9 text-[#BBD5B2] opacity-70" />
        </Card>
      </div>
    </section>
  );
}
