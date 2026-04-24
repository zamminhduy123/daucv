import Link from "next/link";
import Image from "next/image";

interface LogoProps {
  /** If true, wraps the logo in a Link back to "/" */
  asLink?: boolean;
  size?: "sm" | "md" | "lg";
}

const sizeMap = {
  sm: "text-xl",
  md: "text-2xl",
  lg: "text-3xl",
} as const;

const imgSizeMap = {
  sm: 24,
  md: 32,
  lg: 40,
} as const;

export default function Logo({ asLink = true, size = "md" }: LogoProps) {
  const content = (
    <span
      className={`font-heading font-bold tracking-tight text-[#2F4F4F] flex items-center gap-1.5 ${sizeMap[size]}`}
    >
      <Image 
        src="/main-icon.webp" 
        alt="Đậu" 
        width={imgSizeMap[size]} 
        height={imgSizeMap[size]} 
        className="leading-none drop-shadow-sm"
      />
      ĐẬU
    </span>
  );

  if (!asLink) return content;

  return (
    <Link href="/" className="no-underline hover:opacity-80 transition-opacity">
      {content}
    </Link>
  );
}
