# ADR WM-0001 – Dùng LLM để gán nhãn train cho WM2, không chạy LLM khi dùng mô hình

| | |
|---|---|
| **Trạng thái** | Đã áp dụng (mô hình trích kỹ năng bản 0.2.0) – chờ nhóm xem |
| **Ngày** | 2026-11-19 |
| **Người soạn** | Hoang Le (nháp bằng Claude Code) |
| **Phạm vi** | WM2 – trích kỹ năng. Không đổi định dạng đầu vào, đầu ra của mô hình |

## Bối cảnh

- WM2 trích span kỹ năng bằng PhoBERT. Mô hình học từ **nhãn yếu**, vì nhóm chỉ gán tay được tập dev (300 câu) và
  tập test (1.000 câu).
- Nhãn yếu làm từ tag nhà tuyển dụng, từ điển, luật và self-training cho F1 test 0,617. So với nhãn tay trên dev,
  chính nhãn yếu chỉ được F1 0,600 với recall 0,48, tức bỏ sót khoảng một nửa kỹ năng.
- Hai cách sửa phía mô hình đều không cải thiện: học tiếp PhoBERT trên văn bản tin tuyển dụng (0,607) và giảm trọng
  số token O khi train (0,615, khoảng tin cậy chứa 0). Nút thắt nằm ở nhãn train.
- Kế hoạch dự án đã loại chatbot LLM khỏi sản phẩm (ngoài nội dung môn, khó đánh giá, dễ bịa, tốn chi phí). Quyết
  định này không đảo lại điều đó.

## Quyết định

1. **LLM chỉ làm người gán nhãn train.** LLM đọc guideline gán nhãn kỹ năng của nhóm (chính guideline dùng cho tập
   vàng) và gán span cho câu train. Đầu ra được dò lại trên token thành nhãn BIO.
2. **Khi dùng, mô hình vẫn chỉ là PhoBERT** chạy trên CPU: không gọi API ngoài, không cần key.
3. **Chỉ gửi câu VietJobs ra ngoài.** VietJobs là bộ dữ liệu công khai (CC BY 4.0 / MIT, trích dẫn Pham Dinh et al.,
   LREC 2026). Câu nhóm tự crawl và câu test bị chặn bằng kiểm tra trong code; câu TopCV giữ nhãn yếu cũ.
4. **Nhãn LLM không bao giờ là tập test.** Đánh giá vẫn trên tập test gán tay, chấm một lần theo quy tắc ghi trước.
5. **Chỉ đổi mô hình khi thắng rõ:** khoảng tin cậy 95% của ΔF1 (bootstrap ghép cặp theo tin) nằm trên 0 ở cả ba
   seed. Kết quả: 0,617 → 0,730, ΔF1 +0,109 đến +0,117, cả ba khoảng tin cậy nằm trên 0. Mô hình đổi sang bản 0.2.0.

## Các phương án đã cân nhắc

| Phương án | Vì sao không chọn |
|---|---|
| Gán tay thêm câu train | Cần vài nghìn câu mới đủ; nhóm chỉ có một người gán chính |
| Dùng thẳng cột kỹ năng có sẵn của VietJobs (cũng do LLM sinh) | Không theo guideline của nhóm, không có vị trí span |
| Chạy LLM trực tiếp để trích kỹ năng khi dùng | Tốn chi phí mỗi lần chạy, phụ thuộc dịch vụ ngoài, khó tái lập, phải gửi dữ liệu crawl ra ngoài |
| Sửa mô hình (DAPT, đổi hàm loss) | Đã thử theo quy tắc ghi trước, không cải thiện |

## Hệ quả

**Được:**
- F1 test tăng 0,617 → 0,730, tăng cả precision lẫn recall; chi phí API ước khoảng 0,54 USD.
- Định dạng đầu vào, đầu ra và tài nguyên cần để chạy mô hình không đổi.

**Phải chấp nhận:**
- Thêm một phụ thuộc bên ngoài **lúc làm nhãn**: dịch vụ có thể đổi mô hình, nên tái lập dựa vào bộ nhãn LLM đã lưu.
- Nhãn LLM vẫn nhiễu (F1 0,849 so với nhãn tay trên dev); một mô hình LLM, gán một lần.
- Mỗi tin ra nhiều kỹ năng hơn, nên các số đếm kỹ năng phía sau sẽ đổi.
- Key API chỉ để trên máy, không đưa vào repo.

## Việc kèm theo

- [x] Bộ gán nhãn bằng LLM, có chặn dữ liệu crawl và câu test; đăng ký trước và kết quả trong bảng kết quả thực nghiệm.
- [x] Đóng gói mô hình bản 0.2.0 (full và dự phòng), chạy thử; cập nhật danh mục model và nhật ký.
- [ ] Báo nhóm vận hành pipeline đổi tag image.
- [ ] Lưu bộ nhãn LLM và mô hình lên kho dữ liệu chung.
- [x] Đo tốc độ trên CPU (2 luồng): ~0,45 giây/tin theo lô; một văn bản ~1.600 ký tự p95 0,21 giây.
