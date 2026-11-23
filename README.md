# Web-mining-joblens

**Mining Vietnamese Job Postings for Skill Demand and Company Reviews**

Dự án thu thập tin tuyển dụng và review công ty công khai từ các nguồn tuyển dụng tại Việt Nam (ví dụ TopCV, ITviec), rồi khai phá văn bản để trả lời ba câu hỏi: kỹ năng nào đang được tuyển nhiều, nhân viên đánh giá một công ty ra sao theo từng khía cạnh, và tin nào phù hợp với bộ kỹ năng của một người.

## Các bài toán

| Bài | Nội dung | Kỹ thuật chính |
|---|---|---|
| T1 | Trích xuất kỹ năng trong mô tả tin, chuẩn hóa về tên chuẩn | PhoBERT, từ điển alias |
| T2 | Gán khía cạnh và cực tính cho từng câu review | Từ điển, hồi quy logistic |
| T3 | Gợi ý tin theo danh sách kỹ năng | TF-IDF, trùng kỹ năng |
| Phân tích cấu trúc | Đồ thị đồng xuất hiện kỹ năng và các nhóm nghề | NPMI, Louvain |

T1 cung cấp kỹ năng cho thống kê nhu cầu, cho đồ thị kỹ năng và cho T3; T2 tạo tóm tắt công ty theo khía cạnh.

## Phương pháp

**Nguyên tắc chung.** Mỗi bài bắt đầu từ một baseline đơn giản, sau đó thêm từng thành phần để đo đóng góp riêng của nó. Mọi so sánh dùng tập kiểm tra do nhóm tự gán nhãn. Nhãn yếu và nhãn do LLM chỉ dùng để huấn luyện, không bao giờ dùng để chấm. Một phương pháp chỉ được coi là tốt hơn khi khoảng tin cậy bootstrap 95% của chênh lệch so với baseline nằm hoàn toàn trên 0.

**T1. Trích xuất kỹ năng**
- *Baseline:* khớp từ điển alias.
- *Phương pháp:* PhoBERT-base-v2 gán nhãn chuỗi với một loại thực thể là kỹ năng, sau đó chuẩn hóa về tên chuẩn bằng từ điển. Điểm khác biệt nằm ở nguồn nhãn huấn luyện, gồm ba mức: nhãn yếu từ tag của nhà tuyển dụng, nhãn yếu có thêm luật và self-training, và nhãn do LLM gán theo guideline. LLM chỉ gán nhãn cho dữ liệu công khai và không chạy khi triển khai.
- *Đánh giá:* precision, recall và F1 thực thể khớp chặt, so các nguồn nhãn trên cùng một tập kiểm tra.

**T2. Khía cạnh và cực tính của review**
- *Baseline:* từ điển cảm xúc. Thêm một luật suy cực tính từ phần của review (điều thích, góp ý) để kiểm tra mô hình có học được gì hơn bố cục của trang hay không.
- *Phương pháp:* khía cạnh lấy từ từ điển; cực tính học bằng hồi quy logistic trên tín hiệu từ điển và TF-IDF.
- *Đánh giá:* F1 của khía cạnh và macro-F1 của cực tính ở mức câu. Kết quả được đối chiếu với điểm sao theo khía cạnh đi kèm review, là tín hiệu độc lập với người gán nhãn.

**T3. Gợi ý tin theo kỹ năng**
- *Baseline:* xếp theo độ phổ biến. Do chưa có log hành vi người dùng nên các phương pháp chính đều dựa trên nội dung.
- *Phương pháp:* trùng kỹ năng có trọng số IDF, độ tương tự TF-IDF, và phương án pha thêm độ phổ biến.
- *Đánh giá:* gộp các tin do mọi phương pháp đề xuất, chấm mù theo thang 0, 1, 2 (người chấm không biết tin do phương pháp nào xếp), rồi tính nDCG@10 và Precision@10.

**Phân tích cấu trúc: đồ thị kỹ năng**
- *Phương pháp:* hai kỹ năng được nối khi cùng xuất hiện trong các tin; chỉ giữ cạnh có NPMI đủ cao, rồi tìm cộng đồng bằng Louvain.
- *Đánh giá:* modularity so với đồ thị ngẫu nhiên giữ nguyên bậc; xem xét định tính các cụm.

## Hệ thống gợi ý việc làm theo kỹ năng

Các thành phần trên là lõi của một bản MVP cho người tìm việc IT. Tin được thu thập định kỳ từ nhiều nguồn tuyển dụng và được trích kỹ năng. Người dùng nhập CV, resume hoặc đoạn tự giới thiệu; hệ thống trích kỹ năng để người dùng sửa, rồi trả về 10 tin phù hợp nhất, mỗi tin kèm phân tích độ phù hợp (kỹ năng đã có, kỹ năng còn thiếu, điểm khớp) và tóm tắt review của công ty theo khía cạnh.

