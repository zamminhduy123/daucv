# Blog Authoring Guide

This project uses **MDX** for blog content. MDX allows you to write standard Markdown while seamlessly embedding React components. 

**IMPORTANT: Do not write full blog pages in raw HTML.** Always use MDX and the provided reusable components to ensure a consistent, responsive, and branded experience (the "Đậu" soft green SaaS style).

## Directory Structure
- **Content:** `/content/blog/` (Store all `.mdx` files here)
- **Components:** `/src/components/blog/` (Store all reusable React blog components here)
- **Page Layout:** `/src/app/blog/[slug]/page.tsx` (Handles the layout, sidebar, Table of Contents, and MDX rendering)

## Creating a New Blog Post

1. **Copy the Template:** Duplicate `/content/blog/_template.mdx` and rename it with your desired slug (e.g., `cach-viet-cv-chuan-ats.mdx`).
2. **Update Frontmatter:** Fill in the YAML frontmatter at the top of the file (title, description, date, coverImage, etc.).
3. **Write Content:** Write your article using standard Markdown headings (`##`, `###`), paragraphs, and lists.
4. **Compose with Components:** Use the pre-built blog components to create engaging, rich layouts (see below).

## Reusable Components

The following components are automatically available inside any `.mdx` file. You do not need to import them manually.

### 1. `<TakeawaysBox />`
Displays a highlighted pale-green box summarizing key points. Place this near the top of your article.
```mdx
<TakeawaysBox takeaways={[
  "Điểm quan trọng 1",
  "Điểm quan trọng 2"
]} />
```

### 2. `<FeatureGrid />`
Displays a 2-to-4 column grid of feature cards.
- `title` (optional): Section title.
- `features`: Array of objects with `icon` (must be a valid lucide-react icon name), `title`, and `description`.
```mdx
<FeatureGrid 
  title="Tại sao chọn Đậu?"
  features={[
    { icon: "Zap", title: "Nhanh chóng", description: "Chỉ 5 phút." }
  ]} 
/>
```

### 3. `<StepList />`
A vertical timeline of steps with large numbered circles and optional images.
```mdx
<StepList 
  title="Các bước thực hiện"
  steps={[
    { title: "Bước 1", description: "Làm gì đó.", image: "https://..." }
  ]} 
/>
```

### 4. `<ChecklistSection />`
A rounded card displaying a list of items with green checkmarks.
```mdx
<ChecklistSection 
  title="Các lỗi cần tránh"
  items={[
    "Sai chính tả",
    "Định dạng phức tạp"
  ]} 
/>
```

### 5. `<BlogCTA />`
A prominent bottom banner with a gradient background, mascot image, and call-to-action button.
```mdx
<BlogCTA 
  title="Bắt đầu ngay"
  description="Tạo CV chuẩn ATS miễn phí."
  buttonText="Tạo CV"
  buttonHref="/cv-builder"
  image="https://..."
/>
```

### 6. `<BlogHero />` and `<CommentsSection />`
- `BlogHero`: Manually renders the title, metadata row, and cover image. Note: `page.tsx` generally does this automatically for you.
- `CommentsSection`: Renders a static mockup of a comments section. Note: Often placed manually or appended automatically by the layout.

## Layout Notes
- **Table of Contents (TOC):** You do not need to build a TOC manually. The system automatically reads all `##` and `###` headings from your MDX file and builds a sticky Table of Contents in the right sidebar.
- **Sidebar & Related Blogs:** Handled automatically by the `page.tsx` layout. Do not build them inside the MDX file.
- **Responsive Design:** All components are pre-styled with Tailwind CSS to stack perfectly on mobile devices.

## Example Post
See `/content/blog/example-mdx-usage.mdx` or `_template.mdx` for complete examples of how these components are composed together to create a polished blog article.
