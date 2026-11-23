# Web-mining-joblens

**Mining Vietnamese Job Postings for Skill Demand and Company Reviews** – đồ án môn Web Mining (IT4868E, học kỳ 20261).

Repo thu thập tin tuyển dụng và review công ty công khai từ TopCV và ITviec, rồi khai phá văn bản trên các trang đó để trả lời ba câu hỏi: kỹ năng nào đang được tuyển nhiều, nhân viên đánh giá một công ty ra sao theo từng khía cạnh, và tin nào hợp với bộ kỹ năng của một người.

## Các bài toán

| Bài | Nội dung | Khía cạnh web mining |
|---|---|---|
| WM1 | Thu thập tin, phát hiện tin đăng trùng trong một trang và giữa hai trang | Thu thập web, near-duplicate detection (MinHash) |
| WM2 | Trích xuất kỹ năng trong mô tả tin, chuẩn hóa về một tên chuẩn | Web content mining, trích xuất thông tin |
| WM3 | Khía cạnh và cảm xúc theo câu trong review công ty | Khai phá quan điểm (ABSA) |
| WM5 | Gợi ý tin theo danh sách kỹ năng của người dùng | Gợi ý, cá nhân hóa (chưa có log hành vi thật, đánh giá bằng chấm tay) |
| WM4, WM6 | Tìm kiếm BM25 và đồ thị đồng xuất hiện kỹ năng | Tùy chọn: truy hồi thông tin, phân tích cấu trúc |

## Phương pháp

Mỗi bài bắt đầu từ một baseline đơn giản rồi thêm từng bước, để thấy bước nào thật sự có ích. Mọi so sánh dùng tập kiểm tra do nhóm tự gán nhãn; nhãn yếu và nhãn do LLM chỉ dùng để huấn luyện. Chênh lệch giữa hai phương pháp chỉ được coi là có ý nghĩa khi khoảng tin cậy bootstrap 95% nằm hoàn toàn trên 0. Số liệu chi tiết và phân tích lỗi nằm ở [`experiments/results.md`](experiments/results.md).

**WM1, phát hiện tin trùng.** Baseline so khớp chính xác tiêu đề và tên công ty. Phương pháp chính cắt văn bản thành các cụm từ chồng nhau (shingling), ước lượng độ giống bằng MinHash và tìm cặp ứng viên bằng LSH. Vì nhiều tin của cùng một công ty dùng chung đoạn giới thiệu và phúc lợi, bước cuối loại các đoạn lặp lại giữa nhiều tin của một công ty trước khi so, và so tiêu đề theo kiểu mềm. Đánh giá bằng precision, recall, F1 trên các cặp tin được gán nhãn.

**WM2, trích xuất kỹ năng.** Baseline là từ điển alias Việt, Anh dò trực tiếp trong câu. Mô hình chính là PhoBERT-base-v2 gán nhãn chuỗi (BIO) với một loại thực thể là kỹ năng. Bài toán chính của bước này là lấy nhãn huấn luyện ở đâu khi nhãn tay ít: thử lần lượt nhãn yếu từ tag kỹ năng của nhà tuyển dụng, nhãn yếu thêm luật và self-training, và nhãn do LLM gán theo đúng guideline của tập kiểm tra. LLM chỉ gán nhãn cho dữ liệu huấn luyện công khai, không chạy khi dùng mô hình. Đánh giá bằng F1 thực thể chặt (seqeval), kỹ năng được chuẩn hóa qua từ điển alias.

**WM3, khai phá quan điểm theo khía cạnh.** Mỗi câu review được gán khía cạnh (lương và phúc lợi, đào tạo, quản lý, cân bằng công việc, văn hóa, văn phòng) và cực tính (tích cực, tiêu cực, trung tính). Baseline là từ điển cảm xúc; thêm một luật dùng phần của review (điều thích, góp ý) để đoán cực tính, vì bố cục trang tiết lộ khá nhiều. Phương pháp chính là mô hình lai: từ điển cho khía cạnh, hồi quy logistic cho cực tính. Kết quả còn được đối chiếu với điểm sao theo từng khía cạnh mà người gán nhãn không tạo ra.

**WM5, gợi ý tin theo kỹ năng.** Chưa có log hành vi người dùng thật nên dùng phương pháp dựa trên nội dung. Baseline là xếp theo độ phổ biến; so với trùng kỹ năng có trọng số IDF (kỹ năng lấy từ WM2), độ tương tự TF-IDF giữa hồ sơ và nội dung tin, và phương án pha thêm độ phổ biến. Đánh giá bằng nDCG@10 và P@10 trên các hồ sơ kỹ năng, kết quả của mọi phương pháp được gộp lại và chấm mù theo thang 0, 1, 2.

**WM4, WM6 (tùy chọn).** Tìm kiếm BM25 mở rộng bằng alias, và đồ thị đồng xuất hiện kỹ năng phân cụm bằng Louvain, xếp hạng bằng PageRank.