- **Đã có:** spider crawl tiếp được, job theo lô, dịch vụ HTTP với hai điểm vào (trích kỹ năng, gợi ý); kết quả gợi ý đã liệt kê kỹ năng khớp và còn thiếu cho từng tin.
- **Chưa có:** đọc file CV (PDF, Word), giao diện, chạy theo lịch.
- Văn bản hồ sơ chỉ xử lý trong bộ nhớ, không lưu; hồ sơ người dùng chỉ giữ danh sách kỹ năng đã xác nhận.

## Chạy nhanh

Cần Python 3.12 và [uv](https://docs.astral.sh/uv/). Huấn luyện và đánh giá chạy từ file cục bộ, không cần dịch vụ ngoài.

```bash
uv sync                  # cài thư viện
cp .env.example .env     # cấu hình, không commit .env
uv run pytest            # kiểm thử
uv run ruff check .      # kiểm tra mã
```

Dữ liệu crawl, tập nhãn và mô hình nằm trong `data/` (đã gitignore), không có trong repo. Dữ liệu mẫu nhỏ để kiểm thử nằm ở `tests/fixtures/`. Crawler mặc định ghi ra file cục bộ; đặt `JOBLENS_KAFKA_BOOTSTRAP` nếu muốn gửi thêm tới Kafka.

## Dịch vụ HTTP

Hai điểm vào: trích kỹ năng từ văn bản, và gợi ý tin theo danh sách kỹ năng. Mặc định dùng từ điển alias; đặt `JOBLENS_MINING_SKILL_MODEL` trỏ tới thư mục mô hình để dùng PhoBERT trên CPU.

```bash
uv run python -m service.index          # dựng chỉ mục từ snapshot đã crawl
uv run uvicorn service.app:app --port 8091

curl -s -X POST localhost:8091/v1/skills:extract -H 'Content-Type: application/json' \
  -d '{"text": "Yêu cầu 2 năm kinh nghiệm ReactJS, Node.js, MongoDB; biết Docker là lợi thế."}'
curl -s -X POST localhost:8091/v1/recommend -H 'Content-Type: application/json' \
  -d '{"skill_ids": ["joblens:python", "joblens:sql"], "k": 3}'
```

Dịch vụ không lưu và không ghi log văn bản đầu vào. Image Docker dựng từ `images/`.

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `crawler/` | Spider và parser cho từng nguồn tuyển dụng, lọc dữ liệu cá nhân |
| `ie/` | T1: từ điển alias, nhãn huấn luyện, huấn luyện và đánh giá PhoBERT |
| `absa/` | T2: khía cạnh và cực tính của review |
| `recsys/` | T3: baseline, phiếu chấm tay, chỉ số |
| `graph/` | Đồ thị đồng xuất hiện kỹ năng |
| `service/` | Dịch vụ HTTP |
| `batch/` | Job chạy theo lô |
| `annotation/` | Guideline gán nhãn, công cụ lấy mẫu và tính κ (không chứa nhãn) |
| `experiments/` | Mã thí nghiệm và kiểm định thống kê; `archive/` giữ mã các thí nghiệm đã thử và không dùng |
| `common/` | Hàm dùng chung |
| `images/` | Dockerfile |
| `docs/` | Phương pháp, đánh giá và quyết định thiết kế |
| `models.yaml` | Danh mục mô hình: phương pháp, chỉ số, tập đánh giá |

## Quy tắc dữ liệu

- Crawler tôn trọng robots.txt, giữ tối đa 1 request mỗi giây mỗi trang, dùng User-Agent nêu mục đích học tập, không vào trang cần đăng nhập hay đường dẫn CV, và dừng trong ngày khi gặp HTTP 429 hoặc 403.
- Chỉ thêm nguồn mới khi điều khoản sử dụng của nguồn đó cho phép truy cập tự động; không lách cơ chế chống bot.
- Repo không chứa dữ liệu crawl, HTML thô, tập nhãn, mô hình hay khóa truy cập. Nội dung tin và review thuộc về trang nguồn, không đăng lại.
- Câu crawl và câu thuộc tập kiểm tra không được gửi tới dịch vụ bên ngoài. Chỉ văn bản từ bộ dữ liệu công khai mới dùng để gán nhãn tự động.
- VietJobs (Pham Dinh et al., LREC 2026, CC BY 4.0) dùng cho huấn luyện, từ điển và baseline; cần trích dẫn khi sử dụng.

## Thành viên

| Họ tên | MSSV |
|---|---|
| Nguyễn Hải Đăng | 20235484 |
| Lê Trung Dũng | 20235489 |
| Lê Nhật Hoàng | 20235498 |
| Lê Hoàng Tùng | 20235572 |
