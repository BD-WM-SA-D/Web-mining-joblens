<!-- ĐỒNG BỘ TỪ joblens/docs/project-plan/templates/AGENTS.md + agents/web-mining.md – sửa ở đó trước, không sửa tại đây -->
# Hướng dẫn cho AI agent

Áp dụng cho mọi AI agent làm việc trong repo này: Codex, Claude Code, Cursor, Copilot… Người dùng nói khác thì làm theo người dùng, nhưng phải nhắc lại quy tắc bị bỏ qua.

## Bối cảnh

JobLens VN là đồ án liên môn học kỳ 20261. Một hệ thống được chia thành 4 repo trong org `BD-WM-SA-D`:

| Repo | Vai trò |
|---|---|
| `joblens` | Dùng chung: schema Kafka, contract bảng, fixtures, glossary, phiên bản, tài liệu kế hoạch |
| `Big-Data-Storage-and-Processing-joblens` | Môn IT4931 Big Data: Kafka, Spark, Iceberg, dbt, GX, Airflow, Trino, K8s |
| `Web-mining-joblens` | Môn Web Mining: crawler, dedup, IE, ABSA, IR, RecSys, đồ thị |
| `PTTKHT-joblens` | Môn IT3120 SA&D: cổng JobLens (API + UI), UML, yêu cầu, kiểm thử chấp nhận |

Mỗi repo là bài nộp của **một** môn. Mỗi artifact chỉ có **một** môn chấm chính. Code đặt sai repo làm hỏng tính độc lập của bài nộp.

Tài liệu gốc:
- File nào lên repo nào: `joblens/docs/repo-routing.md`.
- Quy tắc làm việc: `joblens/docs/project-plan/09-quy-tac-lam-viec-chung.md`.
- Ma trận sở hữu: `joblens/docs/project-plan/07-quy-tac-phan-tach-mon.md`.

## Ngôn ngữ

- Tài liệu, comment, mô tả commit/PR, nhật ký viết bằng **tiếng Việt có dấu**.
- Tên biến, hàm, file, cột, topic viết bằng tiếng Anh (`snake_case` cho Python/SQL).

## Mỗi khi tạo hoặc sửa file (bắt buộc)

1. **Xác định repo đích** bằng bảng "Tra nhanh" ở đầu `joblens/docs/repo-routing.md` (chi tiết ở mục A–F) và mục "Phạm vi repo này" ở cuối file này. Nếu file không thuộc repo đang mở thì **không tạo**: báo người dùng repo đúng và phần việc cần làm ở đó. Nếu bảng không có loại file này thì hỏi người dùng.
2. **Tôn trọng dòng đánh dấu.** File có dòng đầu `ĐỒNG BỘ TỪ …` hoặc `SINH TỪ …` thì **không sửa tại chỗ**. Chỉ ra bản gốc cần sửa (thường ở `joblens/docs/project-plan/templates/` hoặc `joblens/schemas/`).
3. **Thêm dòng đánh dấu** khi tạo file mục C (`ĐỒNG BỘ TỪ`), mục E (`LIÊN QUAN: <repo>/<file>`) hoặc file sinh từ schema (`SINH TỪ … @ vX.Y.Z`).
4. **Đánh dấu việc dùng AI.** Khi commit, thêm dòng `AI: <công cụ> – <phần nào>` cuối commit message.
   - Việc thường ngày không cần ghi `NHAT-KY.md`.
   - Chỉ ghi nhật ký (vài dòng, mục mới trên cùng) khi đổi hợp đồng hoặc file cấu hình chung, khi ghép hệ thống hay chốt số liệu.
   - Nếu thay đổi chạm hợp đồng ở `joblens`, nhắc người dùng **nhắn nhóm chat**.
   - **Không tự điền tên người kiểm tra**, để `<người kiểm tra>`.

## Không bao giờ làm

- **Commit những thứ cấm:**
  - Bí mật: `.env`, key, token, kubeconfig.
  - Dữ liệu crawl, HTML thô, dump Kafka, warehouse Iceberg.
  - Tập nhãn, file model (`*.pt`, `*.bin`, `*.safetensors`, `*.onnx`, `*.pkl`).
  - Dữ liệu cá nhân (tên, email, SĐT, CV).
  - Slide hay tài liệu của giảng viên.
  - Output notebook.
- **Lách bộ chặn:**
  - Không dùng `--no-verify`.
  - Không sửa `.gitignore` hay `.pre-commit-config.yaml` để cho file cấm đi qua.
- **Thao tác git và GitHub nguy hiểm:**
  - Không push khi người dùng chưa yêu cầu.
  - Không force-push, không viết lại lịch sử đã push.
  - Không merge PR thay người.
  - Không tạo hay xóa repo, không đổi cài đặt org/repo.
- **Thu thập dữ liệu sai quy tắc:**
  - Không chạy crawler thật khi chưa được yêu cầu rõ.
  - Không lách robots.txt hay chống bot, không thêm đăng nhập vào trang nguồn.
  - Không vượt 1 request/giây/domain, không chạm đường dẫn CV.
- **Tải nặng vào repo:** không tải dataset lớn hay model vào repo, không gửi dữ liệu crawl cho dịch vụ bên ngoài.
- **Ghi vào bảng hay topic của repo khác** (quy tắc 2): cần dữ liệu thì đọc, hoặc mở issue `cross-repo`.
- **Bịa thông tin:**
  - Tên thành viên, MSSV, ngày giảng viên đồng ý, mã môn.
  - Số liệu thí nghiệm, benchmark, metric.
  - Chỗ chưa biết thì giữ dạng `<...>`.