## Chạy nhanh

Cần Python 3.12 và [uv](https://docs.astral.sh/uv/). Huấn luyện và đánh giá chạy từ file cục bộ, không cần dịch vụ ngoài.

```bash
uv sync                      # cài thư viện
cp .env.example .env         # cấu hình (không commit .env)
uv run pytest                # kiểm thử
uv run ruff check .          # kiểm tra mã
```

Dữ liệu crawl, tập nhãn và mô hình nằm trong thư mục `data/` (đã gitignore) hoặc ở kho lưu trữ riêng, không có trong repo. Bộ dữ liệu mẫu nhỏ để chạy kiểm thử nằm ở `tests/fixtures/`.

Crawler mặc định ghi bản ghi ra file cục bộ. Khi đặt biến `JOBLENS_KAFKA_BOOTSTRAP`, crawler còn gửi bản ghi tới một hàng đợi Kafka (tùy chọn).

## Dịch vụ khai phá (HTTP API)

Hai điểm vào chính: trích kỹ năng từ văn bản tin và gợi ý tin theo danh sách kỹ năng. Mặc định dùng từ điển alias; đặt biến `JOBLENS_MINING_SKILL_MODEL` trỏ tới thư mục mô hình để dùng PhoBERT.

```bash
uv run python -m service.index                 # dựng chỉ mục tin từ snapshot đã crawl
uv run uvicorn service.app:app --port 8091

curl -s localhost:8091/health
curl -s -X POST localhost:8091/v1/skills:extract -H 'Content-Type: application/json' \
  -d '{"text": "Yêu cầu 2 năm kinh nghiệm ReactJS, Node.js, MongoDB; biết Docker là lợi thế."}'
curl -s -X POST localhost:8091/v1/recommend -H 'Content-Type: application/json' \
  -d '{"skill_ids": ["joblens:python", "joblens:sql"], "k": 3}'
```

- Dịch vụ không lưu và không ghi log văn bản người dùng. Lỗi đầu vào trả về `400`.
- Chế độ PhoBERT chạy trên CPU, đủ nhanh để dùng trực tiếp từ giao diện ứng dụng.
- Image Docker dựng từ thư mục `images/`; có bản đầy đủ (kèm mô hình) và bản nhẹ trả kết quả từ từ điển.
- Kiểm thử API: `uv run pytest tests/test_mining_service.py`.

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `crawler/` | Spider TopCV và ITviec, parser, lọc dữ liệu cá nhân, phát hiện tin trùng |
| `ie/` | WM2: từ điển alias, nhãn yếu và nhãn LLM, huấn luyện và đánh giá PhoBERT |
| `absa/` | WM3: khía cạnh và cực tính trong review |
| `recsys/` | WM5: baseline, phiếu chấm tay, tính chỉ số |
| `retrieval/`, `graph/` | WM4 và WM6 (tùy chọn) |
| `service/` | Dịch vụ HTTP cho trích kỹ năng và gợi ý |
| `batch/` | Job chạy theo lô, ghi kết quả theo định dạng bản ghi cố định |
| `annotation/` | Hướng dẫn gán nhãn, công cụ lấy mẫu và tính κ (không chứa nhãn) |
| `experiments/` | Mã thí nghiệm, bootstrap, `results.md` và nhật ký từng lần chạy; `archive/` giữ mã các thí nghiệm đã thử và không dùng trong kết quả chính thức |
| `common/` | Hàm dùng chung (đọc JSONL) |
| `images/` | Dockerfile |
| `docs/` | Nguồn báo cáo Web Mining và quyết định thiết kế |
| `models.yaml` | Danh mục mô hình đã huấn luyện: phiên bản, chỉ số, tập đánh giá |

## Quy tắc dữ liệu

- Crawler tôn trọng robots.txt, không quá 1 request mỗi giây mỗi trang, dùng User-Agent nêu rõ mục đích học tập, không vào trang cần đăng nhập hay đường dẫn CV, và dừng trong ngày khi gặp HTTP 429 hoặc 403.
- Repo không chứa dữ liệu crawl, HTML thô, tập nhãn, file mô hình hay khóa truy cập. Nội dung tin và review thuộc về trang nguồn, không đăng lại.
- Câu crawl và câu thuộc tập kiểm tra không được gửi tới dịch vụ bên ngoài; chỉ văn bản từ bộ dữ liệu công khai mới được dùng để gán nhãn tự động.
- VietJobs (Pham Dinh et al., LREC 2026, CC BY 4.0) dùng cho huấn luyện, từ điển và baseline; cần trích dẫn khi dùng.

## Thành viên

| Họ tên | MSSV |
|---|---|
| Nguyễn Hải Đăng | 20235484 |
| Lê Trung Dũng | 20235489 |
| Lê Nhật Hoàng | 20235498 |
| Lê Hoàng Tùng | 20235572 |
