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
