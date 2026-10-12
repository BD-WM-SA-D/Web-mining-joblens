# Hướng dẫn gán nhãn kỹ năng (WM2) – bản 0.2

Mục đích: tạo tập vàng (người gán) để đánh giá mô hình trích kỹ năng. Mỗi câu lấy từ mô tả hoặc yêu cầu của một tin tuyển dụng IT. Người gán bôi đen **từng kỹ năng cứng** trong câu, gán nhãn `SKILL`. Sau đó script đổi sang nhãn BIO (`B-SKILL`, `I-SKILL`, `O`) để tính F1 bằng seqeval (strict).

Tập này **chỉ dùng làm dev/test**. Không trộn với nhãn yếu (tag của nhà tuyển dụng, từ điển).

## 1. Thế nào là SKILL

Gán nhãn khi cụm từ là **một kỹ năng cứng cụ thể**, có thể học, kiểm tra được và dùng được để so khớp ứng viên với tin:

| Nhóm | Ví dụ |
|---|---|
| Ngôn ngữ lập trình, truy vấn | Python, Java, C#, SQL, PL/SQL, Bash |
| Framework, thư viện | Spring Boot, ReactJS, Django, TensorFlow, jQuery |
| Cơ sở dữ liệu, hàng đợi | PostgreSQL, MongoDB, Redis, Kafka, RabbitMQ |
| Nền tảng, hạ tầng, cloud | AWS, Azure, Docker, Kubernetes, Linux, Nginx |
| Công cụ, phần mềm | Git, Jira, Figma, Photoshop, AutoCAD, Excel, Power BI |
| Phương pháp, quy trình kỹ thuật | Agile, Scrum, CI/CD, TDD, kiểm thử tự động |
| Khái niệm, kiến thức kỹ thuật | OOP, lập trình hướng đối tượng, microservices, RESTful API, cấu trúc dữ liệu và giải thuật, machine learning, TCP/IP |
| Nghiệp vụ kỹ thuật cụ thể | phân tích nghiệp vụ, viết test case, thiết kế UI/UX, ETL |

## 2. Không gán

| Không gán | Ví dụ |
|---|---|
| Kỹ năng mềm, tính cách | kỹ năng giao tiếp, làm việc nhóm, chịu áp lực, cẩn thận |
| Ngoại ngữ | tiếng Anh, TOEIC 600, tiếng Nhật N2 (VietJobs có cột riêng) |
| Bằng cấp, chuyên ngành | tốt nghiệp đại học CNTT, chuyên ngành khoa học máy tính |
| Số năm kinh nghiệm, cấp bậc | 2 năm kinh nghiệm, senior, leader |
| Chức danh | lập trình viên Java, kỹ sư DevOps → chỉ gán `Java`; `DevOps` đứng một mình như phương pháp thì gán |
| Từ quá chung | lập trình, phần mềm, công nghệ, hệ thống, máy tính, tin học |
| Lĩnh vực sản phẩm | ngân hàng, thương mại điện tử, fintech, game (trừ khi là kỹ năng: "phát triển game Unity" → `Unity`) |
| Chứng chỉ | PMP, PSM, AWS Certified, IELTS (giống bằng cấp) |
| Sản phẩm đem bán, không phải thứ người làm phải dùng | "tư vấn bán gói Domain/Hosting/Server", "bán hệ thống chấm công AI Camera" → không gán |

**Mẹo:** tự hỏi "ứng viên có cần **biết dùng / biết làm** cái này để làm việc không?". Có → gán. Chỉ là thứ được nhắc tới, đem bán, hay là bằng cấp → không gán.

## 3. Ranh giới span

1. **Lấy cụm ngắn nhất vẫn đủ nghĩa.** "kinh nghiệm làm việc với Spring Boot" → `Spring Boot`. "thành thạo Adobe Photoshop" → `Adobe Photoshop` (giữ tên hãng nếu có trong câu).
2. **Không lấy số phiên bản**, trừ khi là một phần của tên: "Java 8" → `Java`; `HTML5`, `CSS3`, `Python 3` → lấy `HTML5`, `CSS3`, `Python`.
3. **Dấu "/" hoặc "," ngăn hai kỹ năng thì tách thành hai span**: "ReactJS/VueJS" → `ReactJS`, `VueJS`. Ngoại lệ là tên chuẩn có sẵn dấu "/": `CI/CD`, `TCP/IP`, `PL/SQL`, `UI/UX`, `C/C++` (gán một span vì nhà tuyển dụng dùng như một tên).
4. **Liệt kê trong ngoặc**: "tin học văn phòng (Word, Excel)" → `Word`, `Excel`; không gán "tin học văn phòng" khi đã có tên công cụ cụ thể. Đứng một mình thì gán `tin học văn phòng`.
5. **Kỹ năng ghép với từ chung**: "cơ sở dữ liệu MySQL" → `MySQL`. "thiết kế cơ sở dữ liệu" → gán cả cụm (là nghiệp vụ kỹ thuật).
6. **Viết tắt mơ hồ**: "AI" trong tin thiết kế đồ họa là Adobe Illustrator, trong tin dữ liệu là trí tuệ nhân tạo. Cả hai đều gán `SKILL`; người chuẩn hóa sẽ xử lý sau.
7. **Không bỏ dấu câu vào span**: "Docker," → `Docker`.
8. **Tiếng Việt và tiếng Anh như nhau**: "kiểm thử tự động" và "automation testing" đều gán.
9. **Tên sản phẩm, thiết bị kỹ thuật cụ thể** mà người làm phải vận hành thì gán: `Veeam Backup`, `HPE StoreOnce`, `SAN`. Tên hãng đứng một mình ("server HPE/DELL") thì không gán.
10. **Chữ "..." hoặc "v.v." cuối danh sách** không nằm trong span: "Photoshop, AI, Corel..." → `Photoshop`, `AI`, `Corel`.

