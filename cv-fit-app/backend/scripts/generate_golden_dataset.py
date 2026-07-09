from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


@dataclass(frozen=True)
class JobProfile:
    role: str
    company: str
    domain: str
    city: str
    level: str
    years: str
    stack: list[str]
    responsibilities: list[str]
    requirements: list[str]
    benefits: list[str]
    project: str


@dataclass(frozen=True)
class Candidate:
    name: str
    email: str
    phone: str
    city: str
    school: str


JOBS: list[JobProfile] = [
    JobProfile(
        role="ReactJS Developer",
        company="FinGo Vietnam",
        domain="fintech cho vay tiêu dùng và quản lý ví điện tử",
        city="TP. Hồ Chí Minh",
        level="Middle",
        years="2-4 năm",
        stack=["ReactJS", "TypeScript", "Redux Toolkit", "Next.js", "REST API", "Tailwind CSS", "Jest"],
        responsibilities=[
            "Phát triển các màn hình web cho luồng định danh eKYC, quản lý khoản vay và dashboard giao dịch.",
            "Tối ưu hiệu năng rendering, bundle size và Core Web Vitals cho ứng dụng có hơn 300.000 người dùng/tháng.",
            "Phối hợp với Backend, Product Owner và QA để phân tích yêu cầu, review API contract và xử lý lỗi production.",
            "Viết unit test, integration test cho component quan trọng và tham gia code review hằng tuần.",
        ],
        requirements=[
            "Có kinh nghiệm thực tế với ReactJS, TypeScript, Redux Toolkit hoặc Zustand.",
            "Hiểu tốt REST API, authentication flow, xử lý form phức tạp và responsive UI.",
            "Biết Next.js, Tailwind CSS, Jest/React Testing Library là lợi thế.",
            "Có tư duy sản phẩm, giao tiếp rõ ràng và đọc hiểu tài liệu tiếng Anh kỹ thuật.",
        ],
        benefits=[
            "Lương 28-45 triệu gross, review 2 lần/năm.",
            "Bảo hiểm sức khỏe PVI, laptop MacBook, ngân sách học tập 12 triệu/năm.",
            "Hybrid 3 ngày/tuần tại văn phòng Quận 1.",
        ],
        project="nền tảng phê duyệt khoản vay online",
    ),
    JobProfile(
        role="Backend Node.js Developer",
        company="TikiNow Tech Hub",
        domain="thương mại điện tử và logistics giao hàng nhanh",
        city="TP. Hồ Chí Minh",
        level="Middle/Senior",
        years="3-5 năm",
        stack=["Node.js", "NestJS", "PostgreSQL", "Redis", "Kafka", "Docker", "AWS"],
        responsibilities=[
            "Thiết kế và xây dựng microservices cho đơn hàng, tồn kho và điều phối giao vận.",
            "Tối ưu API, database query và cache để đáp ứng lưu lượng cao trong các chiến dịch sale.",
            "Xây dựng event-driven workflow với Kafka, đảm bảo idempotency và observability.",
            "Tham gia thiết kế kiến trúc, viết tài liệu kỹ thuật, review code và hỗ trợ incident production.",
        ],
        requirements=[
            "Thành thạo Node.js, NestJS hoặc Express.js; hiểu sâu async processing và error handling.",
            "Có kinh nghiệm PostgreSQL/MySQL, Redis, message queue như Kafka hoặc RabbitMQ.",
            "Biết Docker, CI/CD, AWS ECS/Lambda/SQS là lợi thế.",
            "Ưu tiên ứng viên từng làm hệ thống có traffic lớn hoặc nghiệp vụ transactional.",
        ],
        benefits=[
            "Lương 35-60 triệu gross, thưởng hiệu suất theo quý.",
            "Cơ hội xử lý bài toán scale thật với hàng triệu đơn hàng.",
            "Gói bảo hiểm cao cấp, 15 ngày phép, flexible working time.",
        ],
        project="hệ thống fulfillment cho chiến dịch flash sale",
    ),
    JobProfile(
        role="AI Engineer",
        company="VietMed AI",
        domain="healthtech hỗ trợ phân tích hồ sơ bệnh án",
        city="Hà Nội",
        level="Middle",
        years="2-4 năm",
        stack=["Python", "PyTorch", "Transformers", "LangChain", "FastAPI", "Vector Database", "MLflow"],
        responsibilities=[
            "Xây dựng pipeline xử lý văn bản y tế tiếng Việt, trích xuất thực thể và phân loại hồ sơ.",
            "Fine-tune mô hình Transformer, đánh giá bằng precision, recall, F1-score và theo dõi drift.",
            "Phát triển API phục vụ inference, tích hợp vector search và RAG cho trợ lý nội bộ.",
            "Làm việc với bác sĩ chuyên môn để chuẩn hóa nhãn dữ liệu và phân tích lỗi mô hình.",
        ],
        requirements=[
            "Thành thạo Python, PyTorch hoặc TensorFlow, có kinh nghiệm NLP/LLM.",
            "Hiểu embedding, vector database, prompt engineering, RAG và evaluation dataset.",
            "Biết FastAPI, Docker, MLflow, Airflow là lợi thế.",
            "Có khả năng đọc paper, thử nghiệm có kiểm soát và trình bày kết quả bằng số liệu.",
        ],
        benefits=[
            "Lương 32-55 triệu gross, thưởng dự án nghiên cứu.",
            "Được tài trợ GPU cloud, khóa học AI và hội thảo chuyên ngành.",
            "Môi trường làm việc với dữ liệu có tác động xã hội rõ ràng.",
        ],
        project="trợ lý AI tóm tắt bệnh án tiếng Việt",
    ),
    JobProfile(
        role="Manual QA Tester",
        company="EduSmart Vietnam",
        domain="edtech quản lý lớp học trực tuyến",
        city="Đà Nẵng",
        level="Junior/Middle",
        years="1-3 năm",
        stack=["Test Case", "Regression Testing", "Jira", "Postman", "SQL cơ bản", "Agile/Scrum"],
        responsibilities=[
            "Phân tích requirement, viết test case, test scenario và chuẩn bị test data cho web/mobile app.",
            "Thực hiện functional testing, regression testing, smoke testing sau mỗi sprint.",
            "Log bug rõ ràng trên Jira, phối hợp với Developer để verify bug fix.",
            "Test API cơ bản bằng Postman và truy vấn database đơn giản để kiểm tra dữ liệu.",
        ],
        requirements=[
            "Có kinh nghiệm kiểm thử phần mềm web hoặc mobile từ 1 năm trở lên.",
            "Nắm vững quy trình test case, bug lifecycle, regression testing và Agile/Scrum.",
            "Biết Postman, SQL cơ bản; cẩn thận, giao tiếp tốt và tư duy phản biện.",
            "Ưu tiên ứng viên từng test sản phẩm giáo dục hoặc SaaS.",
        ],
        benefits=[
            "Lương 14-24 triệu gross, review lương 2 lần/năm.",
            "Đào tạo automation testing nếu có định hướng phát triển.",
            "Văn phòng trung tâm Đà Nẵng, hỗ trợ ăn trưa và gửi xe.",
        ],
        project="nền tảng lớp học trực tuyến cho trung tâm ngoại ngữ",
    ),
    JobProfile(
        role="DevOps Engineer",
        company="CloudMate Solutions",
        domain="cloud managed service cho doanh nghiệp Việt Nam",
        city="Hà Nội",
        level="Senior",
        years="4-6 năm",
        stack=["AWS", "Kubernetes", "Terraform", "Docker", "GitLab CI/CD", "Prometheus", "Grafana"],
        responsibilities=[
            "Thiết kế và vận hành hạ tầng Kubernetes multi-environment cho các hệ thống SaaS.",
            "Tự động hóa provisioning bằng Terraform, chuẩn hóa CI/CD pipeline và deployment strategy.",
            "Thiết lập monitoring, alerting, logging tập trung và quy trình incident response.",
            "Tối ưu chi phí cloud, bảo mật secret, backup/restore và disaster recovery plan.",
        ],
        requirements=[
            "Có kinh nghiệm AWS, Kubernetes, Docker, Terraform trong môi trường production.",
            "Thành thạo CI/CD với GitLab CI, GitHub Actions hoặc Jenkins.",
            "Hiểu networking, Linux, observability, SRE practice và bảo mật hạ tầng.",
            "Có chứng chỉ AWS hoặc CKA là lợi thế.",
        ],
        benefits=[
            "Lương 45-75 triệu gross, phụ cấp chứng chỉ quốc tế.",
            "Remote linh hoạt, ngân sách cloud lab cá nhân.",
            "Thưởng on-call và bảo hiểm sức khỏe cho gia đình.",
        ],
        project="nền tảng Kubernetes hosting cho khách hàng SaaS",
    ),
    JobProfile(
        role="Flutter Mobile Developer",
        company="MomoCare Lab",
        domain="ứng dụng chăm sóc sức khỏe cá nhân",
        city="TP. Hồ Chí Minh",
        level="Middle",
        years="2-4 năm",
        stack=["Flutter", "Dart", "Bloc", "Firebase", "REST API", "App Store", "Google Play"],
        responsibilities=[
            "Phát triển ứng dụng mobile đa nền tảng cho đặt lịch khám, nhắc thuốc và ví sức khỏe.",
            "Tối ưu trải nghiệm người dùng, crash-free rate, performance và offline caching.",
            "Tích hợp REST API, Firebase Analytics, push notification và deep link.",
            "Phối hợp với Designer, Backend và QA để release app lên App Store/Google Play.",
        ],
        requirements=[
            "Có kinh nghiệm Flutter/Dart từ 2 năm, hiểu state management như Bloc, Riverpod hoặc Provider.",
            "Đã từng release ứng dụng lên App Store hoặc Google Play.",
            "Hiểu mobile architecture, local storage, push notification và app lifecycle.",
            "Biết native Android/iOS là lợi thế.",
        ],
        benefits=[
            "Lương 25-45 triệu gross, thưởng release theo milestone.",
            "MacBook, device test lab, budget học mobile architecture.",
            "Hybrid tại Quận 3, giờ làm linh hoạt.",
        ],
        project="ứng dụng nhắc lịch khám và theo dõi sức khỏe",
    ),
    JobProfile(
        role="Data Engineer",
        company="RetailX Analytics",
        domain="phân tích dữ liệu bán lẻ omnichannel",
        city="TP. Hồ Chí Minh",
        level="Middle/Senior",
        years="3-5 năm",
        stack=["Python", "SQL", "Airflow", "Spark", "dbt", "BigQuery", "Kafka"],
        responsibilities=[
            "Xây dựng data pipeline batch và streaming cho đơn hàng, tồn kho, loyalty và marketing.",
            "Thiết kế data model, data mart và kiểm soát chất lượng dữ liệu phục vụ dashboard BI.",
            "Tối ưu ETL job, partitioning, cost query và SLA xử lý dữ liệu.",
            "Làm việc với Data Analyst, Product và Engineering để chuẩn hóa metric kinh doanh.",
        ],
        requirements=[
            "Thành thạo SQL, Python và có kinh nghiệm Airflow hoặc orchestration tương đương.",
            "Có kinh nghiệm Spark, BigQuery/Snowflake/Redshift, Kafka hoặc Pub/Sub.",
            "Hiểu data warehouse, dimensional modeling, dbt và data quality check.",
            "Ưu tiên ứng viên từng làm retail, ecommerce hoặc fintech data.",
        ],
        benefits=[
            "Lương 38-65 triệu gross, thưởng KPI dữ liệu.",
            "Data platform hiện đại, được tham gia thiết kế từ đầu.",
            "Bảo hiểm sức khỏe, hybrid 2 ngày/tuần.",
        ],
        project="customer 360 data platform cho chuỗi bán lẻ",
    ),
    JobProfile(
        role="Business Analyst IT",
        company="VNBank Digital",
        domain="ngân hàng số và thanh toán doanh nghiệp",
        city="Hà Nội",
        level="Middle",
        years="3-5 năm",
        stack=["BRD", "User Story", "UAT", "BPMN", "SQL", "Jira", "Figma"],
        responsibilities=[
            "Thu thập yêu cầu nghiệp vụ từ khối vận hành, pháp chế và sản phẩm ngân hàng số.",
            "Viết BRD, SRS, user story, acceptance criteria và mô hình hóa quy trình bằng BPMN.",
            "Phối hợp với UX/UI, Developer, QA để làm rõ scope, quản lý change request và hỗ trợ UAT.",
            "Truy vấn dữ liệu bằng SQL cơ bản để phân tích lỗi nghiệp vụ và đối soát giao dịch.",
        ],
        requirements=[
            "Có kinh nghiệm BA IT từ 3 năm, ưu tiên lĩnh vực banking, payment hoặc fintech.",
            "Nắm vững requirement elicitation, user story, UAT, BPMN và Agile/Scrum.",
            "Biết SQL cơ bản, Jira/Confluence, Figma hoặc công cụ wireframe.",
            "Giao tiếp tốt, viết tài liệu rõ ràng và quản lý stakeholder hiệu quả.",
        ],
        benefits=[
            "Lương 30-50 triệu gross, thưởng tháng 13 và bonus dự án.",
            "Được đào tạo nghiệp vụ ngân hàng và chứng chỉ BA.",
            "Văn phòng Ba Đình, bảo hiểm sức khỏe cao cấp.",
        ],
        project="cổng thanh toán doanh nghiệp cho ngân hàng số",
    ),
    JobProfile(
        role="Product Designer UI/UX",
        company="GrabLocal Vietnam",
        domain="marketplace dịch vụ địa phương",
        city="TP. Hồ Chí Minh",
        level="Middle",
        years="2-5 năm",
        stack=["Figma", "Design System", "User Research", "Prototype", "Usability Testing", "Mobile UX"],
        responsibilities=[
            "Thiết kế flow mobile/web cho đặt dịch vụ, quản lý booking và đánh giá nhà cung cấp.",
            "Thực hiện user research, usability testing và phân tích hành vi người dùng để cải thiện conversion.",
            "Xây dựng component trong design system, handoff rõ ràng cho engineering team.",
            "Làm việc chặt với Product Manager, Data Analyst và Developer trong quy trình discovery-delivery.",
        ],
        requirements=[
            "Có portfolio thể hiện quy trình thiết kế sản phẩm số thực tế.",
            "Thành thạo Figma, prototype, design system và mobile UX pattern.",
            "Biết đọc dữ liệu funnel, A/B testing và chuyển insight thành quyết định thiết kế.",
            "Giao tiếp tốt, có khả năng bảo vệ rationale thiết kế bằng bằng chứng.",
        ],
        benefits=[
            "Lương 28-48 triệu gross, MacBook và màn hình thiết kế.",
            "Budget user research, workshop và khóa học quốc tế.",
            "Hybrid, văn hóa product-led và feedback nhanh.",
        ],
        project="marketplace đặt dịch vụ sửa chữa tại nhà",
    ),
    JobProfile(
        role="Cybersecurity Analyst",
        company="SecureVN SOC",
        domain="dịch vụ giám sát an toàn thông tin 24/7",
        city="Hà Nội",
        level="Junior/Middle",
        years="1-3 năm",
        stack=["SIEM", "Splunk", "EDR", "MITRE ATT&CK", "Incident Response", "Linux", "Python"],
        responsibilities=[
            "Giám sát alert từ SIEM, EDR, firewall và phân loại mức độ rủi ro theo playbook.",
            "Điều tra incident, phân tích log, IOC, timeline tấn công và đề xuất biện pháp containment.",
            "Viết rule correlation, báo cáo sau sự cố và cập nhật knowledge base cho SOC.",
            "Phối hợp với khách hàng để xử lý phishing, malware, brute-force và data leakage.",
        ],
        requirements=[
            "Có kiến thức nền tảng networking, Linux, Windows log và bảo mật hệ thống.",
            "Biết SIEM như Splunk/QRadar/Elastic, EDR và quy trình incident response.",
            "Hiểu MITRE ATT&CK, OWASP Top 10; biết Python scripting là lợi thế.",
            "Sẵn sàng làm ca xoay và giao tiếp khách hàng rõ ràng.",
        ],
        benefits=[
            "Lương 18-32 triệu gross, phụ cấp ca trực và chứng chỉ bảo mật.",
            "Được đào tạo CompTIA Security+, CySA+, CEH.",
            "Môi trường SOC thực chiến với nhiều loại hình khách hàng.",
        ],
        project="trung tâm SOC giám sát hệ thống tài chính",
    ),
    JobProfile(
        role="Java Spring Boot Developer",
        company="FSoft Enterprise",
        domain="phần mềm doanh nghiệp cho khách hàng Nhật Bản",
        city="Đà Nẵng",
        level="Middle",
        years="2-5 năm",
        stack=["Java", "Spring Boot", "Spring Security", "MySQL", "REST API", "JUnit", "Docker"],
        responsibilities=[
            "Phát triển REST API cho hệ thống ERP, quản lý người dùng, phân quyền và workflow phê duyệt.",
            "Thiết kế database schema, viết unit test, integration test và xử lý bug trong sprint.",
            "Tối ưu câu query, cải thiện performance service và đảm bảo bảo mật API.",
            "Làm việc với BrSE, QA và khách hàng Nhật để làm rõ yêu cầu kỹ thuật.",
        ],
        requirements=[
            "Thành thạo Java, Spring Boot, Spring Security và JPA/Hibernate.",
            "Có kinh nghiệm MySQL/PostgreSQL, REST API, JUnit/Mockito và Docker.",
            "Hiểu OOP, design pattern, clean code và quy trình Agile/Scrum.",
            "Tiếng Anh đọc hiểu tốt; biết tiếng Nhật là lợi thế.",
        ],
        benefits=[
            "Lương 25-45 triệu gross, thưởng dự án và tháng 13.",
            "Đào tạo tiếng Nhật, chứng chỉ cloud và career path rõ ràng.",
            "Văn phòng Đà Nẵng, onsite Nhật Bản nếu phù hợp.",
        ],
        project="hệ thống ERP quản lý phê duyệt nội bộ",
    ),
    JobProfile(
        role="Golang Backend Developer",
        company="PayLoop Asia",
        domain="payment gateway cho merchant Đông Nam Á",
        city="TP. Hồ Chí Minh",
        level="Senior",
        years="4-7 năm",
        stack=["Golang", "gRPC", "PostgreSQL", "Redis", "Kafka", "Kubernetes", "Prometheus"],
        responsibilities=[
            "Xây dựng service thanh toán có độ sẵn sàng cao, xử lý settlement, refund và reconciliation.",
            "Thiết kế gRPC API, event schema, retry strategy và cơ chế idempotency cho giao dịch tài chính.",
            "Tối ưu throughput, latency, connection pool và monitoring bằng Prometheus/Grafana.",
            "Mentor developer khác, tham gia architecture review và postmortem sau incident.",
        ],
        requirements=[
            "Có kinh nghiệm Golang production từ 3 năm, hiểu concurrency, context, channel và profiling.",
            "Thành thạo PostgreSQL, Redis, Kafka hoặc message queue tương đương.",
            "Hiểu distributed system, idempotency, observability và Kubernetes.",
            "Ưu tiên ứng viên từng làm payment, banking hoặc hệ thống giao dịch lớn.",
        ],
        benefits=[
            "Lương 55-90 triệu gross, ESOP cho nhân sự chủ chốt.",
            "On-call allowance, bảo hiểm sức khỏe quốc tế.",
            "Được quyết định kiến trúc cho hệ thống payment regional.",
        ],
        project="payment gateway xử lý giao dịch merchant",
    ),
    JobProfile(
        role="Automation QA Engineer",
        company="Sendo Tech",
        domain="sàn thương mại điện tử Việt Nam",
        city="TP. Hồ Chí Minh",
        level="Middle",
        years="2-4 năm",
        stack=["Playwright", "Cypress", "TypeScript", "Postman", "API Testing", "CI/CD", "Jira"],
        responsibilities=[
            "Xây dựng automation test suite cho checkout, seller center và campaign promotion.",
            "Viết API test, E2E test, regression suite và tích hợp vào CI/CD pipeline.",
            "Phân tích flaky test, report coverage và phối hợp với Developer để giảm bug leakage.",
            "Định nghĩa test strategy cho các tính năng có rủi ro cao trước release.",
        ],
        requirements=[
            "Có kinh nghiệm automation testing với Playwright, Cypress hoặc Selenium.",
            "Biết TypeScript/JavaScript, API testing bằng Postman/Newman và CI/CD.",
            "Nắm vững test pyramid, regression testing, defect management và Agile.",
            "Ưu tiên ứng viên từng test checkout, payment hoặc ecommerce workflow.",
        ],
        benefits=[
            "Lương 25-42 triệu gross, thưởng release ổn định.",
            "Được xây dựng framework automation từ sớm.",
            "Hybrid, hỗ trợ thiết bị test và khóa học QA nâng cao.",
        ],
        project="automation suite cho luồng checkout ecommerce",
    ),
    JobProfile(
        role="iOS Developer",
        company="Traveloka Vietnam Lab",
        domain="du lịch trực tuyến và đặt vé",
        city="TP. Hồ Chí Minh",
        level="Middle",
        years="2-5 năm",
        stack=["Swift", "UIKit", "SwiftUI", "Combine", "REST API", "Unit Test", "App Store"],
        responsibilities=[
            "Phát triển tính năng tìm kiếm chuyến bay, đặt phòng và quản lý booking trên iOS.",
            "Tối ưu startup time, memory usage, crash-free users và trải nghiệm thanh toán.",
            "Viết unit test, snapshot test và phối hợp release qua TestFlight/App Store.",
            "Làm việc với Product, Backend và QA để xử lý edge case theo thị trường Việt Nam.",
        ],
        requirements=[
            "Có kinh nghiệm Swift, UIKit; biết SwiftUI và Combine là lợi thế.",
            "Hiểu iOS app lifecycle, memory management, networking, local storage.",
            "Đã từng release app lên App Store và xử lý crash log.",
            "Có tư duy UX, clean architecture và code review nghiêm túc.",
        ],
        benefits=[
            "Lương 32-55 triệu gross, MacBook Pro và iPhone test.",
            "Thưởng travel credit hằng năm, bảo hiểm sức khỏe.",
            "Hybrid và môi trường sản phẩm có người dùng lớn.",
        ],
        project="ứng dụng đặt chuyến bay và khách sạn",
    ),
    JobProfile(
        role="Android Kotlin Developer",
        company="BeRide Engineering",
        domain="gọi xe, giao hàng và ví tài xế",
        city="Hà Nội",
        level="Middle",
        years="2-5 năm",
        stack=["Kotlin", "Android SDK", "Jetpack Compose", "MVVM", "Coroutine", "Room", "Firebase"],
        responsibilities=[
            "Phát triển ứng dụng tài xế cho nhận chuyến, điều hướng, ví thu nhập và hỗ trợ khách hàng.",
            "Tối ưu realtime location, background service, offline mode và battery usage.",
            "Tích hợp REST API, Firebase Crashlytics, push notification và analytics event.",
            "Viết unit test, review code và phối hợp release theo từng khu vực.",
        ],
        requirements=[
            "Có kinh nghiệm Kotlin, Android SDK và MVVM/Clean Architecture.",
            "Biết Jetpack Compose, Coroutine/Flow, Room, WorkManager và Firebase.",
            "Hiểu performance mobile, location service và lifecycle.",
            "Ưu tiên ứng viên từng làm ride-hailing, logistics hoặc ứng dụng realtime.",
        ],
        benefits=[
            "Lương 30-52 triệu gross, thưởng theo hiệu quả sản phẩm.",
            "Thiết bị test đa dạng, hỗ trợ khóa học Android chuyên sâu.",
            "Văn phòng Cầu Giấy, giờ làm linh hoạt.",
        ],
        project="ứng dụng tài xế realtime cho gọi xe",
    ),
    JobProfile(
        role="Full-stack TypeScript Developer",
        company="PropTech Nexus",
        domain="SaaS quản lý môi giới bất động sản",
        city="TP. Hồ Chí Minh",
        level="Middle/Senior",
        years="3-6 năm",
        stack=["Next.js", "ReactJS", "Node.js", "TypeScript", "Prisma", "PostgreSQL", "AWS"],
        responsibilities=[
            "Phát triển end-to-end các module CRM, quản lý lead, lịch hẹn và báo cáo doanh thu.",
            "Thiết kế API, database schema, phân quyền và tối ưu UI cho người dùng sale cường độ cao.",
            "Xây dựng integration với email, Zalo OA, payment và hệ thống báo cáo.",
            "Tham gia quyết định kiến trúc, code review và cải thiện developer experience.",
        ],
        requirements=[
            "Thành thạo TypeScript, ReactJS/Next.js và Node.js.",
            "Có kinh nghiệm Prisma/TypeORM, PostgreSQL và thiết kế REST API.",
            "Biết AWS, CI/CD, testing và multi-tenant SaaS là lợi thế.",
            "Có khả năng làm việc độc lập, ownership cao và hiểu nghiệp vụ B2B SaaS.",
        ],
        benefits=[
            "Lương 40-70 triệu gross, ESOP theo hiệu quả.",
            "Product team nhỏ, quyền ảnh hưởng lớn lên roadmap kỹ thuật.",
            "Hybrid, laptop cao cấp và ngân sách học tập.",
        ],
        project="CRM SaaS cho môi giới bất động sản",
    ),
    JobProfile(
        role="WordPress/PHP Developer",
        company="MediaPlus Digital",
        domain="agency triển khai website marketing cho SME",
        city="TP. Hồ Chí Minh",
        level="Junior/Middle",
        years="1-3 năm",
        stack=["PHP", "WordPress", "WooCommerce", "MySQL", "HTML/CSS", "JavaScript", "SEO"],
        responsibilities=[
            "Xây dựng website WordPress, landing page, WooCommerce store và plugin tùy chỉnh theo brief.",
            "Tối ưu tốc độ tải trang, SEO technical, responsive layout và bảo mật cơ bản.",
            "Bảo trì website khách hàng, xử lý bug giao diện, form, payment và backup định kỳ.",
            "Phối hợp với Designer, Account và SEO team để bàn giao dự án đúng tiến độ.",
        ],
        requirements=[
            "Có kinh nghiệm PHP, WordPress theme/plugin và WooCommerce.",
            "Biết HTML/CSS, JavaScript, MySQL và nguyên tắc SEO technical.",
            "Có khả năng đọc brief, estimate task và hỗ trợ khách hàng.",
            "Ưu tiên ứng viên có portfolio website đã triển khai.",
        ],
        benefits=[
            "Lương 15-28 triệu gross, thưởng dự án.",
            "Được học thêm performance, security và headless CMS.",
            "Văn phòng Quận Bình Thạnh, môi trường agency năng động.",
        ],
        project="website thương mại điện tử cho doanh nghiệp SME",
    ),
    JobProfile(
        role="Unity Game Developer",
        company="SkyFox Games",
        domain="mobile game casual và hybrid-casual",
        city="Hà Nội",
        level="Middle",
        years="2-4 năm",
        stack=["Unity", "C#", "Mobile Game", "Ads SDK", "Firebase", "Addressables", "Git"],
        responsibilities=[
            "Phát triển gameplay, UI, level logic và hệ thống reward cho mobile game casual.",
            "Tối ưu FPS, memory, build size và tích hợp Ads SDK, Firebase Analytics, remote config.",
            "Phối hợp với Game Designer, Artist và UA team để thử nghiệm A/B và cải thiện retention.",
            "Sửa bug, refactor module cũ và chuẩn bị build Android/iOS cho soft launch.",
        ],
        requirements=[
            "Có kinh nghiệm Unity/C# và đã tham gia ít nhất một game mobile release.",
            "Hiểu game loop, physics cơ bản, animation, UI canvas và performance mobile.",
            "Biết Ads SDK, IAP, Firebase, Addressables là lợi thế.",
            "Có tư duy sản phẩm game, đọc chỉ số retention, ARPDAU, CPI.",
        ],
        benefits=[
            "Lương 22-38 triệu gross, thưởng theo hiệu quả game.",
            "Môi trường game studio, được tham gia soft launch quốc tế.",
            "PC cấu hình cao, snack, team building hằng quý.",
        ],
        project="mobile game casual cho thị trường global",
    ),
    JobProfile(
        role="ERP Functional Consultant",
        company="BizOne Consulting",
        domain="triển khai ERP cho sản xuất và phân phối",
        city="Hà Nội",
        level="Middle",
        years="3-5 năm",
        stack=["ERP", "Odoo", "SAP Business One", "Business Process", "UAT", "SQL", "Training"],
        responsibilities=[
            "Khảo sát quy trình mua hàng, bán hàng, kho, kế toán và sản xuất tại khách hàng.",
            "Cấu hình ERP, viết tài liệu giải pháp, hỗ trợ migration dữ liệu và kiểm thử UAT.",
            "Đào tạo key user, xử lý issue sau go-live và đề xuất cải tiến quy trình.",
            "Làm việc với Developer để mô tả customization cần thiết.",
        ],
        requirements=[
            "Có kinh nghiệm triển khai ERP/Odoo/SAP Business One từ 3 năm.",
            "Hiểu quy trình doanh nghiệp, đặc biệt mua hàng, bán hàng, kho hoặc kế toán.",
            "Biết SQL cơ bản, UAT, training user và viết tài liệu giải pháp.",
            "Sẵn sàng đi onsite khách hàng khi cần.",
        ],
        benefits=[
            "Lương 28-45 triệu gross, phụ cấp onsite và thưởng dự án.",
            "Được đào tạo chứng chỉ ERP và kỹ năng tư vấn.",
            "Môi trường tiếp xúc nhiều ngành nghề sản xuất, phân phối.",
        ],
        project="triển khai ERP cho nhà máy sản xuất bao bì",
    ),
    JobProfile(
        role="IT Support Specialist",
        company="Lotus Retail Group",
        domain="chuỗi bán lẻ thời trang trên toàn quốc",
        city="TP. Hồ Chí Minh",
        level="Junior",
        years="1-2 năm",
        stack=["Windows", "Microsoft 365", "LAN/Wi-Fi", "POS", "Helpdesk", "Asset Management"],
        responsibilities=[
            "Hỗ trợ người dùng nội bộ về máy tính, email, Microsoft 365, máy in và hệ thống POS.",
            "Quản lý ticket helpdesk, asset laptop, tài khoản người dùng và phân quyền cơ bản.",
            "Xử lý sự cố mạng LAN/Wi-Fi tại văn phòng và cửa hàng, phối hợp vendor khi cần.",
            "Viết hướng dẫn sử dụng, checklist onboarding/offboarding và báo cáo SLA hằng tháng.",
        ],
        requirements=[
            "Có kinh nghiệm IT Support/Helpdesk từ 1 năm, hiểu Windows, Microsoft 365 và mạng cơ bản.",
            "Biết xử lý sự cố POS, printer, LAN/Wi-Fi là lợi thế.",
            "Thái độ dịch vụ tốt, kiên nhẫn, ghi nhận ticket rõ ràng.",
            "Có thể di chuyển hỗ trợ cửa hàng trong nội thành.",
        ],
        benefits=[
            "Lương 12-20 triệu gross, phụ cấp điện thoại và di chuyển.",
            "Tháng 13, bảo hiểm đầy đủ, giảm giá nhân viên.",
            "Lộ trình lên System Admin hoặc IT Operations.",
        ],
        project="hệ thống helpdesk cho chuỗi cửa hàng bán lẻ",
    ),
]


