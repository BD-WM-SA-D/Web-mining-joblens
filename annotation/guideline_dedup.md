# Guideline gán nhãn cặp tin trùng (WM1)

Gán cho WM1: mỗi **cặp tin** nhận một nhãn **trùng** hoặc **không trùng**.
Tập đánh giá: ~300 cặp, người thứ hai gán ~30 cặp để đo Cohen's κ (mục tiêu ≥ 0,7).

## 1. Định nghĩa "trùng"

Hai tin là **trùng** khi chúng là **cùng một vị trí tuyển dụng của cùng một công ty, trong cùng một đợt tuyển**,
dù đăng ở hai trang khác nhau hay đăng lại nhiều lần trên cùng một trang.

Câu hỏi để tự kiểm: *nếu ứng viên nộp hồ sơ cho cả hai tin, họ có đang ứng tuyển vào cùng một chỗ làm không?*
Có → trùng. Không → không trùng.

## 2. Quy tắc

**Trùng:**

1. Cùng công ty, cùng vị trí, mô tả viết lại nhưng công việc như nhau.
   *"Nhân Viên IT Helpdesk" (TopCV) và "IT Helpdesk" (ITviec) của cùng một công ty → trùng.*
2. Tiêu đề khác nhau nhưng chỉ do cách viết: thêm "Tuyển gấp", "Lương upto 2000$", tên chi nhánh, viết tắt.
3. Một tin tiếng Việt, một tin tiếng Anh, cùng vị trí: **cùng chức danh và cùng cấp**. Chức danh quản lý
   dịch tương đương coi là cùng cấp: "Trưởng nhóm" ≈ "Lead" ≈ "Manager", "Chuyên viên" ≈ "Specialist".
   *"Trưởng Nhóm Hạ Tầng Và Bảo Mật CNTT" và "Infrastructure Security Manager" cùng công ty → trùng.*
4. Khác số lượng tuyển, khác hạn nộp, khác ngày đăng → vẫn trùng nếu là cùng đợt.

**Không trùng:**

5. **Khác cấp bậc**: Junior ≠ Senior ≠ Lead, Fresher ≠ Middle. Đây là hai vị trí khác nhau.
   **Dải cấp bậc khác nhau cũng là khác cấp**: "Middle, Senior" ≠ "All Level" ≠ "Junior, Senior",
   dù hai dải giao nhau.
6. **Khác mảng kỹ thuật hoặc khác yêu cầu chính**: Backend Java ≠ Backend Python, iOS ≠ Android, Manual
   Tester ≠ Automation Tester. **Khác ngoại ngữ yêu cầu** cũng vậy: "IT Comtor – Tiếng Thái" ≠
   "IT Comtor – Tiếng Indonesian".
7. **Khác địa điểm làm việc** (Hà Nội ≠ TP.HCM), trừ khi tin ghi rõ nhiều địa điểm cho cùng một vị trí.
8. Cùng công ty, cùng nhóm nghề, nhưng mô tả công việc khác hẳn → hai vị trí khác nhau.
   **Tiêu đề khác nhau thì quyết theo phần mô tả công việc**: phần nhiệm vụ và yêu cầu như nhau →
   trùng (quy tắc 1); khác → không trùng. Đoạn giới thiệu công ty và phúc lợi **không tính**, vì công ty
   dùng chung cho mọi tin. *"AI Software Engineer … AI Agents" và "Agentic Engineer … Backend AI Agents"
   của MB Bank: xem nhiệm vụ, không xem tiêu đề.*
9. Công ty tuyển dụng hộ (headhunt, "Khách hàng của chúng tôi") mà không rõ là cùng công ty → **không trùng**,
   kèm cờ `khó / cần bàn`.

**Ca khó:**

10. Cùng vị trí nhưng đăng cách nhau nhiều tháng (ví dụ 03/2026 và 10/2026): coi là **hai đợt tuyển khác nhau**
    → không trùng. Ranh giới tạm đặt ở **3 tháng**; cặp quanh ranh giới thì tick `khó / cần bàn`.
11. Tin gộp nhiều vị trí ("Tuyển Backend/Frontend/Tester") so với tin lẻ một vị trí → **không trùng**.
12. Không đủ thông tin để quyết (mô tả quá ngắn, công ty viết khác tên) → chọn theo phán đoán tốt nhất
    và **bắt buộc** tick `khó / cần bàn`.

## 3. Cách gán

- Đọc **tên công ty và tiêu đề trước**, thường quyết được ngay.
- Chỉ đọc mô tả khi hai cái trên chưa đủ. Không cần đọc hết, so vài gạch đầu dòng đầu là được.
- Không tra cứu ngoài (không mở trang gốc, không Google). Chỉ dùng thông tin hiển thị trong task.
- Người gán **không biết cặp đến từ tầng nào** – trường `stratum` bị ẩn trong giao diện.

## 4. Vì sao tập nhãn có nhiều cặp "không trùng"

Cặp được rút theo 4 tầng (`annotation/sample_dedup_pairs.py`), trong đó tầng `same_company` là
cặp cùng công ty mà thuật toán **không** đề xuất. Tầng này dùng để đo **recall**: nếu chỉ gán cặp do
thuật toán đề xuất thì không bao giờ biết nó bỏ sót bao nhiêu.
Nên tỷ lệ nhãn "không trùng" cao là bình thường, không phải lỗi lấy mẫu.

## 5. Quy trình

1. Tạo project Label Studio, dán `annotation/label_studio_dedup.xml`, nhập `data/annotation/dedup_batch1.labelstudio.json`.
2. Gán thử 30 cặp → bàn các cặp khó → chốt guideline.
3. Gán hết ~300 cặp. Phím tắt: `1` = trùng, `2` = không trùng, Ctrl+Enter = Submit.
4. Người thứ hai gán ~30 cặp trên project riêng (không thấy nhãn người thứ nhất), tính Cohen's κ.
5. Export → tính P/R/F1 cho baseline và MinHash, ghi `experiments/results.md`.
