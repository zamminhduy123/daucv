export const meta = {
  name: 'blog-quality-overhaul',
  description: 'Comprehensive blog quality improvement across all phases',
  phases: [
    { title: 'Phase 1: Cleanup', detail: 'Delete low-quality T2 blog posts' },
    { title: 'Phase 2: Generator Fix', detail: 'Improve fallback and quality checks' },
    { title: 'Phase 3: Internal Linking', detail: 'Add prev/next and shared-tags linking' },
    { title: 'Phase 4: Blog List Fix', detail: 'Activate category filter, search, pagination' },
    { title: 'Phase 5: Tag Pages', detail: 'Create /blog/[tag] aggregation pages' },
    { title: 'Phase 6: OG Images', detail: 'Add per-post Open Graph/Twitter images' },
    { title: 'Phase 7: Cron Setup', detail: 'Create GitHub Actions workflow for automation' },
  ],
}

const BLOG_DIR = '/Users/rzy/Desktop/ProjectWithTien/cv-helper/cv-fit-app/frontend/content/blog'
const projectDir = '/Users/rzy/Desktop/ProjectWithTien/cv-helper/cv-fit-app'

const T2_TO_DELETE = [
  "cach-viet-cv-trai-nganh-nhan-dung-ky-nang-de-nha-tuyen-dung-van-muon-gap-ban.mdx",
  "cv-account-executive-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-bac-si-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-business-analyst-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-business-development-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-cham-soc-khach-hang-cach-viet-cv-cho-vi-tri-cskh-ro-ky-nang-va-chi-so-phuc-vu-2.mdx",
  "cv-cham-soc-khach-hang-cach-viet-cv-cho-vi-tri-cskh-ro-ky-nang-va-chi-so-phuc-vu.mdx",
  "cv-cho-thuc-tap-sinh-cach-viet-it-kinh-nghiem-nhung-van-du-thuyet-phuc.mdx",
  "cv-chuan-ats-cho-sinh-vien-moi-ra-truong-cach-viet-de-de-duoc-goi-phong-van.mdx",
  "cv-chuyen-vien-an-toan-thong-tin-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-chuyen-vien-bao-hiem-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-chuyen-vien-crm-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-chuyen-vien-m-a-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-chuyen-vien-phan-tich-tai-chinh-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-chuyen-vien-thuong-mai-dien-tu-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-chuyen-vien-truyen-thong-marketing-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-chuyen-vien-xuat-nhap-khau-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-content-marketing-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-customer-success-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-dao-tao-noi-bo-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-data-analyst-chuan-ats-cach-viet-kinh-nghiem-va-ky-nang-noi-bat.mdx",
  "cv-data-analyst-chuan-ats.mdx",
  "cv-data-analyst-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-designer-cach-ket-hop-portfolio-va-cv-de-nha-tuyen-dung-thay-duoc-gu-lan-nang-luc.mdx",
  "cv-dieu-duong-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-dieu-phoi-su-kien-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-duoc-si-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-giao-vien-tieng-anh-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-hrbp-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-ke-hoach-chuoi-cung-ung-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-ke-toan-cach-trinh-bay-kinh-nghiem-chung-tu-va-do-chinh-xac-mot-cach-thuyet-phuc.mdx",
  "cv-kiem-soat-chat-luong-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-kiem-toan-noi-bo-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-ky-su-ai-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-ky-su-co-khi-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-ky-su-dien-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-ky-su-moi-truong-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-ky-su-xay-dung-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen-2.mdx",
  "cv-ky-su-xay-dung-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-ky-thuat-vien-bao-tri-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-le-tan-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-logistics-coordinator-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-marketing-cach-viet-thanh-tich-chien-dich-de-nha-tuyen-dung-nhin-thay-nang-luc-that.mdx",
  "cv-nhan-su-cach-nhan-manh-tuyen-dung-c-b-va-phoi-hop-noi-bo-trong-ho-so.mdx",
  "cv-nhan-vien-kho-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-nhan-vien-mua-hang-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-nhan-vien-phan-tich-nghiep-vu-bao-hiem-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-phap-che-doanh-nghiep-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-qa-qc-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-quan-ly-du-an-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen-2.mdx",
  "cv-quan-ly-du-an-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-quan-ly-ngan-quy-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-quan-ly-san-xuat-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-scrum-master-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-tro-ly-giam-doc-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-tro-ly-kinh-doanh-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-truyen-thong-noi-bo-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-tuyen-dung-it-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-ux-researcher-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-van-hanh-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "cv-xuat-nhap-khau-huong-dan-thuc-te-de-tang-co-hoi-ung-tuyen.mdx",
  "danh-gia-cv-truoc-khi-ung-tuyen-checklist-tu-ra-soat-trong-15-phut.mdx",
  "example-mdx-usage.mdx",
  "linkedin-va-cv-khac-nhau-the-nao-cach-dong-bo-ho-so-de-khong-mat-diem-voi-recruiter.mdx",
  "mau-cv-tieng-viet-chuyen-nghiep.mdx",
  "meo-toi-uu-cv-bang-ai-cach-dung-cong-cu-dung-de-tang-chat-luong-ho-so.mdx",
  "portfolio-va-cv-khac-nhau-the-nao-cach-dung-ca-hai-de-tang-co-hoi-phong-van.mdx",
  "tu-khoa-trong-jd-va-cv-cach-chon-dung-keyword-ma-khong-bien-ho-so-thanh-may-moc.mdx",
]