CANDIDATES: list[Candidate] = [
    Candidate("Nguyen Minh Khoa", "khoa.nguyen@example.com", "0901 234 501", "TP. Hồ Chí Minh", "ĐH Bách Khoa TP.HCM"),
    Candidate("Tran Thi Bao Ngoc", "ngoc.tran@example.com", "0901 234 502", "TP. Hồ Chí Minh", "ĐH Khoa học Tự nhiên TP.HCM"),
    Candidate("Le Quang Huy", "huy.le@example.com", "0901 234 503", "Hà Nội", "ĐH Công nghệ - ĐHQGHN"),
    Candidate("Pham Thu Ha", "ha.pham@example.com", "0901 234 504", "Đà Nẵng", "ĐH Duy Tân"),
    Candidate("Hoang Anh Tuan", "tuan.hoang@example.com", "0901 234 505", "Hà Nội", "Học viện Công nghệ Bưu chính Viễn thông"),
    Candidate("Vu Thanh Lam", "lam.vu@example.com", "0901 234 506", "TP. Hồ Chí Minh", "ĐH FPT"),
    Candidate("Do My Linh", "linh.do@example.com", "0901 234 507", "TP. Hồ Chí Minh", "ĐH Kinh tế TP.HCM"),
    Candidate("Bui Gia Bao", "bao.bui@example.com", "0901 234 508", "Hà Nội", "ĐH Thương mại"),
    Candidate("Dang Nhat Nam", "nam.dang@example.com", "0901 234 509", "TP. Hồ Chí Minh", "ĐH Văn Lang"),
    Candidate("Nguyen Thi Mai Anh", "maianh.nguyen@example.com", "0901 234 510", "Hà Nội", "Học viện Kỹ thuật Mật mã"),
    Candidate("Tran Duc Anh", "ducanh.tran@example.com", "0901 234 511", "Đà Nẵng", "ĐH Bách Khoa Đà Nẵng"),
    Candidate("Le Minh Tri", "tri.le@example.com", "0901 234 512", "TP. Hồ Chí Minh", "ĐH Công nghệ Thông tin - ĐHQG TP.HCM"),
    Candidate("Pham Bao Chau", "chau.pham@example.com", "0901 234 513", "TP. Hồ Chí Minh", "ĐH Sư phạm Kỹ thuật TP.HCM"),
    Candidate("Ho Thi Khanh Linh", "khanhlinh.ho@example.com", "0901 234 514", "TP. Hồ Chí Minh", "ĐH Hoa Sen"),
    Candidate("Vo Quoc Viet", "viet.vo@example.com", "0901 234 515", "Hà Nội", "ĐH Công nghiệp Hà Nội"),
    Candidate("Nguyen Van A", "nguyenvana1998@example.com", "0901 234 516", "TP. Hồ Chí Minh", "Cao đẳng nghề CNTT"),
    Candidate("Tran Thi B", "tranthib.work@example.com", "0901 234 517", "TP. Hồ Chí Minh", "Trung tâm tin học ABC"),
    Candidate("Le Van C", "levanc.cv@example.com", "0901 234 518", "Hà Nội", "ĐH Mở Hà Nội"),
    Candidate("Pham Thi D", "phamthid@example.com", "0901 234 519", "Đà Nẵng", "Cao đẳng Kinh tế Kế hoạch"),
    Candidate("Hoang Van E", "ehoang123@example.com", "0901 234 520", "TP. Hồ Chí Minh", "Tự học online"),
]


def bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def render_jd(index: int, job: JobProfile) -> str:
    stack = ", ".join(job.stack)
    return dedent(
        f"""
        JOB DESCRIPTION #{index:02d} - {job.role}

        Công ty: {job.company}
        Địa điểm: {job.city}
        Cấp bậc: {job.level}
        Kinh nghiệm yêu cầu: {job.years}

        1. Giới thiệu công ty
        {job.company} là công ty công nghệ Việt Nam hoạt động trong lĩnh vực {job.domain}. Đội ngũ sản phẩm đang mở rộng để xây dựng {job.project}, phục vụ khách hàng doanh nghiệp và người dùng cuối tại thị trường Việt Nam. Chúng tôi đề cao ownership, tư duy dữ liệu, chất lượng sản phẩm và khả năng phối hợp liên phòng ban.

        2. Trách nhiệm chính
        {bullet_list(job.responsibilities)}

        3. Yêu cầu công việc
        Tech stack chính: {stack}
        {bullet_list(job.requirements)}

        4. Quyền lợi
        {bullet_list(job.benefits)}

        5. Quy trình tuyển dụng
        - Vòng 1: Trao đổi với HR về kinh nghiệm, định hướng và mức lương kỳ vọng.
        - Vòng 2: Phỏng vấn kỹ thuật/tình huống với Engineering Manager hoặc Hiring Manager.
        - Vòng 3: Bài test ngắn hoặc trao đổi văn hóa đội nhóm nếu cần.
        """
    ).strip() + "\n"


