import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';

export interface BlogCTAProps {
  title: string;
  description: string;
  buttonText: string;
  buttonHref: string;
  image?: string;
}

export function BlogCTA({ title, description, buttonText, buttonHref, image }: BlogCTAProps) {
  const ctaImage = image || '/main-icon.webp';

  return (
    <div className="my-8 overflow-hidden rounded-xl border border-[#E2EDCC] bg-[#F0F6DC] shadow-[0_2px_10px_rgba(47,79,79,0.08)] py-4">
      <div className="relative flex min-h-[74px] flex-col items-center gap-2 px-4 py-4 sm:min-h-[82px] sm:flex-row sm:gap-5 sm:px-6 sm:py-3">
        <div className="relative hidden h-[78px] w-[100px] shrink-0 overflow-visible sm:block">
          <Image
            src={ctaImage}
            alt=""
            aria-hidden="true"
            fill
            objectFit='contain'
            className="absolute m-0! shadow-none!"
          />
        </div>

        <div className="relative flex flex-col gap-2 z-10 flex-1 text-center sm:text-left mr-4">
          <h3 className="m-0! border-none pb-0 font-heading text-[15px] font-bold leading-tight text-[#2F4F2F] sm:text-[16px]">
            {title}
          </h3>
          <p className="m-0! mt-1 text-[11px] font-medium leading-snug text-[#5F6F55] sm:text-[12px]">
            {description}
          </p>
        </div>

        <Link
          href={buttonHref}
          className="relative z-10 inline-flex h-9 shrink-0 items-center justify-center rounded-lg bg-[#5A9E40] px-4 text-[12px] font-bold text-white! no-underline shadow-[0_3px_8px_rgba(90,158,64,0.28)] transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-[#4D8738] hover:shadow-[0_4px_12px_rgba(90,158,64,0.35)] active:scale-[0.98] sm:px-5"
        >
          {buttonText}
          <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
