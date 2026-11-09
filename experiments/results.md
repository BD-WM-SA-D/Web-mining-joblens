# Kết quả thực nghiệm Web Mining

Chỉ ghi số liệu, không ghi dữ liệu gốc. Mỗi số kèm snapshot dữ liệu và lệnh tạo ra nó.

## Dữ liệu

> Dữ liệu chính là tin tự crawl (TopCV, ITviec). VietJobs chỉ dùng cho nhãn yếu, từ điển alias và baseline – không dùng làm tập test.

### VietJobs – tập IT `it_v1` (2026-10-07)

- Nguồn: `dinhieufam/VietJobs`, revision `ea140511b77935704e93d21c2973b72f46d48902`, CSV sha256 `85862b06…c49d477`. Trích dẫn Pham Dinh et al., LREC 2026.
- Lọc `category == công_nghệ_thông_tin_kỹ_thuật_số`: 1.906 / 48.092 tin. Nhóm này có cả vị trí không kỹ thuật (kinh doanh, thiết kế đồ họa).
- Lệnh: `uv run python -m ie.vietjobs`

### Từ điển kỹ năng nháp (`ie/resources/skill_alias.csv`)

- 200 kỹ năng chuẩn, 442 cách viết (bản tự sinh, chưa xem tay).
- Từ điển phủ 54,9% số lần gắn tag `technical_skills` trong tập IT (phần còn lại là đuôi dài, 3.771 tag khác nhau).
- 84,4% số tag xuất hiện nguyên văn trong mô tả/yêu cầu. Đây là giới hạn trên cho nhãn yếu dạng span của WM2.
- Lệnh: `uv run python -m ie.skill_alias --top 200`

### Đợt gán nhãn kỹ năng 1 (`skill_batch1`)

- 1.507 câu từ 125 tin (seed 20261007), trong đó 153 câu của 12 tin được hai người gán để đo κ.
- Lệnh: `uv run python -m annotation.sample_skill_batch --sentences 1500`
- κ: `<...>` (153 câu `double` đã có nhãn người thứ nhất, chưa có người thứ hai)
- Vai trò (quyết định 2026-10-12): **dev set / luyện guideline**, gán đến ~300 câu thì dừng. Tập test WM2 lấy từ tin TopCV tự crawl.
- **Đã gán xong dev (2026-10-18):** 300 câu đầu (24 tin, 7.301 token), 1 người gán.
  - 129 câu có kỹ năng, 171 câu rỗng (57%); 294 span SKILL.
  - Gợi ý sẵn bằng từ điển (`annotation/preannotate_dict.py`, `dict-alias-v0`) cho 300 câu chưa gán; 59 câu có gợi ý, người gán giữ nguyên 20 câu, sửa 39 câu.
  - Rà lại toàn bộ sau khi gán: sửa 13 câu sai hoặc lệch quy tắc; 15 span dính khoảng trắng/dấu câu ở mép được cắt tự động khi đổi BIO; 0 span lệch ranh giới token.
  - 9 câu tick "khó / cần bàn" → các quy tắc chốt vào guideline bản 0.3.
  - Lệnh: `uv run python -m annotation.export_bio --project 1 --batch skill_batch1` → `data/annotation/skill_batch1.bio.jsonl`.

## WM2 – trích kỹ năng

### Baseline từ điển trên dev `skill_batch1` (2026-10-18)

| Tập | Câu | Span vàng | P | R | F1 (seqeval strict) |
|---|---|---|---|---|---|
| dev `skill_batch1` | 300 | 294 | 0,869 | 0,361 | 0,510 |

- F1 khoảng tin cậy 95% (bootstrap 1.000 lần theo câu): [0,440; 0,582] – dev chỉ 300 câu nên khoảng còn rộng.
- Lệnh: `uv run python -m ie.baseline_dict --bio data/annotation/skill_batch1.bio.jsonl --eval-set skill_batch1 --split dev` (ghi thêm `experiments/runs/<run_id>.json`)
- **P trên dev bị đẩy lên:** 257/300 câu được gợi ý sẵn bằng chính từ điển này trước khi người gán sửa, và từ điển dựng từ tag VietJobs cùng nguồn. Số chính thức phải đo trên test `skill_test1` (TopCV, gán không có gợi ý).
- Bỏ sót chủ yếu: (1) kỹ năng dạng cụm tiếng Việt không có trong từ điển (`vận hành máy CNC`, `vẽ tay`, `thiết kế thumbnail`, `mô hình dữ liệu`, `phân khúc khách hàng`); (2) tên công cụ ngoài top 200 (`Digiwin T100`, `IBM MQ`, `Katalon`, `Mastercam`, `ELK`); (3) một số alias thiếu dù có nhóm (`Agile`, `Scrum` khi viết "Agile/Scrum").
- Gán thừa: `API` (quá chung theo guideline), `C` đứng riêng, "Agile/Scrum" khớp thành một span thay vì hai, và lệch ranh giới (`React` trong "ReactJS…", `phân tích yêu cầu` khi người gán lấy cụm dài hơn).

### Nhãn yếu cho train PhoBERT `wm2_weak_v1` (2026-11-09)

- Cách gán: tag kỹ năng của chính tin (VietJobs `technical_skills`, TopCV `skill_tags`; bỏ kỹ năng mềm theo từ vựng
  `soft_skills` của VietJobs, bỏ tag > 5 token) cộng từ điển alias, dò khớp dài nhất trên token.