def render_perfect_cv(index: int, candidate: Candidate, job: JobProfile) -> str:
    primary = job.stack[:4]
    secondary = job.stack[4:]
    return dedent(
        f"""
        CV #{index:02d} - PERFECT MATCH

        {candidate.name}
        {job.role} | {candidate.city}
        Email: {candidate.email} | Điện thoại: {candidate.phone}
        LinkedIn: linkedin.com/in/{candidate.name.lower().replace(" ", "-")} | GitHub/Portfolio: github.com/{candidate.name.lower().split()[0]}{index:02d}

        TÓM TẮT
        {job.role} có {job.years} kinh nghiệm trong lĩnh vực {job.domain}. Thành thạo {", ".join(primary)} và có kinh nghiệm production với {", ".join(secondary)}. Mạnh về ownership, tối ưu hiệu năng, đo lường bằng số liệu và phối hợp chặt với Product/QA/Business để giao sản phẩm đúng hạn.

        KỸ NĂNG CHÍNH
        - Tech stack khớp JD: {", ".join(job.stack)}
        - Quy trình: Agile/Scrum, code review, CI/CD, viết tài liệu kỹ thuật, incident/post-release review.
        - Công cụ: Jira, Confluence, Git, Docker, monitoring dashboard, test automation tùy dự án.

        KINH NGHIỆM LÀM VIỆC
        Senior/Middle {job.role} - {job.company} style project | 2022 - nay
        - Dẫn dắt triển khai {job.project}, trực tiếp phụ trách các hạng mục liên quan đến {", ".join(primary)}.
        - Tối ưu luồng xử lý chính, giảm 40% latency trung bình và giảm 28% lỗi production sau 3 tháng.
        - Thiết kế lại module quan trọng, tăng 35% throughput trong giờ cao điểm và cải thiện SLA từ 97,8% lên 99,5%.
        - Xây dựng bộ test và checklist release, giảm 45% bug leakage sang môi trường staging/production.
        - Phối hợp với Product Owner, QA và stakeholder để chuyển yêu cầu kinh doanh thành user story rõ acceptance criteria.

        {job.role} - Saigon Digital Product Studio | 2020 - 2022
        - Phát triển và bảo trì sản phẩm B2B có hơn 80.000 người dùng hoạt động hằng tháng.
        - Chuẩn hóa coding convention, review trung bình 12 pull request/tuần và mentor 3 thành viên junior.
        - Tự động hóa báo cáo kỹ thuật, tiết kiệm khoảng 8 giờ vận hành mỗi tuần cho team.

        DỰ ÁN TIÊU BIỂU
        {job.project.title()}
        - Vai trò: Owner kỹ thuật cho module lõi.
        - Công nghệ: {", ".join(job.stack)}
        - Kết quả: release đúng kế hoạch, cải thiện conversion/hiệu năng đo được và nhận phản hồi tích cực từ người dùng nội bộ.

        HỌC VẤN
        {candidate.school} - Cử nhân Công nghệ thông tin

        CHỨNG CHỈ
        - Professional Scrum Master I
        - AWS Cloud Practitioner hoặc chứng chỉ kỹ thuật tương đương theo định hướng dự án
        """
    ).strip() + "\n"


