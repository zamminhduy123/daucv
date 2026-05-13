## Creating blog posts

This project uses MDX for blog posts.

To create a new blog post:
1. Copy `/content/blog/_template.mdx`.
2. Rename it using the blog slug.
3. Edit the frontmatter.
4. Use the reusable components from `/components/blog`.
5. Do not write full blog pages in raw HTML.

The shared blog layout handles the page shell, right sidebar, table of contents, and related posts.
The MDX file should focus on article content and reusable blog sections.