## 4. Câu khó

- Không chắc thì gán theo quy tắc gần nhất, tick ô **"khó / cần bàn"**, ghi một dòng lý do.
- Mỗi tuần gom các câu bị tick, thống nhất cách gán, rồi bổ sung ví dụ vào guideline này (tăng số phiên bản).

## 5. Ví dụ

| Câu | Span SKILL |
|---|---|
| Có kinh nghiệm 2 năm lập trình Java, Spring Boot. | `Java`, `Spring Boot` |
| Thành thạo ReactJS/NextJS, hiểu biết về RESTful API. | `ReactJS`, `NextJS`, `RESTful API` |
| Sử dụng tốt Photoshop, AI, Figma. | `Photoshop`, `AI`, `Figma` |
| Kỹ năng giao tiếp tốt, tiếng Anh giao tiếp. | (không có) |
| Tốt nghiệp chuyên ngành CNTT hoặc tương đương. | (không có) |
| Triển khai hệ thống trên AWS, quản lý CI/CD bằng Jenkins. | `AWS`, `CI/CD`, `Jenkins` |
| Hiểu biết về cấu trúc dữ liệu và giải thuật, OOP. | `cấu trúc dữ liệu và giải thuật`, `OOP` |
| Nam/nữ 24–40 tuổi. | (không có) |

### Ví dụ dạng câu gặp trong đợt 1 (đã viết lại)

| Câu | Span SKILL | Vì sao |
|---|---|---|
| Có kinh nghiệm làm việc với SVN/GIT. | `SVN`, `GIT` | "/" ngăn hai công cụ |
| Thành thạo HTML5, CSS3, JS, Jquery. | `HTML5`, `CSS3`, `JS`, `Jquery` | gán đúng chữ trong câu, không sửa chính tả |
| Có kiến thức tốt về cơ sở dữ liệu quan hệ (thiết kế, sử dụng). | `cơ sở dữ liệu quan hệ` | khái niệm kỹ thuật |
| Thành thạo thiết kế phần mềm và cơ sở dữ liệu (PostgreSQL, MongoDB, Kafka). | `thiết kế phần mềm`, `PostgreSQL`, `MongoDB`, `Kafka` | "cơ sở dữ liệu" đã có tên cụ thể trong ngoặc → không gán |
| Sử dụng thành thạo tin học văn phòng (MS Word, MS Excel, Visio). | `MS Word`, `MS Excel`, `Visio` | quy tắc 4 |
| Có kinh nghiệm triển khai ảo hóa (VMware/HyperV/KVM). | `ảo hóa`, `VMware`, `HyperV`, `KVM` | "ảo hóa" là nghiệp vụ kỹ thuật cụ thể |
| Thực hiện review code và tuân thủ quy trình CI/CD. | `review code`, `CI/CD` | |
| Phối hợp thiết kế luồng dữ liệu (ETL). | `thiết kế luồng dữ liệu`, `ETL` | |
| Tối ưu database (indexing, partitioning, sharding). | `indexing`, `partitioning`, `sharding` | "database" đứng chung chung → không gán |
| Có kiến thức về kiến trúc RAG. | `RAG` | |
| Ưu tiên biết ứng dụng AI trong công việc. | `AI` | người làm phải biết dùng |
| Tư vấn bán hệ thống chấm công bằng AI Camera. | (không có) | sản phẩm đem bán |
| 3 năm kinh nghiệm vị trí BA, dự án fintech (Banking). | (không có) | chức danh, lĩnh vực |
| Có chứng chỉ PMP, PSM là lợi thế. | (không có) | chứng chỉ |
| Tiếng Nhật giao tiếp, tối thiểu JLPT N3. | (không có) | ngoại ngữ |
| Có kinh nghiệm trong việc tích hợp các hệ thống. | (không có) | quá chung |
| Có khả năng vẽ tay hoặc vẽ trên tablet. | `vẽ tay` | kỹ năng nghề cụ thể (tin thiết kế) |
| Biết chụp hình sản phẩm, quay dựng video ngắn cho Tiktok bằng Capcut. | `chụp hình`, `quay dựng video`, `Capcut` | bỏ từ bổ nghĩa ("sản phẩm", "ngắn"); Tiktok chỉ là nơi đăng → không gán |
| Chạy quảng cáo Tiktok Ads, Facebook Ads. | `Tiktok Ads`, `Facebook Ads` | công cụ người làm phải dùng |
| Phối hợp với bộ phận Idea và Marketing để đảm bảo thiết kế phù hợp concept. | (không có) | tên phòng ban; "thiết kế" quá chung |

