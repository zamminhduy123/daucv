import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

const contentDirectory = path.join(process.cwd(), 'content/blog');

export interface BlogPost {
  slug: string;
  title: string;
  description: string;
  date: string;
  category: string;
  author: string;
  coverImage: string;
  readTime: string;
  tags: string[];
  authorAvatar: string;
  content: string;
}

export function getPostBySlug(slug: string): BlogPost {
  const realSlug = slug.replace(/\.mdx$/, '');
  const fullPath = path.join(contentDirectory, `${realSlug}.mdx`);
  const fileContents = fs.readFileSync(fullPath, 'utf8');
  
  const { data, content } = matter(fileContents);
  
  return {
    slug: realSlug,
    title: data.title,
    description: data.description,
    date: data.date,
    category: data.category,
    author: data.author,
    coverImage: data.coverImage || "https://images.unsplash.com/photo-1586281380349-632531db7ed4?q=80&w=2070&auto=format&fit=crop",
    readTime: data.readTime || "5 min read",
    tags: data.tags || ["Đậu"],
    authorAvatar: data.authorAvatar || "https://ui-avatars.com/api/?name=Đậu&background=E8F5E9&color=2E7D32",
    content,
  };
}

export function getAllPosts(): Omit<BlogPost, 'content'>[] {
  if (!fs.existsSync(contentDirectory)) return [];

  const slugs = fs.readdirSync(contentDirectory);
  const posts = slugs
    .filter((slug) => slug.endsWith('.mdx'))
    .map((slug) => {
      const realSlug = slug.replace(/\.mdx$/, '');
      const fullPath = path.join(contentDirectory, slug);
      const fileContents = fs.readFileSync(fullPath, 'utf8');
      const { data } = matter(fileContents);
      
      return {
        slug: realSlug,
        title: data.title,
        description: data.description,
        date: data.date,
        category: data.category,
        author: data.author,
        coverImage: data.coverImage || "https://images.unsplash.com/photo-1586281380349-632531db7ed4?q=80&w=2070&auto=format&fit=crop",
        readTime: data.readTime || "5 min read",
        tags: data.tags || ["Đậu"],
        authorAvatar: data.authorAvatar || "https://ui-avatars.com/api/?name=Đậu&background=E8F5E9&color=2E7D32",
      };
    })
    .sort((post1, post2) => (post1.date > post2.date ? -1 : 1));

  return posts;
}