- **Lẫn báo cáo giữa các môn:** không viết nội dung báo cáo của môn khác vào repo này, không chép nguyên văn đoạn văn giữa các báo cáo (R3), không dán cùng một hình vào hai báo cáo (R5).
- **Dùng `latest`:** không dùng tag `latest` cho image hay phiên bản thư viện. Phiên bản pin nằm ở `joblens/versions.md`.

## Đổi schema hay hợp đồng dữ liệu

- Sửa ở `joblens` **trước**, rồi mới sửa code ở repo môn. Không tạo bản sao schema trong repo môn.
- Thêm trường hoặc cột không bắt buộc thì làm được ngay. **Đổi tên hoặc xóa** thì báo người dùng: phải hỏi nhóm đang dùng hợp đồng đó trước.
- Đang làm ở repo môn mà thấy cần đổi hợp đồng thì nói rõ cần đổi gì ở `joblens`, không tự chế cách lách.

## Git

- Trong repo môn, nhóm được push thẳng `main`. Agent chỉ commit hoặc push khi người dùng yêu cầu.
- Commit theo Conventional Commits, ví dụ `feat(crawler): thêm adapter ITviec`.
- Ở repo `joblens` nên dùng nhánh và PR để CI chạy. Việc cần repo khác làm thì gợi ý mở issue `cross-repo` ở repo đó.

## Trước khi báo xong

- Chạy `pre-commit run --all-files` và test của repo (xem "Phạm vi repo này"). Báo lệnh đã chạy và kết quả thật.
- Bước nào không chạy được thì nói rõ là chưa kiểm tra, không viết "đã xong".
- Tóm tắt: file đã tạo, sửa, xóa; mục nhật ký đã ghi; việc còn lại ở repo khác (nếu có).

## Hỏi người dùng thay vì đoán khi

- Không xác định được file thuộc repo nào.
- Đổi tên hoặc xóa trường, cột, bảng, topic trong hợp đồng.
- Xóa file hay thư mục có sẵn.
- Yêu cầu mâu thuẫn với quy tắc ở trên.

## Phạm vi repo này: `Web-mining-joblens` (Web Mining)

Câu hỏi môn chấm: *tri thức gì* được khai phá từ dữ liệu web, bằng kỹ thuật nào, và *tốt đến đâu*.

**Thuộc về đây:**
- `crawler/`: spider, parser, adapter từng trang, producer ghi vào Kafka, thuật toán dedup (WM1).
- `ie/`, `absa/`, `retrieval/`, `recsys/`, `graph/`: mô hình WM2–WM6, từ điển alias kỹ năng.
- `annotation/`: guideline gán nhãn và thống kê κ (không có dữ liệu nhãn).
- `experiments/`: notebook đã xóa output, cùng bảng kết quả.
- `images/`: Dockerfile cho job mô hình. `models.yaml`: danh mục model.
- `docs/` (nguồn báo cáo Web Mining) và `docs/adr/`.

**Không thuộc về đây:**
- Helm, manifest K8s, khai báo topic, dbt, GX, DAG Airflow → `Big-Data-Storage-and-Processing-joblens`.
- UML, đặc tả UC, API/UI → `PTTKHT-joblens`.
- Schema message hay contract bảng (kể cả `silver.job_skills`) → `joblens`.

**Quy tắc riêng:**
- **Crawl lịch sự:** tôn trọng robots.txt, ≤ 1 request/giây/domain, User-Agent ghi rõ mục đích học tập. Không crawl trang cần đăng nhập, không chạm đường dẫn CV của TopCV, không lách chống bot. Không chạy crawler thật nếu người dùng chưa yêu cầu rõ; khi thử thì dùng fixtures hoặc HTML mẫu tự soạn.
- **PII:** không lưu tên, email, SĐT người đăng tin hay người review; lọc ngay trong parser.
- **Không commit:** HTML thô, dữ liệu crawl, file export nhãn, file model, cache Hugging Face. Những thứ này nằm ở `s3://joblens/…`.
- **Train xong:** cập nhật `models.yaml` (version, đường dẫn S3, metric, snapshot dữ liệu train). Image gắn tag `version-gitsha`, không dùng `latest`.
- **Ghi nguồn số liệu:** mỗi thí nghiệm ghi snapshot hay tag Iceberg đã dùng và báo cáo cả baseline. Nhãn yếu (tag nhà tuyển dụng, cột kỹ năng LLM của VietJobs) không được dùng làm tập test.
- Repo này ghi topic `jobs.raw.*`, `reviews.raw.*`, `dlq.parse_errors.v1` và bảng `silver.job_skills`, `silver.job_dedup`, `silver.review_aspects`, `silver.reco_scores` (qua image do Airflow của repo Big Data chạy). Không ghi bảng khác.
- Mỗi mô hình giao dưới dạng image theo hợp đồng chạy trong ADR 0001 D3 (`--input-table … --output-table … --run-id …`), kèm image stub. Dịch vụ tìm kiếm (nếu làm WM4) theo `schemas/api/search.v1.yaml`.
- Không chuẩn hóa lương/địa điểm/cấp bậc cho silver (việc của Big Data – D2); `job_uid` luôn tính bằng `joblens_contracts.job_uid()`.
- Phải chạy được một mình: train và đánh giá trên VietJobs + fixtures, không cần Kafka hay K8s.

**Lệnh kiểm tra:** `pre-commit run --all-files`. Khi đã có code thì thêm `pytest -q`.
