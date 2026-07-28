import { MetadataRoute } from 'next';
import { getAllPosts } from '@/lib/mdx';
import { REDIRECTED_BLOG_SLUGS, SITE_URL } from '@/lib/site';
import { nganhNgheList } from './mau-cv/[nganh-nghe]/page';

export default function sitemap(): MetadataRoute.Sitemap {
  const posts = getAllPosts().filter(
    (post) => !REDIRECTED_BLOG_SLUGS.has(post.slug),
  );
  const baseUrl = SITE_URL;
  const industries = Object.keys(nganhNgheList);

  // Collect all unique tags across posts
  const allTags = new Set<string>();
  posts.forEach((post) => {
    post.tags?.forEach((tag) => allTags.add(tag));
  });

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
    ...Array.from(allTags).map((tag) => ({
      url: `${baseUrl}/blog/tag/${encodeURIComponent(tag)}`,
      lastModified: new Date(),
      changeFrequency: 'monthly' as const,
      priority: 0.6,
    })),
    ...industries.map((industry) => ({
      url: `${baseUrl}/mau-cv/${industry}`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.8,
    })),
  ];
}
