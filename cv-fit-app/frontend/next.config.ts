import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
        port: "",
        pathname: "/**",
      },
    ],
  },
  async redirects() {
    return [
      // Fresher IT cluster 2: consolidate cannibalizing pair (same-day publish 2026-06-08)
      {
        source:
          "/blog/cv-fresher-it-bien-kinh-nghiem-it-oi-thanh-diem-sang-thu-hut-nha-tuyen-dung",
        destination:
          "/blog/xay-dung-cv-it-fresher-bien-kinh-nghiem-non-thanh-diem-manh-va-thu-hut-nha-tuyen-dung",
        permanent: true,
      },
      // Fresher IT cluster 1: consolidate cannibalizing pair (same-day publish 2026-06-03)
      {
        source:
          "/blog/cv-chuan-ats-cho-fresher-it-7-meo-giup-ban-vuot-qua-robot-tu-dong",
        destination:
          "/blog/cv-chuan-ats-cho-fresher-it-huong-dan-tung-buoc-de-vuot-qua-robot-tuyen-dung",
        permanent: true,
      },
      // Product Manager: consolidate cannibalizing pair
      {
        source:
          "/blog/viet-cv-product-manager-cach-the-hien-tu-duy-san-pham-va-dan-dat-tang-truong",
        destination:
          "/blog/cv-product-manager-chuan-ats-huong-dan-viet-chi-tiet-dat-ket-qua-cao",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