- Loại toàn bộ 250 tin thuộc dev `skill_batch1` và test `skill_test1` (theo job_uid trong manifest).
- Kết quả: 1.781 tin VietJobs + 179 tin TopCV → 24.144 câu, 6.438 câu có kỹ năng (27%), 14.390 span.
- Độ nhiễu, đo bằng cách áp cùng cách gán lên 300 câu dev đã gán tay (seqeval strict):

| Cách gán | P | R | F1 |
|---|---|---|---|
| Chỉ từ điển (= baseline) | 0,869 | 0,361 | 0,510 |
| Chỉ tag của tin | 0,757 | 0,180 | 0,291 |
| Tag + từ điển (dùng cho train) | 0,799 | 0,405 | 0,537 |

- Nhận xét: nhãn yếu bắt được ~40% kỹ năng thật → mô hình train trên đó dễ học thói "bỏ sót" (câu có kỹ năng nhưng bị
  gán toàn O). Hướng xử lý khi train: bỏ bớt câu không có span nào, hoặc chỉ tính loss trên token đã gán B/I.
- Lệnh: `uv run python -m ie.weak_labels` → `data/weak/wm2_weak_v1.bio.jsonl`

### Crawl thử TopCV (2026-10-12)

- Lệnh: `uv run python -m crawler.topcv.run --max-jobs 20` (parser `topcv-parser:0.1.0`, bộ lọc slug bản đầu).
- 23 request (1 robots.txt, 2 sitemap, 20 trang tin), tất cả HTTP 200, không bị chặn, 30 giây.
- 4/20 trang là tin IT (danh mục chính "Công nghệ Thông tin"), 0 lỗi parse, 4/4 khớp `job_posting.v1`, 4/4 có `date_posted`, 2/4 có lương dạng số.
- Bộ lọc slug bản đầu khớp chuỗi con ("ai" khớp "tai") → sửa sang khớp từ nguyên vẹn: số URL lọt lọc trong một sitemap con giảm 29 → 8/200.
- Sitemap tin TopCV: 220 file con × ~200 URL ≈ 44.000 tin đang có. Ước tính crawl toàn bộ tin IT: ~2.000 request (~35–40 phút).
- Tag "Kỹ năng cần có" của nhà tuyển dụng lẫn kỹ năng mềm ("Giao tiếp", "Làm việc nhóm") và cụm dài → nhãn yếu WM2 phải lọc qua từ điển alias.

### Crawl TopCV đợt 1 và sự cố HTTP 429 (2026-10-12)

**Sự cố:** lần chạy `--max-jobs 2000 --max-sitemaps 220` (19:56–21:52) bị TopCV trả **HTTP 429 (Too Many Requests)** từ khoảng 20:40. Spider bản cũ không dừng mà thử lại (RETRY_TIMES = 2), AUTOTHROTTLE còn rút ngắn khoảng cách vì 429 trả về nhanh → **5.507 request, 4.673 bị 429**, 832 thành công. Khi theo dõi, agent chỉ nhìn số trang/phút nên báo nhầm là "máy chủ chậm".
**Đã sửa (`crawler/topcv/spider.py`):** gặp 429/403 là dừng cả lần chạy, không thử lại; tối thiểu 3 giây/request; tối đa 1 lần thử lại cho lỗi 5xx; dừng khi quá 20 lỗi. **Bài học:** theo dõi crawl phải xem mã HTTP (`response_status_count`), không chỉ số trang.
**Từ nay:** mỗi ngày tối đa vài trăm request, chia nhỏ; không chạy lại trong ngày đã bị 429.

**Dữ liệu thu được (đợt 1, gộp lần thử):** 304 tin IT khác nhau.

| Chỉ số | Giá trị |
|---|---|
| Lương dạng số / "Thỏa thuận" | 55% / 44% |
| Có tag "Kỹ năng cần có" | 51% (median 1 tag/tin; trung bình 5,1) |
| Tag phổ biến | Python 17, SQL 15, **Giao tiếp 14, Làm việc nhóm 11**, Java 10, Giải quyết vấn đề 9 – kỹ năng mềm lẫn nhiều |
| `date_posted` | 100% có; 17/08–12/10/2026 (09: 146 tin, 10: 157 tin) – sitemap chỉ chứa tin đang mở |
| Nhóm nghề | Software Engineering 60, IT Infrastructure 59, Software Testing 37, Thiết kế 31, Product Management 27, AI 18 |
| Địa điểm | Hà Nội 199, TP.HCM 70, Đà Nẵng 8 |
| Độ dài mô tả + yêu cầu | median 301 từ; 100% có phần yêu cầu |

### Tập test WM2 `skill_test1` (2026-10-12)

- Snapshot `topcv_v1`: 304 tin IT TopCV, ngày đăng 17/08–12/10/2026, ids_sha256 `61bad0f9…d1377048`. Lệnh: `uv run python -m crawler.snapshot --source topcv --name topcv_v1`.
- Rút mẫu: 1.000 câu từ 125 tin (tối đa 8 câu/tin, seed 20261012), 96 câu của 12 tin để đo κ. Nhóm nghề: hạ tầng IT 24, phát triển phần mềm 21, testing 17, thiết kế 15, product 14, AI 9.
- Có câu tiếng Anh (tin của công ty nước ngoài).
- κ: `<...>` (chưa gán)
