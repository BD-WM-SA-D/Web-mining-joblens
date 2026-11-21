# Luồng xử lý WM2 – trích kỹ năng từ tin tuyển dụng

*Cập nhật 19/11/2026, ứng với mô hình trích kỹ năng bản 0.2.0. Chỗ chưa đo để `<...>`.*

WM2 nhận văn bản một tin tuyển dụng và trả về danh sách kỹ năng mà tin yêu cầu, kèm vị trí trong văn bản. Tài liệu
này mô tả cách làm dữ liệu, nhãn, mô hình và cách đánh giá. Đầu ra được giao cho pipeline chung của dự án dưới dạng
một image Docker; phần vận hành pipeline thuộc môn khác nên không trình bày ở đây.

## 1. Tổng quan

```
                Guideline gán nhãn kỹ năng (bản 0.4)
                 │                               │
                 ▼                               ▼
   ┌───────────────────────────┐   ┌──────────────────────────────┐
   │ Tập vàng (người gán)      │   │ Nhãn yếu cho train (máy gán) │
   │ dev 300 câu VietJobs      │   │ ① tag nhà tuyển dụng + từ điển│
   │ test 1.000 câu TopCV      │   │ ② + luật theo guideline       │
   │ κ trên ~10% câu           │   │ ③ + self-training             │
   └─────────────┬─────────────┘   │ ④ câu VietJobs: LLM gán lại   │
                 │                 │    theo guideline             │
                 │                 └──────────────┬───────────────┘
                 │   chọn epoch trên dev          ▼
                 ├───────────────────► Fine-tune PhoBERT-base-v2 (BIO, 3 seed)
                 │   chấm test một lần            │
                 └───────────────────► F1 strict + bootstrap ghép cặp
                                                  │
                                                  ▼
                                  Đóng gói thành image, giao cho pipeline
                                                  │
                                                  ▼
                       Tin mới → danh sách kỹ năng (span, mã kỹ năng, độ tin cậy)
```

## 2. Dữ liệu

| Nguồn | Dùng cho | Có gửi ra ngoài? |
|---|---|---|
| Tin TopCV nhóm tự crawl | Tập test (1.000 câu từ 125 tin); một phần câu train (có tag "Kỹ năng cần có") | Không |
| Tin ITviec nhóm tự crawl | Chạy thử và thống kê nhu cầu kỹ năng; không dùng để train WM2 | Không |
| VietJobs, các tin ngành IT (Pham Dinh et al., LREC 2026; CC BY 4.0 / MIT) | Phần lớn câu train; tập dev; nguồn cho từ điển alias | **Có**: câu train được gửi tới API LLM để gán nhãn |
| Từ điển 200 kỹ năng tự soạn, có alias tiếng Việt và tiếng Anh | Baseline, nhãn yếu, chuẩn hóa mã kỹ năng | Không |

- Tách tập theo **tin**: tin đã có câu trong dev hoặc test thì không có câu nào trong train.
- Dữ liệu crawl được đóng băng thành snapshot theo ngày, có mã băm danh sách tin, để chạy lại ra cùng kết quả.

## 3. Tập vàng

- Câu được rút ngẫu nhiên có seed cố định, giới hạn số câu mỗi tin để một tin dài không chiếm phần lớn tập.
- Gán bằng Label Studio chạy trên máy, nên dữ liệu không rời máy.
- Dev được gợi ý sẵn bằng từ điển. **Test gán không có gợi ý**, để tập vàng không thiên về baseline.
- Người thứ hai gán độc lập khoảng 10% câu để đo Cohen's κ.
- Tập test được đóng băng bằng mã băm và không sửa sau khi chấm.

## 4. Nhãn yếu cho train

| Bước | Cách làm | Chất lượng so với nhãn tay (F1 trên dev) |
|---|---|---|
| ① Tag + từ điển | Dò lại tag nhà tuyển dụng và alias từ điển trong câu | 0,542 |
| ② Thêm luật | Thêm cụm guideline coi là kỹ năng, bỏ span guideline loại (kỹ năng mềm, chức danh…) | 0,600 |
| ③ Self-training | Thêm span mà cả ba mô hình PhoBERT (train trên ②) cùng đoán | (đo qua mô hình) |
| ④ LLM theo guideline | Câu VietJobs: LLM đọc guideline, trả danh sách span chép nguyên văn; span được dò lại trên token thành nhãn BIO. Câu TopCV giữ nhãn ③ | 0,849 |

Ràng buộc của bước ④:
- **LLM chỉ gán nhãn train, không chạy khi dùng mô hình.** Mô hình giao đi chỉ là PhoBERT.
- Chỉ câu VietJobs được gửi đi. Câu crawl TopCV/ITviec và câu test bị chặn trước khi gọi API, bằng kiểm tra trong code.
- Ví dụ trong guideline gửi kèm mà trùng một câu test thì bị bỏ khỏi prompt.
- Ghi số token và chi phí sau mỗi lần gọi, dừng khi vượt ngân sách. Kết quả nhãn được lưu lại để tái lập, vì dịch vụ ngoài có thể đổi mô hình.
- Mô hình LLM: `gpt-6-luna`, mỗi lần gọi 20 câu. Gán khoảng 20.700 câu, chi phí ước khoảng 0,54 USD.