| Liên hệ khách hàng qua điện thoại, tư vấn, báo giá, đặt lịch hẹn gặp khách hàng. | (không có) | nhiệm vụ hằng ngày, không cần học chuyên môn |

**Nhiệm vụ khác kỹ năng:** động từ chỉ việc làm (liên hệ, tư vấn, hỗ trợ, phối hợp, báo giá, chăm sóc khách hàng, theo dõi, báo cáo) không tự động là kỹ năng. Chỉ gán khi việc đó cần học chuyên môn hoặc gắn với công cụ cụ thể ("edit video", "tư vấn qua CRM" → `CRM`). Phép thử: "Bạn biết ___ không?" nghe lạ (ai cũng làm được) → không gán.

**Chuỗi bước quy trình:** câu liệt kê các bước làm việc bằng chuỗi động từ ("Lên ý tưởng, phác thảo, đề xuất thiết kế…", "Tiếp nhận, phân tích, xử lý yêu cầu…") → không gán các bước. Trong chuỗi có tên công cụ/phương pháp thì chỉ gán tên đó ("phác thảo, dựng hình trên Blender" → `Blender`). "phác thảo" chỉ gán khi là kỹ năng vẽ ("có khả năng vẽ phác thảo bằng tay" → `vẽ phác thảo`).

**Kỹ năng mềm có từ trông kỹ thuật:** "khả năng phân tích, tổng hợp thông tin, giải quyết vấn đề" → không gán. "phân tích dữ liệu", "phân tích nghiệp vụ" là tên nghề cụ thể → gán.

**Mạng xã hội, nền tảng:** chỉ là nơi đăng hay đối tượng ("video cho Tiktok", "fanpage Facebook") → không gán. Là công cụ phải vận hành ("Tiktok Ads", "Facebook Business Manager", "Shopee Seller Center") → gán.

## 6. Quy trình

1. Chuẩn bị dữ liệu (chạy một lần, dữ liệu nằm trong `data/`, không commit):
   ```
   uv run python -m ie.vietjobs
   uv run python -m annotation.sample_skill_batch --sentences 1500
   ```
2. Chạy Label Studio cục bộ (chạy riêng bằng uvx, không cài vào môi trường của repo; lần đầu tải vài trăm MB):
   - `uvx label-studio start` → trình duyệt mở `http://localhost:8080`, đăng ký tài khoản cục bộ (chỉ lưu trên máy).
   - **Create Project** → tab *Labeling Setup* → *Custom template* → xóa nội dung mẫu, dán nội dung `annotation/label_studio_skill.xml` → *Save*.
   - Tab *Data Import* → chọn `data/annotation/skill_batch1.labelstudio.json`.
   - Thao tác gán: bấm **Label All Tasks** → nhấn phím `s` (chọn nhãn SKILL) → bôi đen cụm từ → lặp lại cho từng kỹ năng → **Submit** (Ctrl+Enter). Câu không có kỹ năng: Submit luôn. Gán sai: bấm vào span → Delete.
   - Người thứ hai (đo κ): lọc cột `double = true`, gán trên một tài khoản khác, không xem nhãn của người kia.
3. **Gán thử 100 câu** đầu, xem lại guideline, rồi gán tiếp.
4. **Đo κ:** các câu có `double = true` (khoảng 10%) do người thứ hai gán độc lập. Tính Cohen's κ trên nhãn BIO mức token. Mục tiêu κ ≥ 0,7; thấp hơn thì bàn lại các câu lệch và sửa guideline.
5. Export JSON từ Label Studio vào `data/annotation/` (không commit). Chỉ ghi số liệu (số câu, số span, κ) vào `experiments/results.md`.
6. **Tập test `skill_test1`** (1.000 câu từ 125 tin TopCV, snapshot `topcv_v1`): tạo **project Label Studio riêng**, không trộn với đợt VietJobs `skill_batch1` (dev set). Tạo lại bằng:
   ```
   uv run python -m crawler.snapshot --source topcv --name topcv_v1
   uv run python -m annotation.sample_skill_batch --snapshot data/crawl/topcv/topcv_v1.parquet --batch skill_test1 --sentences 1000 --seed 20261012 --max-per-posting 8
   ```
   Câu tiếng Anh gán như tiếng Việt (quy tắc 8); dòng tiêu đề kiểu "Your Recruitment Journey" thì Submit luôn.

## Lịch sử

| Bản | Ngày | Thay đổi |
|---|---|---|
| 0.1 | 2026-10-07 | Bản đầu |
| 0.2 | 2026-10-11 | Thêm chứng chỉ, sản phẩm đem bán, tên thiết bị; ví dụ từ đợt 1; các bước Label Studio |
