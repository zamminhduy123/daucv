import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/app/'],
    },
    sitemap: 'https://daucv.com/sitemap.xml', // Update this when you have your production domain
  };
}
