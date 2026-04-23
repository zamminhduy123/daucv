import Link from "next/link";

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

export default function Logo({ asLink = true, size = "md" }: LogoProps) {
  const content = (
    <span
      className={`font-heading font-bold tracking-tight text-[#2F4F4F] flex items-center gap-1.5 ${sizeMap[size]}`}
    >
      <span role="img" aria-label="sprout" className="leading-none">🌱</span>
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