// ═══════════════════════════════════════════
// PHASE 1: Delete T2 posts
// ═══════════════════════════════════════════
phase('Phase 1: Cleanup')
log('Phase 1: Deleting ' + T2_TO_DELETE.length + ' low-quality posts...')

const cleanupResult = await agent(
  'Phase 1: Blog Cleanup. Delete all T2 (low-quality template) blog posts from: ' + BLOG_DIR + '. These 68 files should be deleted: ' + T2_TO_DELETE.map(f => '  - ' + f).join(', ') + '. DO NOT delete any other files. After deletion, list the remaining files to confirm. Verify exactly 17 .mdx files remain.',
  {
    label: 'delete-T2-posts',
    phase: 'Phase 1: Cleanup',
    isolation: 'worktree',
  }
)
log('Phase 1 complete: ' + cleanupResult)

// ═══════════════════════════════════════════
// PHASE 2: Improve Generator Fallback
// ═══════════════════════════════════════════
phase('Phase 2: Generator Fix')

const generatorFixResult = await agent(
  'Fix the blog post generator at: ' + projectDir + '/backend/scripts/generate_seo_blog_posts.py. PROBLEM: The fallback_article() function produces nearly identical 4-section template for ALL topics. Improvements needed: 1) ROLE-SPECIFIC SECTIONS: Instead of generic 4 sections, generate sections specific to the topic/role. For data analyst -> data metrics, tools, portfolio. For ke toan -> chung tu, bao cao tai chinh. For fresher IT -> GitHub projects, internship. 2) ROLE-SPECIFIC EXAMPLES: Include actual CV bullet examples relevant to the role with before/after phrasing. 3) ROLE-SPECIFIC CHECKLIST: Items should be role-specific. 4) ROLE-SPECIFIC STEPS: Step list should include role-relevant actions. 5) RAISE QUALITY BAR: Increase minimum word count from 850 to 1000. 6) ADD CONCRETE MARKERS: Ensure fallback content has concrete markers. 7) PREVENT TEMPLATE REPETITION: Add role-to-sections mapping so each topic gets unique section titles. Steps: read current fallback_article(), create role-specific section mapper, create role-specific example pools, update fallback_article(), update validate_editorial_quality(). Do NOT change script structure, only improve the fallback functions.',
  {
    label: 'fix-generator',
    phase: 'Phase 2: Generator Fix',
    isolation: 'worktree',
  }
)
log('Phase 2 complete: ' + generatorFixResult)

// ═══════════════════════════════════════════
// PHASE 3: Internal Linking
// ═══════════════════════════════════════════
phase('Phase 3: Internal Linking')

const linkingResult = await agent(
  'Add internal linking to all remaining blog posts in: ' + BLOG_DIR + '. After Phase 1 cleanup, there should be 17 T1 posts. Each .mdx file needs: 1) ADD PREV/NEXT METADATA: In frontmatter, add prevSlug and nextSlug fields forming a chronological chain sorted by date. 2) ADD IN-CONTENT LINKS: For each post, identify 2-3 other posts sharing tags/topics and add natural contextual links using markdown syntax. 3) UPDATE BLOG POST PAGE at: ' + projectDir + '/frontend/src/app/blog/[slug]/page.tsx to add prev/next navigation buttons below the article and change related posts sidebar to filter by shared tags instead of random slice. Read all 17 T1 posts, catalog titles/dates/tags, assign prev/next, identify in-content links, update files. Only add links where they make natural contextual sense. Return list of links added per post.',
  {
    label: 'internal-linking',
    phase: 'Phase 3: Internal Linking',
    isolation: 'worktree',
  }
)
log('Phase 3 complete: ' + linkingResult)

