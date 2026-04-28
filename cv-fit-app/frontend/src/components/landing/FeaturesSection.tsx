import React from 'react';
import { FileCheck, Target, MessageSquare, Check } from 'lucide-react';
import Image from 'next/image';

export default function FeaturesSection() {
  return (
    <section id="tính-năng" className="max-w-7xl mx-auto px-6 py-12">
      <div className="flex flex-col items-center justify-center mb-4">
        <h2 className='font-heading font-bold text-[#2F4F4F] text-3xl md:text-4xl mb-4'>Đậu đồng hành với bạn mọi lúc</h2>
        <p className='text-sm text-gray-600 leading-relaxed'>Từ chỉnh sửa CV đến khi bạn nhận được offer!</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
        
        {/* Card 1: Tối ưu CV với AI */}
        <div className="bg-green-50/50 rounded-3xl p-8 border border-gray-100 flex flex-col h-full">
          <div className="bg-white rounded-xl shadow-sm p-2 w-12 h-12 flex items-center justify-center mb-6">
            <FileCheck className="text-(--primary)" size={24} />
          </div>
          <h3 className="text-xl font-bold text-[#2F4F4F] mb-3">Tối ưu CV với AI</h3>
          <p className="text-sm text-gray-600 leading-relaxed mb-8">
            Hệ thống tự động phân tích và đề xuất chỉnh sửa nội dung CV để vượt qua các bộ lọc ATS khắt khe nhất.
          </p>
          
          {/* Inner Mockup 1 */}
          <div className="mt-auto bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <p className="text-[10px] uppercase font-bold text-gray-400 mb-6 tracking-wider">Độ tương thích</p>
            <div className="flex items-center gap-8">
              {/* Circular Progress */}
              <div className="relative w-20 h-20 flex-shrink-0">
                <svg className="w-full h-full" viewBox="0 0 36 36">
                  <path
                    className="stroke-gray-100"
                    strokeWidth="3"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    className="stroke-[var(--primary)]"
                    strokeWidth="3"
                    strokeDasharray="85, 100"
                    strokeLinecap="round"
                    fill="none"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-bold text-[#2F4F4F]">85%</span>
                </div>
              </div>

              {/* Checklist */}
              <div className="flex flex-col gap-3 flex-1">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="bg-green-100 rounded-full p-0.5">
                      <Check size={10} className="text-(--primary)" strokeWidth={4} />
                    </div>
                    <div className="bg-gray-100 rounded-full h-2 w-full max-w-[80px]"></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Card 2: Chấm điểm độ phù hợp */}
        <div className="bg-orange-50/50 rounded-3xl p-8 border border-gray-100 flex flex-col h-full">
          <div className="bg-white rounded-xl shadow-sm p-2 w-12 h-12 flex items-center justify-center mb-6">
            <Target className="text-orange-500" size={24} />
          </div>
          <h3 className="text-xl font-bold text-[#2F4F4F] mb-3">Chấm điểm độ phù hợp</h3>
          <p className="text-sm text-gray-600 leading-relaxed mb-8">
            So sánh kỹ năng của bạn với mô tả công việc (JD) để tìm ra những khoảng trống cần bổ sung.
          </p>
          
          {/* Inner Mockup 2 */}
          <div className="mt-auto bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <p className="text-[10px] uppercase font-bold text-gray-400 mb-6 tracking-wider">Kỹ năng còn thiếu</p>
            <div className="flex flex-col gap-4">
              {/* Skill Item 1 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-red-500"></div>
                  <span className="text-xs font-semibold text-[#2F4F4F]">Data Analysis</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="bg-gray-100 rounded-full h-1.5 w-12"></div>
                  <span className="bg-red-50 text-red-600 px-2.5 py-0.5 rounded-full text-[9px] font-bold">Quan trọng</span>
                </div>
              </div>
              {/* Skill Item 2 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-yellow-400"></div>
                  <span className="text-xs font-semibold text-[#2F4F4F]">Python</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="bg-gray-100 rounded-full h-1.5 w-12"></div>
                  <span className="bg-orange-50 text-orange-600 px-2.5 py-0.5 rounded-full text-[9px] font-bold">Nên có</span>
                </div>
              </div>
              {/* Skill Item 3 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-(--primary)"></div>
                  <span className="text-xs font-semibold text-[#2F4F4F]">SQL</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="bg-gray-100 rounded-full h-1.5 w-12"></div>
                  <span className="bg-green-50 text-(--primary) px-2.5 py-0.5 rounded-full text-[9px] font-bold">Tốt</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Card 3: Luyện phỏng vấn 1-1 */}
        <div className="bg-blue-50/50 rounded-3xl p-8 border border-gray-100 flex flex-col h-full">
          <div className="bg-white rounded-xl shadow-sm p-2 w-12 h-12 flex items-center justify-center mb-6">
            <MessageSquare className="text-blue-500" size={24} />
          </div>
          <h3 className="text-xl font-bold text-[#2F4F4F] mb-3">Luyện phỏng vấn 1-1</h3>
          <p className="text-sm text-gray-600 leading-relaxed mb-8">
            Thực hành phỏng vấn với AI mô phỏng người thật, giúp bạn làm quen với áp lực và cải thiện phản xạ.
          </p>
          
          {/* Inner Mockup 3 */}
          <div className="mt-auto bg-[#F9FAF6] rounded-2xl p-4 shadow-sm border border-gray-100 relative min-h-[160px] flex items-end justify-between overflow-hidden">
            <div className="flex flex-col gap-2 flex-1 z-10">
              {/* Chat Bubble 1: Text */}
              <div className="p-3 bg-white border border-gray-100 rounded-2xl rounded-bl-none shadow-sm max-w-[180px]">
                <p className="text-[10px] text-[#2F4F4F] leading-relaxed">
                  <span className="font-bold text-(--primary)">Bé Đậu:</span> Bạn hãy giới thiệu về dự án đáng tự hào nhất của bạn?
                </p>
              </div>

              {/* Chat Bubble 2: Waveform */}
              <div className="p-3 bg-white border border-gray-100 rounded-2xl rounded-bl-none shadow-sm w-fit flex items-center gap-1 min-w-[120px]">
                {[2, 4, 3, 6, 4, 8, 5, 3, 6, 4, 7, 3, 2].map((h, i) => (
                  <div 
                    key={i} 
                    className="w-1 bg-(--primary) rounded-full" 
                    style={{ height: `${h * 1.5}px` }}
                  ></div>
                ))}
              </div>
            </div>

            {/* Mascot Image */}
            <div className="relative w-24 h-24 -mr-2 flex-shrink-0">
              <Image
                src="/call.webp"
                alt="Mascot with headphones"
                fill
                className="object-contain"
              />
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