def render_average_cv(index: int, candidate: Candidate, job: JobProfile) -> str:
    listed_stack = job.stack[:3] + ["Git", "Agile"]
    missing_keywords = job.stack[3:]
    return dedent(
        f"""
        CV #{index:02d} - AVERAGE MATCH

        {candidate.name}
        Ứng tuyển: {job.role}
        Email: {candidate.email} | SĐT: {candidate.phone} | Địa chỉ: {candidate.city}

        MỤC TIÊU NGHỀ NGHIỆP
        Mong muốn làm việc trong môi trường công nghệ chuyên nghiệp, được học hỏi thêm và đóng góp cho sản phẩm của công ty. Tôi có kinh nghiệm tham gia nhiều dự án phần mềm và có khả năng phối hợp với team để hoàn thành công việc.

        KỸ NĂNG
        - Công nghệ đã dùng: {", ".join(listed_stack)}
        - Có biết về quy trình Agile/Scrum, Jira, Git và làm việc nhóm.
        - Có khả năng đọc tài liệu tiếng Anh ở mức khá.

        KINH NGHIỆM LÀM VIỆC
        {job.role} - Công ty TNHH Phần mềm Sao Việt | 2021 - nay
        - Làm việc với team để phát triển tính năng mới cho hệ thống khách hàng.
        - Sửa bug, cập nhật giao diện/chức năng theo yêu cầu từ quản lý dự án.
        - Tham gia họp sprint, báo cáo tiến độ và hỗ trợ kiểm tra lỗi khi release.
        - Có làm việc với {", ".join(job.stack[:2])}, tuy nhiên chưa tham gia nhiều vào phần kiến trúc tổng thể.
        - Viết tài liệu ngắn cho một số màn hình và hỗ trợ thành viên mới khi cần.

        Nhân viên phát triển phần mềm - Công ty ABC Technology | 2019 - 2021
        - Tham gia bảo trì hệ thống nội bộ cho khách hàng trong nước.
        - Code tính năng theo task được giao, phối hợp QA để fix bug.
        - Hỗ trợ deploy bản build lên môi trường test.

        DỰ ÁN
        Dự án quản lý nội bộ
        - Mô tả: hệ thống giúp quản lý thông tin và quy trình của doanh nghiệp.
        - Vai trò: thành viên phát triển.
        - Công nghệ: {", ".join(listed_stack)}
        - Kết quả: hoàn thành các task được giao, sản phẩm được đưa vào sử dụng.

        HỌC VẤN
        {candidate.school} - Công nghệ thông tin

        GHI CHÚ CHO EVAL
        CV này cố ý thiếu hoặc nhắc rất ít các từ khóa quan trọng sau của JD: {", ".join(missing_keywords)}. Mô tả công việc có kinh nghiệm thật nhưng thiếu số liệu định lượng và impact rõ ràng.
        """
    ).strip() + "\n"