// ═══════════════════════════════════════════
// PHASE 4: Fix Blog List Page
// ═══════════════════════════════════════════
phase('Phase 4: Blog List Fix')

const blogListResult = await agent(
  'Fix the blog list page at: ' + projectDir + '/frontend/src/app/blog/page.tsx. Current problems: 1) Category filter has UI but does not work. 2) Search bar is commented out. 3) Pagination is commented out. 4) Active category is hardcoded. Improvements: 1) Make category filter work with useState client-side state. 2) Activate search - filter by title/description match. 3) Fix categories to reflect actual categories in posts. 4) Implement pagination - show 9 posts per page. 5) Dynamic categories from actual posts. Post data has: slug, title, description, date, category, author, coverImage, readTime, tags, authorAvatar. Use standard React patterns.',
  {
    label: 'fix-blog-list',
    phase: 'Phase 4: Blog List Fix',
    isolation: 'worktree',
  }
)
log('Phase 4 complete: ' + blogListResult)

// ═══════════════════════════════════════════
// PHASE 5: Tag Aggregation Pages
// ═══════════════════════════════════════════
phase('Phase 5: Tag Pages')

const tagPagesResult = await agent(
  'Create tag aggregation pages for the blog. Create new Next.js route at: ' + projectDir + '/frontend/src/app/blog/[tag]/page.tsx. Page should: 1) Show all blog posts with the selected tag. 2) Nice header with tag name. 3) Display posts in same card layout as main blog page. 4) Include same layout (navbar, footer, metadata). 5) Proper SEO metadata with canonical URL. 6) Return 404 if no posts have the selected tag. Also update main blog page to show clickable tags on each card. Use existing getAllPosts() from @/lib/mdx. Update sitemap.ts at: ' + projectDir + '/frontend/src/app/sitemap.ts to add tag page sitemap entries.',
  {
    label: 'tag-pages',
    phase: 'Phase 5: Tag Pages',
    isolation: 'worktree',
  }
)
log('Phase 5 complete: ' + tagPagesResult)

// ═══════════════════════════════════════════
// PHASE 6: Per-Post OG/Twitter Images
// ═══════════════════════════════════════════
phase('Phase 6: OG/Twitter Images')

const ogResult = await agent(
  'Add per-post Open Graph and Twitter card images to blog post pages. Current issue: site has site-level OG/Twitter metadata but NO per-post images. Changes needed: 1) UPDATE generateMetadata in blog post page at: ' + projectDir + '/frontend/src/app/blog/[slug]/page.tsx - add images, openGraph (type: article, publishedTime, tags), and twitter with post-specific content. 2) Add keywords array from post tags. 3) Handle posts without coverImage - use local fallback. 4) NO changes needed to root layout.tsx. Metadata should include: images with coverImage URL, openGraph with article type, twitter summary_large_image, keywords from tags.',
  {
    label: 'og-images',
    phase: 'Phase 6: OG Images',
    isolation: 'worktree',
  }
)
log('Phase 6 complete: ' + ogResult)

// ═══════════════════════════════════════════
// PHASE 7: Cron Setup
// ═══════════════════════════════════════════
phase('Phase 7: Cron Setup')

const cronResult = await agent(
  'Create a GitHub Actions workflow for automated blog post generation. Create file at: ' + projectDir + '/.github/workflows/blog-generation.yml. Requirements: 1) TRIGGERS: Runs daily at 6:00 AM Asia/Ho_Chi_Minh (23:00 UTC). Also allows manual trigger with workflow_dispatch and optional count input (1-5). 2) STEPS: Checkout, setup Python 3.12, install deps, run publish_seo_blog_posts.py --min 2 --max 4, check if files generated, if yes git add/commit/push, if no skip. 3) ERRORS: If script fails, report error but do not fail workflow. The publish wrapper already has dedup state tracking.',
  {
    label: 'setup-cron',
    phase: 'Phase 7: Cron Setup',
    isolation: 'worktree',
  }
)
log('Phase 7 complete: ' + cronResult)

// ═══════════════════════════════════════════
// FINAL
// ═══════════════════════════════════════════
phase('Complete')
log('All phases executed:')
log('1. Deleted ' + T2_TO_DELETE.length + ' low-quality T2 posts')
log('2. Improved generator fallback for role-specific content')
log('3. Added internal linking to T1 posts')
log('4. Fixed blog list page')
log('5. Created tag aggregation pages')
log('6. Added per-post OG/Twitter images')
log('7. Created GitHub Actions cron workflow')
