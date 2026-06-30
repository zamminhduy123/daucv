import { MetadataRoute } from 'next';
import { getAllPosts } from '@/lib/mdx';
import { nganhNgheList } from './mau-cv/[nganh-nghe]/page';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://daucv.com'; // Update this when you have your production domain
  const posts = getAllPosts();
  const industries = Object.keys(nganhNgheList);

  return [
    {
      url: `${baseUrl}`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.9,
    },
    {
      url: `${baseUrl}/qna`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    ...posts.map((post) => ({
      url: `${baseUrl}/blog/${post.slug}`,
      lastModified: new Date(post.date),
      changeFrequency: 'weekly' as const,
      priority: 0.7,
    })),
    ...industries.map((industry) => ({
      url: `${baseUrl}/mau-cv/${industry}`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.8,
    })),
  ];
}