def render_terrible_cv(index: int, candidate: Candidate, job: JobProfile) -> str:
    unrelated_jobs = [
        "nhân viên bán hàng điện máy",
        "cộng tác viên nhập liệu",
        "quản lý fanpage bán mỹ phẩm",
        "phụ trách kho bán lẻ",
        "nhân viên tư vấn khóa học",
    ]
    unrelated = unrelated_jobs[(index - 16) % len(unrelated_jobs)]
    return dedent(
        f"""
        CV #{index:02d} - TERRIBLE MATCH / ATS FAIL

        ho va ten: {candidate.name}
        sdt {candidate.phone}     mail: {candidate.email}
        muon ung tuyen viec IT luong cao, vi thay cong ty dang tuyen {job.role}

        THONG TIN CA NHAN
        Sinh nam 1998. Cao 1m70. Thich xem youtube, nghe nhac, cafe voi ban be. Co laptop ca nhan. Co the di lam ngay neu luong tot. Mong cong ty dao tao tu dau vi em rat cham chi.

        KINH NGHIEM
        2023-2025: {unrelated}
        Lam nhieu viec linh tinh, noi chung la cham soc khach hang, nhap so lieu, gui tin nhan, goi dien, dang bai, lam bao cao bang excel khi sep yeu cau. Cong viec kha ban nen em quen ap luc.

        2021-2023: lam freelance
        Co hoc qua HTML tren mang, co sua may tinh cho nguoi quen, cai win, cai phan mem, lam slide. Da tung nghe ve {job.stack[0]} nhung chua lam du an that. Biet dung Facebook, Canva, Excel co ban.

        KY NANG
        - Cham chi, that tha, hoa dong, vui ve, co trach nhiem.
        - Tin hoc van phong, go van ban nhanh, tim kiem google.
        - Biet mot chut code nhung khong nho ro.
        - Tieng Anh trung binh, giao tiep hoi kho.

        DU AN
        Chua co du an cong ty. Co lam bai tap ca nhan nhung mat file. Co y tuong lam app ban hang nhung chua hoan thanh.

        HOC VAN
        {candidate.school}
        Hoc nhieu khoa online nhung khong co chung chi.

        MUC TIEU
        Em mong muon cong ty cho co hoi. Em se co gang hoc hoi tat ca cong nghe nhu {", ".join(job.stack)} sau khi vao lam. Mong HR xem xet vi em rat can viec.

        Ghi chu: CV nay co format kem, khong co metric, khong co thanh tich, nhieu filler, kinh nghiem khong lien quan va gan nhu khong dap ung JD.
        """
    ).strip() + "\n"


