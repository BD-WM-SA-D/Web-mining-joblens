# Luồng xử lý WM2 – trích kỹ năng từ tin tuyển dụng

*Cập nhật 23/11/2026. Chỗ chưa đo để `<...>`.*

WM2 nhận văn bản một tin tuyển dụng và trả về danh sách kỹ năng mà tin yêu cầu, kèm vị trí trong văn bản. Tài liệu này mô tả cách làm dữ liệu, nhãn, mô hình và cách đánh giá.

## 1. Tổng quan

```
                    Guideline gán nhãn kỹ năng
                 │                               │
                 ▼                               ▼
   ┌───────────────────────────┐   ┌──────────────────────────────┐
   │ Tập gán nhãn (người gán)  │   │ Nhãn huấn luyện (máy gán)    │
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
                       Tin mới → danh sách kỹ năng (đoạn, tên chuẩn, độ tin cậy)
```

## 2. Dữ liệu

| Nguồn | Dùng cho | Có gửi ra ngoài? |
|---|---|---|
| Tin TopCV nhóm tự crawl | Tập test (1.000 câu từ 125 tin); một phần câu train (có tag "Kỹ năng cần có") | Không |
| Tin ITviec nhóm tự crawl | Chạy thử và thống kê nhu cầu kỹ năng; không dùng để train WM2 | Không |
| VietJobs, các tin ngành IT (Pham Dinh et al., LREC 2026; CC BY 4.0) | Phần lớn câu train; tập dev; nguồn cho từ điển alias | **Có**: câu train được gửi tới dịch vụ LLM để gán nhãn |
| Từ điển 200 kỹ năng tự soạn, có alias tiếng Việt và tiếng Anh | Baseline, nhãn huấn luyện, chuẩn hóa tên kỹ năng | Không |

- Tách tập theo **tin**: tin đã có câu trong dev hoặc test thì không có câu nào trong train.
- Dữ liệu crawl được đóng băng thành bản chụp theo ngày, có mã băm danh sách tin, để chạy lại ra cùng kết quả.

## 3. Tập gán nhãn

- Câu được rút ngẫu nhiên với seed cố định, giới hạn số câu mỗi tin để một tin dài không chiếm phần lớn tập.
- Gán bằng công cụ chạy trên máy, nên dữ liệu không rời máy.
- Dev được gợi ý sẵn bằng từ điển. **Test gán không có gợi ý**, để tập không thiên về baseline.
- Người thứ hai gán độc lập khoảng 10% câu để đo Cohen's κ.
- Tập test được đóng băng bằng mã băm và không sửa sau khi chấm.

## 4. Nhãn huấn luyện

| Bước | Cách làm |
|---|---|
| ① Tag và từ điển | Dò lại tag nhà tuyển dụng và alias từ điển trong câu |
| ② Thêm luật | Thêm cụm guideline coi là kỹ năng, bỏ đoạn guideline loại (kỹ năng mềm, chức danh…) |
| ③ Self-training | Thêm đoạn mà cả ba mô hình PhoBERT (huấn luyện trên ②) cùng đoán |
| ④ LLM theo guideline | Câu VietJobs: LLM đọc guideline, trả danh sách đoạn chép nguyên văn; đoạn được dò lại trên token thành nhãn BIO. Câu TopCV giữ nhãn ③ |

Ràng buộc của bước ④:
- **LLM chỉ gán nhãn huấn luyện, không chạy khi dùng mô hình.** Mô hình giao đi chỉ là PhoBERT.
- Chỉ câu VietJobs được gửi đi. Câu crawl TopCV, ITviec và câu test bị chặn trước khi gọi, bằng kiểm tra trong code.
- Ví dụ trong guideline gửi kèm mà trùng một câu test thì bị bỏ khỏi prompt.
- Ghi số token và chi phí sau mỗi lần gọi, dừng khi vượt ngân sách. Nhãn được lưu lại để tái lập, vì dịch vụ ngoài có thể đổi mô hình.
- Gán khoảng 20.700 câu, mỗi lần gọi 20 câu, chi phí ước khoảng 0,54 USD.

