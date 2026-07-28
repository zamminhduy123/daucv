/** The hostname Vercel serves in production. Keep all indexable URLs on it. */
export const SITE_URL = 'https://www.daucv.com';

/**
 * These routes intentionally return permanent redirects in next.config.ts.
 * They must never appear as indexable sitemap entries.
 */
export const REDIRECTED_BLOG_SLUGS = new Set([
  'cv-fresher-it-bien-kinh-nghiem-it-oi-thanh-diem-sang-thu-hut-nha-tuyen-dung',
  'cv-chuan-ats-cho-fresher-it-7-meo-giup-ban-vuot-qua-robot-tu-dong',
  'viet-cv-product-manager-cach-the-hien-tu-duy-san-pham-va-dan-dat-tang-truong',
]);
