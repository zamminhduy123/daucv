"""Anonymized CV extraction fixtures for Phase 0 regression testing.

Each fixture represents a real failure mode observed in the current
pipeline (flat pdfplumber extraction → section detection → positional
highlighting).  The expected values describe what the typed block
reconstruction SHOULD produce.
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------


@dataclass
class ExpectedBlock:
    """Simplified expected block for fixture comparison."""

    block_type: str  # "entry", "bullet", "paragraph", "skill_group", "publication"
    text: str = ""
    title: str = ""
    subtitle: str = ""
    organization: str = ""
    location: str = ""
    date: str = ""
    bullets: list[str] = field(default_factory=list)
    label: str = ""
    skills: list[str] = field(default_factory=list)
    authors: str = ""
    venue: str = ""
    status: str = ""
    confidence: float = 1.0


@dataclass
class ExpectedSection:
    section_type: (
        str  # "experience", "skills", "education", "projects", "publications", "custom"
    )
    title: str
    blocks: list[ExpectedBlock] = field(default_factory=list)
    lines_must_join: list[int] = field(
        default_factory=list
    )  # 0-indexed among section lines
    lines_must_remain_separate: list[int] = field(default_factory=list)


@dataclass
class CVFixture:
    """One representative CV text + its expected reconstruction."""

    name: str
    """Human-readable fixture name (e.g. 'wrapped_project_bullets')."""
    description: str
    """What real-world CV type this represents."""
    raw_text: str
    """Extracted raw text (exactly as pdfplumber would return)."""
    expected_sections: list[ExpectedSection]
    """What sections the reconstruction should produce."""
    content_counts: dict = field(default_factory=dict)
    """Expected counts: sections, entries, bullets, paragraphs."""
    failure_modes: list[str] = field(default_factory=list)
    """What the CURRENT pipeline gets wrong."""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES: list[CVFixture] = []


# 1. Two-page CV
FIXTURES.append(
    CVFixture(
        name="two_page_cv",
        description="Standard two-page CV that spans page boundaries.",
        raw_text=(
            "NGUYEN VAN DUY\n"
            "Backend Developer | hoichiphasonline@gmail.com | +84 90 123 4567 | HCMC\n\n"
            "TÓM TẮT\n"
            "Kỹ sư backend với 3 năm kinh nghiệm xây dựng hệ thống microservices.\n"
            "Thành thạo Python, FastAPI, PostgreSQL.\n\n"
            "KINH NGHIỆM LÀM VIỆC\n"
            "Công ty TNHH TechCorp\n"
            "Backend Developer | Jan 2023 – Present\n"
            "• Xây dựng RESTful API phục vụ 50k+ người dùng\n"
            "• Tối ưu query PostgreSQL giảm 40% thời gian response\n"
            "• Triển khai CI/CD pipeline với GitHub Actions\n\n"
            "Công ty ABC Solution\n"
            "Junior Developer | Jun 2021 – Dec 2022\n"
            "• Phát triển tính năng thanh toán tích hợp MoMo\n"
            "• Viết unit test đạt覆盖率 85%\n\n"
            "DỰ ÁN\n"
            "Hệ thống Video Retrieval Đa phương thức\n"
            "• Xây dựng hệ thống truy xuất video đa phương thức sử dụng\n"
            "  Transformers và GNN\n"
            "• Tích hợp Elasticsearch cho full-text search\n\n"
            "KỸ NĂNG\n"
            "Backend: Python, FastAPI, Django, Node.js\n"
            "Database: PostgreSQL, Redis, MongoDB\n"
            "Cloud: AWS EC2, S3, Docker, Kubernetes\n"
            "AI/ML: PyTorch, Hugging Face Transformers, GNN\n\n"
            "HỌC VẤN\n"
            "Đại học Bách Khoa TP.HCM\n"
            "Kỹ sư Công nghệ Thông tin | 2017 – 2021\n"
            "Điểm GPA: 3.5/4.0\n\n"
            "CHỨNG CHỈ\n"
            "AWS Certified Solutions Architect – Associate | 2023\n"
            "Google Cloud Professional Data Engineer | 2023\n\n"
            "--- PAGE 2 ---\n"
            "CÔNG BỐ KHOA HỌC\n"
            "Nguyen Van Duy, Le Thi Mai, 'Multi-modal Video Retrieval using\n"
            "Graph Neural Networks and Transformers,' IEEE ICIP 2022.\n\n"
            "NGÔN NGỮ\n"
            "Tiếng Việt (Bản xứ)\n"
            "Tiếng Anh (IELTS 7.0 – thành thạo)\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="custom",
                title="TÓM TẮT",
                blocks=[
                    ExpectedBlock(
                        "paragraph",
                        text="Kỹ sư backend với 3 năm kinh nghiệm xây dựng hệ thống microservices. Thành thạo Python, FastAPI, PostgreSQL.",
                    )
                ],
            ),
            ExpectedSection(
                section_type="experience",
                title="KINH NGHIỆM LÀM VIỆC",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Backend Developer",
                        label="TechCorp",
                        date="Jan 2023 – Present",
                        bullets=[
                            "Xây dựng RESTful API phục vụ 50k+ người dùng",
                            "Tối ưu query PostgreSQL giảm 40% thời gian response",
                            "Triển khai CI/CD pipeline với GitHub Actions",
                        ],
                    ),
                    ExpectedBlock(
                        "entry",
                        title="Junior Developer",
                        label="ABC Solution",
                        date="Jun 2021 – Dec 2022",
                        bullets=[
                            "Phát triển tính năng thanh toán tích hợp MoMo",
                            "Viết unit test đạt覆盖率 85%",
                        ],
                    ),
                ],
            ),
            ExpectedSection(
                section_type="projects",
                title="DỰ ÁN",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Hệ thống Video Retrieval Đa phương thức",
                        bullets=[
                            "Xây dựng hệ thống truy xuất video đa phương thức sử dụng Transformers và GNN",
                            "Tích hợp Elasticsearch cho full-text search",
                        ],
                    ),
                ],
                lines_must_join=[3],  # "sử dụng" line wraps from previous
            ),
            ExpectedSection(
                section_type="skills",
                title="KỸ NĂNG",
                blocks=[
                    ExpectedBlock(
                        "skill_group",
                        label="Backend",
                        skills=["Python", "FastAPI", "Django", "Node.js"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Database",
                        skills=["PostgreSQL", "Redis", "MongoDB"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Cloud",
                        skills=["AWS EC2", "S3", "Docker", "Kubernetes"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="AI/ML",
                        skills=["PyTorch", "Hugging Face Transformers", "GNN"],
                    ),
                ],
            ),
            ExpectedSection(
                section_type="education",
                title="HỌC VẤN",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Kỹ sư Công nghệ Thông tin",
                        label="Đại học Bách Khoa TP.HCM",
                        date="2017 – 2021",
                    )
                ],
            ),
            ExpectedSection(
                section_type="certifications",
                title="CHỨNG CHỈ",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="AWS Certified Solutions Architect – Associate",
                        date="2023",
                    ),
                    ExpectedBlock(
                        "entry",
                        title="Google Cloud Professional Data Engineer",
                        date="2023",
                    ),
                ],
            ),
            ExpectedSection(
                section_type="publications",
                title="CÔNG BỐ KHOA HỌC",
                blocks=[
                    ExpectedBlock(
                        "publication",
                        title="Multi-modal Video Retrieval using Graph Neural Networks and Transformers",
                        authors="Nguyen Van Duy, Le Thi Mai",
                        venue="IEEE ICIP 2022",
                    ),
                ],
                lines_must_join=[0],  # "Graph Neural Networks" wraps
            ),
            ExpectedSection(
                section_type="languages",
                title="NGÔN NGỮ",
                blocks=[
                    ExpectedBlock("paragraph", text="Tiếng Việt (Bản xứ)"),
                    ExpectedBlock(
                        "paragraph", text="Tiếng Anh (IELTS 7.0 – thành thạo)"
                    ),
                ],
            ),
        ],
        content_counts={"sections": 7, "entries": 5, "bullets": 8, "skill_groups": 4},
        failure_modes=[
            "first_heading_missing: 'TÓM TẮT' summary at top of CV not detected as section",
            "wrapped_project_bullets: 'sử dụng' becomes bold headline",
            "publication_wrap: 'Graph Neural Networks' becomes bold headline",
            "page_boundary: page 2 content may merge with page 1 footer",
        ],
    )
)


# 2. Wrapped project bullets
FIXTURES.append(
    CVFixture(
        name="wrapped_project_bullets",
        description="Project bullets that wrap to the next physical line in PDF extraction.",
        raw_text=(
            "LE THI MAI\n"
            "Data Scientist | mai.lt@email.com | +84 91 234 5678\n\n"
            "PROJECTS\n"
            "Customer Churn Prediction System\n"
            "• Developed an ML pipeline using Scikit-learn and XGBoost\n"
            "  that reduced customer churn by 23% within 6 months\n"
            "• Built feature engineering workflows processing 2M+ rows\n"
            "  of customer data daily\n"
            "• Deployed model on AWS SageMaker with real-time inference\n"
            "  API serving 10k requests per day\n\n"
            "TECHNICAL SKILLS\n"
            "Machine Learning: Scikit-learn, XGBoost, TensorFlow, PyTorch\n"
            "Programming: Python, R, SQL, Java\n"
            "Big Data: Spark, Hadoop, Hive\n"
            "Cloud: AWS SageMaker, EC2, S3, Google Cloud Platform\n"
            "Tools: Docker, Kubernetes, MLflow, Airflow, Git\n\n"
            "EDUCATION\n"
            "Master of Science in Data Science\n"
            "FPT University | 2019 – 2021 | GPA: 3.7/4.0\n"
            "Bachelor of Science in Mathematics\n"
            "HCMC University of Science | 2015 – 2019 | GPA: 3.6/4.0\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="projects",
                title="PROJECTS",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Customer Churn Prediction System",
                        bullets=[
                            "Developed an ML pipeline using Scikit-learn and XGBoost that reduced customer churn by 23% within 6 months",
                            "Built feature engineering workflows processing 2M+ rows of customer data daily",
                            "Deployed model on AWS SageMaker with real-time inference API serving 10k requests per day",
                        ],
                    ),
                ],
                lines_must_join=[2, 4, 7],  # continuation lines after each bullet
            ),
            ExpectedSection(
                section_type="skills",
                title="TECHNICAL SKILLS",
                blocks=[
                    ExpectedBlock(
                        "skill_group",
                        label="Machine Learning",
                        skills=["Scikit-learn", "XGBoost", "TensorFlow", "PyTorch"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Programming",
                        skills=["Python", "R", "SQL", "Java"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Big Data",
                        skills=["Spark", "Hadoop", "Hive"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Cloud",
                        skills=["AWS SageMaker", "EC2", "S3", "Google Cloud Platform"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Tools",
                        skills=["Docker", "Kubernetes", "MLflow", "Airflow", "Git"],
                    ),
                ],
            ),
            ExpectedSection(
                section_type="education",
                title="EDUCATION",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Master of Science in Data Science",
                        label="FPT University",
                        date="2019 – 2021",
                    ),
                    ExpectedBlock(
                        "entry",
                        title="Bachelor of Science in Mathematics",
                        label="HCMC University of Science",
                        date="2015 – 2019",
                    ),
                ],
            ),
        ],
        content_counts={"sections": 3, "entries": 4, "bullets": 3, "skill_groups": 5},
        failure_modes=[
            "wrapped_bullet_headline: 'that reduced customer churn' becomes bold",
            "wrapped_bullet_headline: 'of customer data daily' becomes bold",
            "wrapped_bullet_headline: 'API serving 10k requests' becomes bold",
            "skill_continuation_bold: 'XGBoost, TensorFlow' becomes bold (index === 0 after wrap)",
        ],
    )
)


# 3. Wrapped skill groups
FIXTURES.append(
    CVFixture(
        name="wrapped_skill_groups",
        description="Skills that wrap across physical lines and get bolded as headings.",
        raw_text=(
            "TRAN MINH HOANG\n"
            "Frontend Engineer | hoang.tm@email.com\n\n"
            "SKILLS\n"
            "Languages: TypeScript, JavaScript, HTML5, CSS3, Python\n"
            "Frameworks: React, Next.js, Vue.js, Angular, Svelte\n"
            "Styling: Tailwind CSS, Styled Components, Material UI,\n"
            "  Bootstrap, CSS-in-JS, Sass/Less\n"
            "State Management: Redux, Zustand, Recoil, Jotai, Pinia\n"
            "Testing: Jest, Cypress, React Testing Library, Playwright\n"
            "Tools: Webpack, Vite, ESLint, Prettier, Husky, lint-staged\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="skills",
                title="SKILLS",
                blocks=[
                    ExpectedBlock(
                        "skill_group",
                        label="Languages",
                        skills=["TypeScript", "JavaScript", "HTML5", "CSS3", "Python"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Frameworks",
                        skills=["React", "Next.js", "Vue.js", "Angular", "Svelte"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Styling",
                        skills=[
                            "Tailwind CSS",
                            "Styled Components",
                            "Material UI",
                            "Bootstrap",
                            "CSS-in-JS",
                            "Sass/Less",
                        ],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="State Management",
                        skills=["Redux", "Zustand", "Recoil", "Jotai", "Pinia"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Testing",
                        skills=[
                            "Jest",
                            "Cypress",
                            "React Testing Library",
                            "Playwright",
                        ],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Tools",
                        skills=[
                            "Webpack",
                            "Vite",
                            "ESLint",
                            "Prettier",
                            "Husky",
                            "lint-staged",
                        ],
                    ),
                ],
                lines_must_join=[3],  # "Bootstrap, CSS-in-JS" wraps from previous
            ),
        ],
        content_counts={"sections": 1, "skill_groups": 6},
        failure_modes=[
            "skill_continuation_bold: 'Bootstrap, CSS-in-JS, Sass/Less' becomes bold",
            "skill_continuation_bold: 'Jotai, Pinia' becomes bold",
            "wrapped_skill_as_heading: 'Bootstrap' recognized as entry title",
        ],
    )
)


# 4. Multi-line publications
FIXTURES.append(
    CVFixture(
        name="multi_line_publications",
        description="Academic publications spanning 3-4 physical lines.",
        raw_text=(
            "PHAM VAN THANG\n"
            "Research Engineer | thang.pv@email.com\n\n"
            "PUBLICATIONS\n"
            "Van Thang Pham, Nguyen Van Duy, 'Efficient Multi-modal\n"
            "Retrieval for Video Understanding via Contrastive Pre-training,'\n"
            "Proceedings of the IEEE/CVF Conference on Computer Vision\n"
            "and Pattern Recognition (CVPR), 2023.\n\n"
            "Le Thi Mai, Van Thang Pham, 'Self-Supervised Representation\n"
            "Learning for Industrial Anomaly Detection,' Journal of Machine\n"
            "Learning Research, vol. 24, no. 12, pp. 1-35, 2023.\n\n"
            "Tran Minh Hoang, 'Adaptive Attention Mechanisms for Real-Time\n"
            "Object Detection in Resource-Constrained Edge Devices,' ACM\n"
            "International Conference on Multimedia (MM), 2024. — Under Review\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="publications",
                title="PUBLICATIONS",
                blocks=[
                    ExpectedBlock(
                        "publication",
                        title="Efficient Multi-modal Retrieval for Video Understanding via Contrastive Pre-training",
                        authors="Van Thang Pham, Nguyen Van Duy",
                        venue="IEEE/CVF CVPR, 2023",
                    ),
                    ExpectedBlock(
                        "publication",
                        title="Self-Supervised Representation Learning for Industrial Anomaly Detection",
                        authors="Le Thi Mai, Van Thang Pham",
                        venue="Journal of Machine Learning Research, vol. 24, no. 12, pp. 1-35, 2023",
                    ),
                    ExpectedBlock(
                        "publication",
                        title="Adaptive Attention Mechanisms for Real-Time Object Detection in Resource-Constrained Edge Devices",
                        authors="Tran Minh Hoang",
                        venue="ACM MM, 2024",
                        status="Under Review",
                    ),
                ],
                lines_must_join=[1, 2, 5, 7],
            ),
        ],
        content_counts={"sections": 1, "publications": 3},
        failure_modes=[
            "publication_title_continuation: 'Retrieval for Video Understanding' becomes bold",
            "publication_continuation: 'and Pattern Recognition (CVPR)' becomes bold",
            "publication_continuation: 'Learning Research, vol. 24' becomes bold",
            "publication_continuation: 'ACM' becomes bold standalone",
        ],
    )
)


# 5. Multiple work-experience records at same company
FIXTURES.append(
    CVFixture(
        name="multiple_experience_records_same_company",
        description="Candidate with multiple roles at one employer.",
        raw_text=(
            "HOANG MINH DUY\n"
            "Software Engineer | dui.hmd@email.com | Hanoi\n\n"
            "WORK EXPERIENCE\n"
            "VNG Corporation\n"
            "Senior Software Engineer | Mar 2024 – Present\n"
            "• Lead a team of 5 engineers building notification platform\n"
            "• Architect event-driven microservices handling 1M events/day\n\n"
            "Software Engineer | Jan 2022 – Feb 2024\n"
            "• Built push notification service with FCM integration\n"
            "• Reduced latency by 35% through async processing patterns\n\n"
            "Intern Software Engineer | Jun 2021 – Dec 2021\n"
            "• Developed internal dashboard for monitoring service health\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="experience",
                title="WORK EXPERIENCE",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Senior Software Engineer",
                        label="VNG Corporation",
                        date="Mar 2024 – Present",
                        bullets=[
                            "Lead a team of 5 engineers building notification platform",
                            "Architect event-driven microservices handling 1M events/day",
                        ],
                    ),
                    ExpectedBlock(
                        "entry",
                        title="Software Engineer",
                        label="VNG Corporation",
                        date="Jan 2022 – Feb 2024",
                        bullets=[
                            "Built push notification service with FCM integration",
                            "Reduced latency by 35% through async processing patterns",
                        ],
                    ),
                    ExpectedBlock(
                        "entry",
                        title="Intern Software Engineer",
                        label="VNG Corporation",
                        date="Jun 2021 – Dec 2021",
                        bullets=[
                            "Developed internal dashboard for monitoring service health"
                        ],
                    ),
                ],
            ),
        ],
        content_counts={"sections": 1, "entries": 3},
        failure_modes=[
            "entry_boundary: Second role 'Software Engineer | Jan 2022' may not be recognized as separate entry",
            "internship_title: 'Intern' may be stripped from title",
        ],
    )
)


# 6. Vietnamese headings only
FIXTURES.append(
    CVFixture(
        name="vietnamese_headings_only",
        description="CV using exclusively Vietnamese section headings.",
        raw_text=(
            "DO THI LAM\n"
            "Nhân viên Marketing | lam.dt@email.com | Da Nang\n\n"
            "TÓM TẮT NGHỀ NGHIỆP\n"
            "Chuyên viên marketing số với 4 năm kinh nghiệm trong\n"
            "ngành thương mại điện tử.\n\n"
            "KINH NGHIỆM LÀM VIỆC\n"
            "Tiki.vn\n"
            "Marketing Specialist | Jul 2022 – Present\n"
            "• Quản lý chiến dịch Facebook Ads với ngân sách 500M VND/tháng\n"
            "• Tăng trưởng traffic website 60% qua SEO\n\n"
            "SHope Vietnam\n"
            "Marketing Intern | Jan 2021 – Jun 2022\n"
            "• Hỗ trợ content creation cho social media\n"
            "• Phân tích dữ liệu người dùng bằng Google Analytics\n\n"
            "KỸ NĂNG\n"
            "Digital Marketing: SEO, SEM, Facebook Ads, Google Ads\n"
            "Content: Copywriting, Content Strategy, Social Media\n"
            "Analytics: Google Analytics, Google Tag Manager, Data Studio\n"
            "Tools: WordPress, Canva, Figma, Adobe Photoshop\n\n"
            "HỌC VẤN\n"
            "Đại học Kinh tế TP.HCM\n"
            "Cử nhân Marketing | 2017 – 2021\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="custom",
                title="TÓM TẮT NGHỀ NGHIỆP",
                blocks=[
                    ExpectedBlock(
                        "paragraph",
                        text="Chuyên viên marketing số với 4 năm kinh nghiệm trong ngành thương mại điện tử.",
                    )
                ],
                lines_must_join=[1],
            ),
            ExpectedSection(
                section_type="experience",
                title="KINH NGHIỆM LÀM VIỆC",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Marketing Specialist",
                        label="Tiki.vn",
                        date="Jul 2022 – Present",
                        bullets=[
                            "Quản lý chiến dịch Facebook Ads với ngân sách 500M VND/tháng",
                            "Tăng trưởng traffic website 60% qua SEO",
                        ],
                    ),
                    ExpectedBlock(
                        "entry",
                        title="Marketing Intern",
                        label="SHope Vietnam",
                        date="Jan 2021 – Jun 2022",
                        bullets=[
                            "Hỗ trợ content creation cho social media",
                            "Phân tích dữ liệu người dùng bằng Google Analytics",
                        ],
                    ),
                ],
            ),
            ExpectedSection(
                section_type="skills",
                title="KỸ NĂNG",
                blocks=[
                    ExpectedBlock(
                        "skill_group",
                        label="Digital Marketing",
                        skills=["SEO", "SEM", "Facebook Ads", "Google Ads"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Content",
                        skills=["Copywriting", "Content Strategy", "Social Media"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Analytics",
                        skills=[
                            "Google Analytics",
                            "Google Tag Manager",
                            "Data Studio",
                        ],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Tools",
                        skills=["WordPress", "Canva", "Figma", "Adobe Photoshop"],
                    ),
                ],
            ),
            ExpectedSection(
                section_type="education",
                title="HỌC VẤN",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Cử nhân Marketing",
                        label="Đại học Kinh tế TP.HCM",
                        date="2017 – 2021",
                    )
                ],
            ),
        ],
        content_counts={"sections": 4, "entries": 3, "bullets": 4, "skill_groups": 4},
        failure_modes=[
            "vietnamese_heading_missing: 'TÓM TẮT NGHỀ NGHIỆP' may not map to summary",
            "vietnamese_heading_missing: 'KINH NGHIỆM LÀM VIỆC' may not map to experience",
            "wrapped_summary: 'trong ngành thương mại điện tử' becomes bold headline",
        ],
    )
)


# 7. English headings only
FIXTURES.append(
    CVFixture(
        name="english_headings_only",
        description="CV with standard English section headings.",
        raw_text=(
            "JAMES WILSON\n"
            "Product Manager | james.w@email.com | London, UK\n\n"
            "PROFESSIONAL SUMMARY\n"
            "Product manager with 6 years of experience building B2B SaaS\n"
            "platforms. Passionate about data-driven decision making and\n"
            "user-centric design.\n\n"
            "WORK EXPERIENCE\n"
            "Stripe\n"
            "Senior Product Manager | 2022 – Present\n"
            "• Launched Stripe Billing v2, increasing revenue by 15%\n"
            "• Managed a team of 3 PMs overseeing payments infrastructure\n\n"
            "Shopify\n"
            "Product Manager | 2019 – 2022\n"
            "• Shipped merchant analytics dashboard used by 500k+ sellers\n"
            "• Defined product roadmap for checkout optimization\n\n"
            "SKILLS\n"
            "Product: Roadmapping, A/B Testing, User Research, Data Analysis\n"
            "Technical: SQL, Python, React, GraphQL\n"
            "Tools: Jira, Confluence, Figma, Amplitude, Mixpanel\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="custom",
                title="PROFESSIONAL SUMMARY",
                blocks=[
                    ExpectedBlock(
                        "paragraph",
                        text="Product manager with 6 years of experience building B2B SaaS platforms. Passionate about data-driven decision making and user-centric design.",
                    )
                ],
                lines_must_join=[1, 2],
            ),
            ExpectedSection(
                section_type="experience",
                title="WORK EXPERIENCE",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Senior Product Manager",
                        label="Stripe",
                        date="2022 – Present",
                        bullets=[
                            "Launched Stripe Billing v2, increasing revenue by 15%",
                            "Managed a team of 3 PMs overseeing payments infrastructure",
                        ],
                    ),
                    ExpectedBlock(
                        "entry",
                        title="Product Manager",
                        label="Shopify",
                        date="2019 – 2022",
                        bullets=[
                            "Shipped merchant analytics dashboard used by 500k+ sellers",
                            "Defined product roadmap for checkout optimization",
                        ],
                    ),
                ],
            ),
            ExpectedSection(
                section_type="skills",
                title="SKILLS",
                blocks=[
                    ExpectedBlock(
                        "skill_group",
                        label="Product",
                        skills=[
                            "Roadmapping",
                            "A/B Testing",
                            "User Research",
                            "Data Analysis",
                        ],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Technical",
                        skills=["SQL", "Python", "React", "GraphQL"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Tools",
                        skills=["Jira", "Confluence", "Figma", "Amplitude", "Mixpanel"],
                    ),
                ],
            ),
        ],
        content_counts={"sections": 2, "entries": 2, "bullets": 4, "skill_groups": 3},
        failure_modes=[
            "first_heading_missing: 'PROFESSIONAL SUMMARY' at top of CV not detected as section",
            "wrapped_summary: 'user-centric design' becomes bold headline",
        ],
    )
)


# 8. Two-column CV (sidebar + main)
FIXTURES.append(
    CVFixture(
        name="two_column_cv",
        description="CV with sidebar layout — pdfplumber reads left-to-right across columns.",
        raw_text=(
            "NGUYEN THI HOA | hoa.nt@email.com | +84 98 765 4321 | HCMC\n"
            "Backend Developer\n"
            "EDUCATION\n"
            "Bachelor of Computer Science\n"
            "University of Science, VNU-HCM | 2018-2022\n"
            "KINH NGHIỆM LÀM VIỆC\n"
            "FPT Software\n"
            "Backend Developer | Mar 2022 – Present\n"
            "• Developed RESTful APIs for banking applications\n"
            "• Implemented OAuth 2.0 authentication for 3 client apps\n"
            "SKILLS\n"
            "Java, Spring Boot, Python, FastAPI, PostgreSQL, Docker\n"
            "DỰ ÁN\n"
            "E-Commerce Platform\n"
            "• Built shopping cart and payment integration\n"
            "• Deployed on AWS using ECS and RDS\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="experience",
                title="KINH NGHIỆM LÀM VIỆC",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Backend Developer",
                        label="FPT Software",
                        date="Mar 2022 – Present",
                        bullets=[
                            "Developed RESTful APIs for banking applications",
                            "Implemented OAuth 2.0 authentication for 3 client apps",
                        ],
                    ),
                ],
            ),
            ExpectedSection(
                section_type="skills",
                title="SKILLS",
                blocks=[
                    ExpectedBlock(
                        "skill_group",
                        label="Skills",
                        skills=[
                            "Java",
                            "Spring Boot",
                            "Python",
                            "FastAPI",
                            "PostgreSQL",
                            "Docker",
                        ],
                    )
                ],
            ),
            ExpectedSection(
                section_type="projects",
                title="DỰ ÁN",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="E-Commerce Platform",
                        bullets=[
                            "Built shopping cart and payment integration",
                            "Deployed on AWS using ECS and RDS",
                        ],
                    ),
                ],
            ),
        ],
        content_counts={"sections": 3, "entries": 2, "bullets": 4, "skill_groups": 1},
        failure_modes=[
            "column_order: 'EDUCATION' and 'Bách' appear interleaved with sidebar items",
            "column_merge: sidebar contact info appears mid-paragraph",
        ],
    )
)


# 9. CV without bullet characters
FIXTURES.append(
    CVFixture(
        name="no_bullet_characters",
        description="CV where bullets are plain dashes or hyphens.",
        raw_text=(
            "LE QUOC NAM\n"
            "DevOps Engineer | nam.lq@email.com\n\n"
            "EXPERIENCE\n"
            "AWS Consulting\n"
            "DevOps Engineer | 2021 – Present\n"
            "- Designed and implemented CI/CD pipelines using Jenkins and\n"
            "  GitLab CI for 15 microservices\n"
            "- Automated infrastructure provisioning with Terraform\n"
            "- Reduced deployment time from 2 hours to 15 minutes\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="experience",
                title="EXPERIENCE",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="DevOps Engineer",
                        label="AWS Consulting",
                        date="2021 – Present",
                        bullets=[
                            "Designed and implemented CI/CD pipelines using Jenkins and GitLab CI for 15 microservices",
                            "Automated infrastructure provisioning with Terraform",
                            "Reduced deployment time from 2 hours to 15 minutes",
                        ],
                    ),
                ],
                lines_must_join=[2],
            ),
        ],
        content_counts={"sections": 1, "entries": 1, "bullets": 3},
        failure_modes=[
            "no_bullet: lines starting with '-' are not recognized as bullets",
            "no_bullet_headline: 'GitLab CI for 15 microservices' becomes bold",
            "no_bullet_headline: 'Reduced deployment time' becomes bold (first non-bullet after dash)",
        ],
    )
)


# 10. Company, role, date on separate lines
FIXTURES.append(
    CVFixture(
        name="separate_metadata_lines",
        description="Each piece of experience metadata on its own line.",
        raw_text=(
            "PHAM THI BAN\n"
            "QA Engineer | ban.pt@email.com | Hanoi\n\n"
            "EXPERIENCE\n"
            "PTIT (Post and Telecommunications Institute of Technology)\n"
            "QA Engineer\n"
            "Hanoi, Vietnam\n"
            "September 2021 – Present\n"
            "- Designed and executed 500+ test cases for student management system\n"
            "- Automated regression testing using Selenium WebDriver\n"
            "- Reduced bug escape rate by 30%\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="experience",
                title="EXPERIENCE",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="QA Engineer",
                        label="PTIT",
                        location="Hanoi, Vietnam",
                        date="September 2021 – Present",
                        bullets=[
                            "Designed and executed 500+ test cases for student management system",
                            "Automated regression testing using Selenium WebDriver",
                            "Reduced bug escape rate by 30%",
                        ],
                    ),
                ],
            ),
        ],
        content_counts={"sections": 1, "entries": 1, "bullets": 3},
        failure_modes=[
            "separate_metadata: 'Hanoi, Vietnam' on its own line becomes a bold entry title",
            "separate_metadata: 'September 2021 – Present' may become a section heading",
        ],
    )
)


# 11. Company, role, date on same line
FIXTURES.append(
    CVFixture(
        name="shared_metadata_line",
        description="All experience metadata on one line.",
        raw_text=(
            "NGUYEN QUOC ANH\n"
            "Fullstack Developer | anh.nq@email.com\n\n"
            "EXPERIENCE\n"
            "Software Engineer at Viettel Digital | Hanoi | 2020-2024\n"
            "- Developed microservices using Java Spring Boot\n"
            "- Built React frontend for internal dashboard\n"
            "- Mentored 2 junior developers\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="experience",
                title="EXPERIENCE",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Software Engineer",
                        label="Viettel Digital",
                        location="Hanoi",
                        date="2020-2024",
                        bullets=[
                            "Developed microservices using Java Spring Boot",
                            "Built React frontend for internal dashboard",
                            "Mentored 2 junior developers",
                        ],
                    ),
                ],
            ),
        ],
        content_counts={"sections": 1, "entries": 1, "bullets": 3},
        failure_modes=[
            "shared_metadata: entire line 'Software Engineer at Viettel Digital...' becomes one item",
            "shared_metadata: 'at Viettel Digital' not parsed into organization field",
        ],
    )
)


# 12. Sections spanning page boundaries
FIXTURES.append(
    CVFixture(
        name="page_boundary_span",
        description="A section starts on page 1 and continues on page 2.",
        raw_text=(
            "TRẦN VĂN BẢO\n"
            "Data Engineer | bao.tv@email.com | HCMC\n\n"
            "EXPERIENCE\n"
            "MoMo (Momo Global JSC)\n"
            "Data Engineer | Feb 2022 – Present\n"
            "- Built ETL pipelines processing 50M+ transactions/month\n"
            "- Optimized Airflow DAGs reducing pipeline runtime by 45%\n"
            "- Designed data lake architecture on AWS S3 and Glue\n"
            "- Created real-time analytics dashboards using Looker\n"
            "- Implemented data quality monitoring with Great Expectations\n\n"
            "VNG Corporation\n"
            "Data Analyst Intern | Jul 2021 – Jan 2022\n"
            "- Analyzed user behavior data for Zalo Pay\n"
            "- Created weekly reports using SQL and Tableau\n\n"
            "--- PAGE 2 ---\n"
            "SKILLS\n"
            "Data Engineering: Apache Spark, Airflow, Kafka, dbt, Snowflake\n"
            "Programming: Python, SQL, Scala, R\n"
            "Cloud: AWS (S3, Glue, Redshift, EMR), GCP BigQuery\n"
            "Tools: Git, Docker, Kubernetes, Terraform\n\n"
            "EDUCATION\n"
            "Master of Data Science\n"
            "FPT University | 2019 – 2021\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="experience",
                title="EXPERIENCE",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Data Engineer",
                        label="MoMo (Momo Global JSC)",
                        date="Feb 2022 – Present",
                        bullets=[
                            "Built ETL pipelines processing 50M+ transactions/month",
                            "Optimized Airflow DAGs reducing pipeline runtime by 45%",
                            "Designed data lake architecture on AWS S3 and Glue",
                            "Created real-time analytics dashboards using Looker",
                            "Implemented data quality monitoring with Great Expectations",
                        ],
                    ),
                    ExpectedBlock(
                        "entry",
                        title="Data Analyst Intern",
                        label="VNG Corporation",
                        date="Jul 2021 – Jan 2022",
                        bullets=[
                            "Analyzed user behavior data for Zalo Pay",
                            "Created weekly reports using SQL and Tableau",
                        ],
                    ),
                ],
            ),
            ExpectedSection(
                section_type="skills",
                title="SKILLS",
                blocks=[
                    ExpectedBlock(
                        "skill_group",
                        label="Data Engineering",
                        skills=["Apache Spark", "Airflow", "Kafka", "dbt", "Snowflake"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Programming",
                        skills=["Python", "SQL", "Scala", "R"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Cloud",
                        skills=["AWS (S3, Glue, Redshift, EMR)", "GCP BigQuery"],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Tools",
                        skills=["Git", "Docker", "Kubernetes", "Terraform"],
                    ),
                ],
            ),
            ExpectedSection(
                section_type="education",
                title="EDUCATION",
                blocks=[
                    ExpectedBlock(
                        "entry",
                        title="Master of Data Science",
                        label="FPT University",
                        date="2019 – 2021",
                    )
                ],
            ),
        ],
        content_counts={"sections": 3, "entries": 2, "bullets": 7, "skill_groups": 4},
        failure_modes=[
            "page_boundary_section: 'SKILLS' on page 2 may merge into EXPERIENCE section",
            "page_boundary_entry: VNG entry may lose company name if on page boundary",
        ],
    )
)


# 13. Managerial word wrapped (specific test for 'managerial' matching 'manager')
FIXTURES.append(
    CVFixture(
        name="managerial_word_boundary",
        description="Word 'managerial' should not trigger manager role detection.",
        raw_text=(
            "LE MINH TRIET\n"
            "Software Engineer | triet.lm@email.com\n\n"
            "SKILLS\n"
            "Leadership: Team management, stakeholder communication,\n"
            "  managerial interview scenarios, conflict resolution\n"
            "Technical: Python, Django, PostgreSQL, Redis\n"
        ),
        expected_sections=[
            ExpectedSection(
                section_type="skills",
                title="SKILLS",
                blocks=[
                    ExpectedBlock(
                        "skill_group",
                        label="Leadership",
                        skills=[
                            "Team management",
                            "stakeholder communication",
                            "managerial interview scenarios",
                            "conflict resolution",
                        ],
                    ),
                    ExpectedBlock(
                        "skill_group",
                        label="Technical",
                        skills=["Python", "Django", "PostgreSQL", "Redis"],
                    ),
                ],
                lines_must_join=[2],  # "managerial interview scenarios" wraps
            ),
        ],
        content_counts={"sections": 1, "skill_groups": 2},
        failure_modes=[
            "managerial_match: 'managerial' contains 'manager' and may be detected as a manager role",
            "managerial_continuation_bold: 'managerial interview scenarios' becomes bold (wraps from '  ')",
            "word_boundary: 'managerial interview scenarios' should stay as skill, not become a heading",
        ],
    )
)
