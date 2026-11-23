# Web-mining-joblens

**Mining Vietnamese Job Postings for Skill Demand and Company Reviews**

Dự án thu thập tin tuyển dụng và review công ty công khai từ TopCV và ITviec, rồi khai phá văn bản để trả lời ba câu hỏi: kỹ năng nào đang được tuyển nhiều, nhân viên đánh giá một công ty ra sao theo từng khía cạnh, và tin nào phù hợp với bộ kỹ năng của một người.

## Các bài toán

| Bài | Nội dung | Kỹ thuật chính |
|---|---|---|
| WM1 | Phát hiện tin đăng trùng trong một trang và giữa hai trang | Shingling, MinHash, LSH |
| WM2 | Trích xuất kỹ năng trong mô tả tin, chuẩn hóa về tên chuẩn | PhoBERT, từ điển alias |
| WM3 | Gán khía cạnh và cực tính cho từng câu review | Từ điển, hồi quy logistic |
| WM5 | Gợi ý tin theo danh sách kỹ năng | TF-IDF, trùng kỹ năng |
| WM4, WM6 | Tìm kiếm và đồ thị đồng xuất hiện kỹ năng (tùy chọn) | BM25, PageRank, Louvain |

## Phương pháp

Mỗi bài bắt đầu từ một baseline đơn giản rồi thêm từng bước, để thấy bước nào thật sự có ích. Mọi so sánh dùng tập kiểm tra do nhóm tự gán nhãn; nhãn yếu và nhãn do LLM chỉ dùng để huấn luyện. Một phương pháp chỉ được coi là tốt hơn khi khoảng tin cậy bootstrap 95% của chênh lệch nằm hoàn toàn trên 0.

- **WM1.** Baseline so khớp chính xác tiêu đề và công ty. Phương pháp chính so độ giống nội dung bằng MinHash, sau khi loại các đoạn lặp lại giữa nhiều tin của cùng một công ty (giới thiệu, phúc lợi) và so tiêu đề theo kiểu mềm. Đo bằng precision, recall, F1 trên các cặp tin được gán nhãn.
- **WM2.** Baseline là từ điển alias. Mô hình chính là PhoBERT-base-v2 gán nhãn chuỗi, với một loại thực thể là kỹ năng. Điểm đáng chú ý là nguồn nhãn huấn luyện: so sánh nhãn yếu từ tag của nhà tuyển dụng, nhãn yếu có thêm luật và self-training, và nhãn do LLM gán theo đúng guideline của tập kiểm tra. LLM chỉ gán nhãn cho dữ liệu công khai và không chạy khi dùng mô hình. Đo bằng F1 thực thể chặt.
- **WM3.** Baseline là từ điển cảm xúc, kèm một luật suy cực tính từ phần của review (điều thích, góp ý) để biết mô hình học được gì ngoài bố cục trang. Phương pháp chính lấy khía cạnh từ từ điển và học cực tính bằng hồi quy logistic. Kết quả được đối chiếu thêm với điểm sao theo khía cạnh của trang nguồn.
- **WM5.** Chưa có log hành vi người dùng nên dùng phương pháp dựa trên nội dung. Baseline xếp theo độ phổ biến; so với trùng kỹ năng có trọng số IDF, độ tương tự TF-IDF và phương án pha thêm độ phổ biến. Kết quả của mọi phương pháp được gộp lại, chấm mù theo thang 0, 1, 2, rồi tính nDCG@10 và P@10.

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

Hai điểm vào: trích kỹ năng từ văn bản tin, và gợi ý tin theo danh sách kỹ năng. Mặc định dùng từ điển alias; đặt `JOBLENS_MINING_SKILL_MODEL` trỏ tới thư mục mô hình để dùng PhoBERT trên CPU.

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
| `crawler/` | Spider TopCV và ITviec, parser, lọc dữ liệu cá nhân, phát hiện tin trùng |
| `ie/` | WM2: từ điển alias, nhãn huấn luyện, huấn luyện và đánh giá PhoBERT |
| `absa/` | WM3: khía cạnh và cực tính của review |
| `recsys/` | WM5: baseline, phiếu chấm tay, chỉ số |
| `retrieval/`, `graph/` | WM4 và WM6 |
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
