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
- κ: `<...>` (chưa gán)
- Vai trò (quyết định 2026-10-12): **dev set / luyện guideline**, gán đến ~300 câu thì dừng. Tập test WM2 lấy từ tin TopCV tự crawl.

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
