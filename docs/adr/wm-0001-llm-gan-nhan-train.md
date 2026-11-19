# ADR WM-0001 – Dùng LLM để gán nhãn train cho WM2, không chạy LLM trong sản phẩm

| | |
|---|---|
| **Trạng thái** | ĐÃ ÁP DỤNG (image `skill-extractor` 0.2.0) – chờ nhóm xem |
| **Ngày** | 2026-11-19 |
| **Người soạn** | Hoang Le (nháp bằng Claude Code) |
| **Phạm vi** | Repo Web Mining. Không đổi hợp đồng dữ liệu hay hợp đồng chạy image |
| **Liên quan** | ADR 0001 D3 (image mô hình), ADR 0002 (`mining-service`), `docs/luong-xu-ly-wm2.md`, `experiments/results.md` |

## Bối cảnh

- WM2 trích span kỹ năng bằng PhoBERT. Mô hình học từ **nhãn yếu**, vì nhóm chỉ gán tay được tập dev (300 câu) và
  tập test (1.000 câu).
- Nhãn yếu ban đầu (tag nhà tuyển dụng + từ điển + luật + self-training) cho F1 test 0,617. So với nhãn tay trên dev,
  bản thân nhãn yếu chỉ được F1 0,600; recall 0,48, tức bỏ sót khoảng một nửa kỹ năng.
- Hai cách sửa phía mô hình đều không cải thiện: học tiếp PhoBERT trên văn bản tin tuyển dụng (0,607) và giảm trọng
  số token O khi train (0,615, khoảng tin cậy chứa 0). Nút thắt nằm ở nhãn train.
- Tài liệu kế hoạch đã loại **chatbot LLM** khỏi sản phẩm (blueprint mục 1: nằm ngoài nội dung môn, khó đánh giá, dễ
  bịa, tốn chi phí API). Quyết định này không đảo lại điều đó.

## Quyết định

1. **LLM chỉ làm người gán nhãn train.** Một mô hình LLM qua API đọc guideline gán nhãn kỹ năng 0.4 của nhóm (chính
   guideline dùng cho tập vàng) và gán span cho câu train. Đầu ra được dò lại trên token thành nhãn BIO.
2. **Sản phẩm vẫn chỉ chạy PhoBERT.** Image `skill-extractor` chạy trên CPU trong pod, không gọi API ngoài và không
   cần key. `mining-service` không đổi.
3. **Chỉ gửi câu VietJobs ra ngoài.** VietJobs là bộ dữ liệu công khai (CC BY 4.0 / MIT, trích dẫn Pham Dinh et al.,
   LREC 2026). Câu crawl TopCV/ITviec và câu test bị chặn ngay trong code; câu TopCV giữ nhãn yếu cũ.
4. **Nhãn LLM không bao giờ là tập test.** Đánh giá vẫn trên tập test gán tay, chấm một lần theo quy tắc đăng ký trước.
5. **Đổi image chỉ khi thắng rõ.** Quy tắc ghi trước khi chạy: CI95 của ΔF1 (bootstrap ghép cặp theo tin) > 0 ở cả
   3 seed. Kết quả: 0,617 → 0,730, ΔF1 +0,109…+0,117, cả 3 khoảng tin cậy nằm trên 0. Image đổi sang 0.2.0.

## Các phương án đã cân nhắc

| Phương án | Vì sao không chọn |
|---|---|
| Gán tay thêm câu train | Chậm (vài nghìn câu mới đủ), chỉ một người gán chính |
| Dùng thẳng cột `technical_skills` của VietJobs (cũng do LLM sinh) | Không theo guideline của nhóm, không có vị trí span; tag nhà tuyển dụng tỏ ra tốt hơn (`joblens/docs/project-plan/13-kham-pha-du-lieu.md`) |
| Chạy LLM trực tiếp để trích kỹ năng trong sản phẩm | Tốn chi phí mỗi lần chạy, phụ thuộc dịch vụ ngoài, khó tái lập, gửi dữ liệu crawl ra ngoài, trái với ranh giới đã chốt |
| Sửa mô hình (DAPT, đổi hàm loss) | Đã thử theo đăng ký trước, không cải thiện |

## Hệ quả

**Tốt:**
- F1 test tăng 0,617 → 0,730, tăng cả precision lẫn recall; chi phí API dưới 1 USD (~0,54 USD ước tính).
- Hợp đồng chạy, schema `silver.job_skills`, tài nguyên pod không đổi. Nhóm Big Data chỉ cần đổi tag image.

**Phải chấp nhận:**
- Thêm một phụ thuộc bên ngoài **lúc train**: dịch vụ có thể đổi mô hình, nên tái lập dựa vào file nhãn LLM đã lưu
  (`data/llm/`, không commit; cần lưu cùng dữ liệu ở `s3://joblens/…`).
- Nhãn LLM vẫn nhiễu (F1 0,849 so với nhãn tay trên dev); một mô hình, gán một lần.
- Số kỹ năng mỗi tin trong `silver.job_skills` tăng; các bảng đếm phía sau sẽ đổi số.
- Key API nằm trong `.env` cục bộ, không bao giờ commit; key đã lộ phải thu hồi.

## Việc kèm theo

- [x] `ie/llm_label.py`, `ie/weak_llm.py`; đăng ký trước và kết quả trong `experiments/results.md`.
- [x] Build image 0.2.0 bản full, chạy thử cục bộ; cập nhật `models.yaml`, `NHAT-KY.md`.
- [x] Ghi luồng dữ liệu mới vào `joblens/docs/project-plan/02-du-lieu.md`, `04-…`, `13-…` (nhánh `docs/wm2-nhan-yeu-llm`, chờ PR).
- [ ] Gắn tag `0.2.0-<gitsha>` sau khi commit; báo Big Data đổi tag trong DAG và ghi `deploy/compat.md`.
- [ ] Đẩy file nhãn LLM và model lên `s3://joblens/…`.
- [ ] Đo thời gian chạy bản full trên CPU cho 50.000 tin: `<chưa đo>`.
