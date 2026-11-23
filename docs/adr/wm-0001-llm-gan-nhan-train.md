# ADR WM-0001 – Dùng LLM để gán nhãn huấn luyện cho WM2, không chạy LLM khi dùng mô hình

| | |
|---|---|
| **Trạng thái** | Đã áp dụng |
| **Ngày** | 2026-11-19 |
| **Phạm vi** | WM2, trích xuất kỹ năng. Không đổi đầu vào và đầu ra của mô hình |

## Bối cảnh

- WM2 tìm các đoạn nói về kỹ năng bằng PhoBERT. Mô hình học từ **nhãn yếu**, vì nhóm chỉ gán tay được tập dev (300 câu) và tập test (1.000 câu).
- Nhãn yếu làm từ tag của nhà tuyển dụng, từ điển, luật và self-training bỏ sót khoảng một nửa số kỹ năng so với nhãn tay.
- Các thử nghiệm ở phía mô hình (huấn luyện thêm trên văn bản tin tuyển dụng, đổi trọng số hàm loss) không cải thiện đáng tin cậy. Nút thắt nằm ở chất lượng nhãn huấn luyện.
- Không dùng chatbot LLM trong hệ thống: nằm ngoài phạm vi môn học, khó đánh giá, dễ bịa và tốn chi phí. Quyết định này không đảo lại điều đó.

## Quyết định

1. **LLM chỉ làm người gán nhãn huấn luyện.** LLM đọc guideline gán nhãn kỹ năng của nhóm (chính guideline dùng cho tập kiểm tra) và trả danh sách đoạn kỹ năng. Đầu ra được dò lại trên token thành nhãn BIO.
2. **Khi dùng, mô hình vẫn chỉ là PhoBERT** chạy trên CPU: không gọi dịch vụ ngoài, không cần khóa truy cập.
3. **Chỉ gửi câu VietJobs ra ngoài.** VietJobs là bộ dữ liệu công khai (CC BY 4.0, trích dẫn Pham Dinh et al., LREC 2026). Câu nhóm tự crawl và câu thuộc tập kiểm tra bị chặn bằng kiểm tra trong code; câu TopCV giữ nhãn yếu từ self-training.
4. **Nhãn LLM không bao giờ là tập kiểm tra.** Đánh giá vẫn trên tập gán tay, chấm một lần theo quy tắc ghi trước.
5. **Chỉ đổi mô hình khi thắng rõ:** khoảng tin cậy 95% của ΔF1 (bootstrap ghép cặp theo tin) nằm trên 0 ở cả ba seed. Với nhãn LLM, F1 tăng từ 0,617 lên 0,730 (ΔF1 từ +0,109 đến +0,117), cả ba khoảng tin cậy nằm trên 0.

## Các phương án đã cân nhắc

| Phương án | Vì sao không chọn |
|---|---|
| Gán tay thêm câu huấn luyện | Cần vài nghìn câu mới đủ; nhóm chỉ có một người gán chính |
| Dùng thẳng cột kỹ năng có sẵn của VietJobs | Không theo guideline của nhóm, không có vị trí đoạn |
| Chạy LLM trực tiếp để trích kỹ năng khi dùng | Tốn chi phí mỗi lần chạy, phụ thuộc dịch vụ ngoài, khó tái lập, phải gửi dữ liệu crawl ra ngoài |
| Sửa phía mô hình | Đã thử theo quy tắc ghi trước, không cải thiện |

## Hệ quả

**Được:**
- F1 trên tập kiểm tra tăng, cả precision lẫn recall; chi phí gán nhãn khoảng 0,54 USD cho khoảng 20.700 câu.
- Đầu vào, đầu ra và tài nguyên cần để chạy mô hình không đổi.

**Phải chấp nhận:**
- Thêm một phụ thuộc bên ngoài **lúc làm nhãn**: dịch vụ có thể đổi mô hình, nên việc tái lập dựa vào bộ nhãn LLM đã lưu lại.
- Nhãn LLM vẫn là nhãn yếu; một mô hình LLM, gán một lần, chưa đo độ ổn định giữa các lần gán.
- Mỗi tin cho nhiều kỹ năng hơn, nên các số đếm kỹ năng tính từ kết quả sẽ thay đổi.
- Khóa truy cập chỉ để trên máy, không đưa vào repo.

## Việc kèm theo

- [x] Bộ gán nhãn bằng LLM, có chặn dữ liệu crawl và câu kiểm tra; cấu hình và kết quả được ghi trước khi chạy.
- [x] Đóng gói mô hình (bản đầy đủ và bản chỉ dùng từ điển), chạy thử.
- [x] Đo tốc độ trên CPU (2 luồng): một văn bản khoảng 1.600 ký tự mất p95 0,21 giây.
- [ ] Lưu bộ nhãn LLM và mô hình ở nơi lưu trữ riêng.