## 5. Huấn luyện

- PhoBERT-base-v2, gán nhãn chuỗi theo BIO với một loại thực thể `SKILL`.
- Câu được tách từ bằng underthesea trước khi đưa vào PhoBERT; chỉ subword đầu của mỗi từ được tính loss. Khi chấm,
  nhãn được trải ngược về token gốc để so với nhãn vàng.
- Learning rate 3e-5, 3 epoch, batch 16, chọn epoch theo F1 trên dev. Ba seed để thấy độ dao động.
- Hai hướng sửa phía mô hình đã thử và **không** cải thiện: học tiếp PhoBERT trên văn bản tin tuyển dụng (DAPT) và
  giảm trọng số token O khi tính loss.

## 6. Đánh giá

- F1 cấp thực thể, khớp chặt (seqeval strict), trên tập test 1.000 câu TopCV; báo cả precision và recall.
- So hai hệ bằng bootstrap ghép cặp theo tin (1.000 lần), cùng seed.
- Mỗi thí nghiệm ghi trước cấu hình, dự đoán và quy tắc kết luận, rồi chấm test **đúng một lần**. Chỉ gọi là "tốt
  hơn" khi khoảng tin cậy 95% của ΔF1 nằm trên 0 ở cả ba seed.

| Hệ (test 1.000 câu) | P | R | F1 |
|---|---|---|---|
| Từ điển alias (baseline) | 0,742 | 0,315 | 0,442 |
| PhoBERT, nhãn yếu tag + từ điển | 0,705 | 0,469 | 0,562 |
| PhoBERT, nhãn yếu self-training (bản 0.1.0) | 0,715 | 0,543 | 0,617 |
| **PhoBERT, nhãn yếu do LLM gán (bản 0.2.0)** | **0,725** | **0,734** | **0,730** |

- So với bản 0.1.0: ΔF1 +0,109 đến +0,117, khoảng tin cậy nằm trên 0 ở cả ba seed.
- Bỏ 30 câu test trùng nguyên văn một câu train: 0,731 so với 0,620, kết luận không đổi.
- Chênh dev (VietJobs) và test (TopCV): 0,797 so với 0,730.

## 7. Khi dùng mô hình (suy luận)

Với mỗi tin:

1. **Tag nhà tuyển dụng** (nếu có) được tra trong từ điển để ra mã kỹ năng; độ tin cậy 1,0.
2. **Mô tả và yêu cầu** được tách dòng, tách token, đưa qua PhoBERT để lấy span kỹ năng; độ tin cậy 0,8. Bản dự phòng
   không có PhoBERT dùng khớp từ điển; độ tin cậy 0,9.
3. **Chuẩn hóa:** span được tra trong từ điển alias để ra mã kỹ năng chung; không có trong từ điển thì dùng mã sinh
   từ chính chữ của span.
4. **Bỏ trùng** span cùng vị trí trong cùng trường.
5. Mỗi dòng kết quả ghi phiên bản mô hình đã tạo ra nó, để biết số liệu phía sau đến từ bản nào.

- Độ tin cậy là mức cố định theo nguồn để nơi dùng có thể lọc, **không** phải xác suất đã hiệu chỉnh.
- Mô hình chạy trên CPU. Đo với 2 luồng CPU: khoảng 0,45 giây/tin khi chạy theo lô (ước khoảng 6 giờ cho 50.000
  tin, chia lô chạy song song được); trả lời một văn bản dài cỡ một tin (~1.600 ký tự) mất p95 0,21 giây.

## 8. Đóng gói và phiên bản

- Mô hình giao dưới dạng image Docker có hai bản: **full** (PhoBERT, torch bản CPU) và **dự phòng** (chỉ từ điển, nhỏ
  và nhanh). Tag image theo dạng `x.y.z-gitsha`, không dùng `latest`.
- Bản hiện hành: 0.2.0, dùng mô hình seed 1.
- Mỗi lần đổi mô hình chỉ khi thắng rõ theo quy tắc ở mục 6; khi đổi thì cập nhật danh mục model (metric, dữ liệu
  train, tập test) và báo nhóm vận hành pipeline đổi tag.
- So với 0.1.0, đầu vào và đầu ra không đổi định dạng. Mỗi tin ra nhiều kỹ năng hơn (recall 0,54 → 0,73), nên các
  số đếm kỹ năng phía sau sẽ tăng.

## 9. Hạn chế

- Nhãn LLM vẫn là nhãn yếu (F1 0,849 so với nhãn tay); một mô hình LLM, gán một lần, chưa đo độ ổn định giữa các lần gán.
- 30/1.000 câu test trùng nguyên văn câu train (câu mẫu lặp giữa các tin); đã chấm lại khi bỏ các câu này.
- Chưa chuẩn hóa về ESCO: mã kỹ năng hiện là mã của từ điển tự soạn.
- Dev cao hơn test 0,067 F1, có thể do nhãn LLM trên văn bản VietJobs khớp dev (cũng là VietJobs) hơn văn bản TopCV.
- Dữ liệu chỉ gồm tin IT đang mở trên một đến hai trang, trong khoảng hai tháng.
