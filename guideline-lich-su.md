# Lịch sử thay đổi các guideline gán nhãn

Chuyển từ cuối từng file guideline trên nhánh chính.

## guideline_absa.md

## Lịch sử

| Bản | Ngày | Thay đổi |
|---|---|---|
| 0.1 | 2026-11-12 | Nháp đầu, chờ duyệt và gán thử 50 câu |
| 0.1.1 | 2026-11-13 | Thêm mục "câu đến từ phần nào" và mục 7 hạn chế, sau khi crawl 200 công ty |
| 0.1.2 | 2026-11-15 | Nói rõ **để trống ≠ `neutral`** (câu hỏi lúc gán lô thử); sửa cấu hình Label Studio bị trắng trên trắng ở chế độ Dark |
| 0.1.3 | 2026-11-15 | Thêm mục 2b: quy trình 4 bước gán một câu, kèm ví dụ chạy đủ các bước |
| 0.2 | 2026-11-15 | Sau lô thử 60 câu: mục 2c bảng tra thuật ngữ, luật 8–9 siết `neutral`, gỡ nhập nhằng "du lịch công ty" |
| 0.2.1 | 2026-11-15 | Thêm luật 10 (gán theo điều người viết muốn nói) và mục 2d: phép thử đổi chiều + ba câu hỏi cho `neutral` |
| 0.2.2 | 2026-11-17 | Bỏ câu luật tự mâu thuẫn về "môi trường" ở mục 2c; chốt "môi trường + từ đánh giá chung" → `culture_fun` |
| 0.2.3 | 2026-11-17 | Sau khi đo κ (0,871 trên 35 câu): mục 2c thêm "năng lực của sếp/lead" → `management_care`, "CLB, uống bia" → `culture_fun`, và luật "câu liệt kê nhiều thứ phải tra từng thứ" (chỗ hai người lệch nhiều nhất) |

## guideline_dedup.md

## Lịch sử

| Bản | Ngày | Thay đổi |
|---|---|---|
| 0.1 | 2026-11-13 | Nháp đầu, chờ duyệt và gán thử 30 cặp |
| 0.2 | 2026-11-18 | Sau κ = 0,733 (4 cặp lệch, cả 4 người 1 "trùng" / người 2 "không trùng"): dải cấp bậc khác = khác cấp (5); khác ngoại ngữ yêu cầu = khác (6); tiêu đề khác thì quyết theo mô tả công việc, bỏ qua khung công ty (8); Việt/Anh cần cùng chức danh và cùng cấp, "Trưởng nhóm" ≈ "Manager" (3) |

## guideline_skill.md

## Lịch sử

| Bản | Ngày | Thay đổi |
|---|---|---|
| 0.1 | 2026-10-07 | Bản đầu |
| 0.2 | 2026-10-11 | Thêm chứng chỉ, sản phẩm đem bán, tên thiết bị; ví dụ từ đợt 1; các bước Label Studio |
| 0.3 | 2026-10-18 | Chốt sau 300 câu dev: quy tắc span 11–15 (viết tắt trong ngoặc, phiên bản, lược từ, từ bổ nghĩa, giữ/bỏ động từ); mục "Quy tắc chốt khi gán đợt 1" (cụm từ quyết định, tên trước ngoặc, chỉ số, tài liệu đầu ra, chức danh, từ quá chung) |
| 0.4 | 2026-11-12 | Chốt sau κ lần 1 trên tập test: tài liệu BA không gán; wireframe/prototype/mockup gán; cloud/AI đứng riêng gán; bảo mật chỉ gán khi cụ thể; "quản lý" chỉ gán nghiệp vụ chính thức; nghiệp vụ ngành gán; thiết bị hạ tầng không gán (sửa quy tắc 9); động từ chung + việc, từ chung đứng riêng, ranh giới hay lệch |