def quality_for_index(index: int) -> str:
    if index <= 5:
        return "perfect"
    if index <= 15:
        return "average"
    return "terrible"


def render_cv(index: int, candidate: Candidate, job: JobProfile) -> str:
    quality = quality_for_index(index)
    if quality == "perfect":
        return render_perfect_cv(index, candidate, job)
    if quality == "average":
        return render_average_cv(index, candidate, job)
    return render_terrible_cv(index, candidate, job)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def generate_dataset(root: Path | None = None) -> None:
    base_dir = (root or project_root()) / "dataset" / "golden"
    jd_dir = base_dir / "jds"
    cv_dir = base_dir / "cvs"
    jd_dir.mkdir(parents=True, exist_ok=True)
    cv_dir.mkdir(parents=True, exist_ok=True)

    for index, (job, candidate) in enumerate(zip(JOBS, CANDIDATES, strict=True), start=1):
        (jd_dir / f"jd_{index:02d}.txt").write_text(render_jd(index, job), encoding="utf-8")
        (cv_dir / f"cv_{index:02d}.txt").write_text(render_cv(index, candidate, job), encoding="utf-8")

    print(f"Generated {len(JOBS)} JDs and {len(CANDIDATES)} CVs in {base_dir}")
    print("Quality distribution: cv_01-cv_05=perfect, cv_06-cv_15=average, cv_16-cv_20=terrible")


if __name__ == "__main__":
    generate_dataset()