## 5. Huấn luyện

- PhoBERT-base-v2, gán nhãn chuỗi theo BIO với một loại thực thể là kỹ năng.
- Câu được tách từ trước khi đưa vào PhoBERT; chỉ subword đầu của mỗi từ được tính loss. Khi chấm, nhãn được trải ngược về token gốc để so với nhãn của tập gán.
- Learning rate 3e-5, 3 epoch, batch 16, chọn epoch theo F1 trên dev. Ba seed để thấy độ dao động.

## 6. Đánh giá

- F1 cấp thực thể, khớp chặt (seqeval strict), trên tập test 1.000 câu TopCV; báo cả precision và recall.
- So hai hệ bằng bootstrap ghép cặp theo tin (1.000 lần), cùng seed.
- Mỗi thí nghiệm ghi trước cấu hình và quy tắc kết luận, rồi chấm test **đúng một lần**. Chỉ gọi là "tốt hơn" khi khoảng tin cậy 95% của ΔF1 nằm trên 0 ở cả ba seed.

| Hệ (test 1.000 câu) | P | R | F1 |
|---|---|---|---|
| Từ điển alias (baseline) | 0,742 | 0,315 | 0,442 |
| PhoBERT, nhãn yếu từ tag và từ điển | 0,705 | 0,469 | 0,562 |
| PhoBERT, nhãn yếu thêm luật và self-training | 0,715 | 0,543 | 0,617 |
| **PhoBERT, nhãn do LLM gán theo guideline** | **0,725** | **0,734** | **0,730** |

- So với mô hình dùng nhãn self-training: ΔF1 từ +0,109 đến +0,117, khoảng tin cậy nằm trên 0 ở cả ba seed.
- Lỗi còn lại chủ yếu ở ranh giới đoạn: F1 khớp một phần 0,811 so với 0,729 khớp chặt (seed 1).

## 7. Khi dùng mô hình (suy luận)

Với mỗi tin:

1. **Tag nhà tuyển dụng** (nếu có) được tra trong từ điển để ra tên kỹ năng chuẩn; độ tin cậy 1,0.
2. **Mô tả và yêu cầu** được tách dòng, tách token, đưa qua PhoBERT để lấy đoạn kỹ năng; độ tin cậy 0,8. Chế độ dự phòng không có PhoBERT dùng khớp từ điển; độ tin cậy 0,9.
3. **Chuẩn hóa:** đoạn được tra trong từ điển alias để ra tên chuẩn; không có trong từ điển thì dùng tên sinh từ chính chữ của đoạn.
4. **Bỏ trùng** đoạn cùng vị trí trong cùng một phần của tin.

- Độ tin cậy là mức cố định theo nguồn để nơi dùng có thể lọc, **không** phải xác suất đã hiệu chỉnh.
- Mô hình chạy trên CPU. Với 2 luồng CPU, trả lời một văn bản dài cỡ một tin (khoảng 1.600 ký tự) mất p50 0,07 giây, p95 0,21 giây.

## 8. Hạn chế

- Nhãn LLM vẫn là nhãn yếu; một mô hình LLM, gán một lần, chưa đo độ ổn định giữa các lần gán.
- Một số câu test trùng nguyên văn câu train (câu mẫu lặp giữa các tin); đã chấm lại khi bỏ các câu này, kết luận không đổi.
- Chuẩn hóa về bộ kỹ năng quốc tế (ESCO) mới làm một phần: `<...>` trên 200 kỹ năng.
- Dev cao hơn test (0,797 so với 0,730), có thể do nhãn LLM trên văn bản VietJobs khớp dev (cũng là VietJobs) hơn văn bản TopCV.
- Dữ liệu chỉ gồm tin IT đang mở trên một đến hai trang, trong khoảng hai tháng.
