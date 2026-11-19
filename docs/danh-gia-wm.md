# Khung đánh giá phần Web Mining – JobLens

*Bản 20/10/2026, cập nhật mục WM2 ngày 19/11/2026. Nguồn cho chương "Thực nghiệm" và "Thảo luận" của báo cáo WM, và cho buổi trình bày với giảng viên. Số có thật lấy từ `experiments/results.md`; số chưa đo để `<...>`.*

## 1. Project trả lời những câu hỏi nào

Mỗi kỹ thuật trong project được chọn để trả lời một câu hỏi cụ thể về dữ liệu tuyển dụng IT tiếng Việt. Đánh giá không chỉ để chấm mô hình mà để trả lời các câu hỏi này.

| Mã | Câu hỏi nghiên cứu | Bài | Chủ đề môn Web Mining |
|---|---|---|---|
| RQ1 | Có thu thập được tin tuyển dụng tiếng Việt **hợp pháp, lịch sự** mà vẫn đủ chất lượng để khai phá không? | Thu thập (WM1a) | Web crawling, dữ liệu có cấu trúc trên web |
| RQ2 | Bao nhiêu tin IT bị đăng lặp giữa các trang? So khớp nội dung có cần thiết hơn so khớp tiêu đề + công ty không? | WM1 dedup | Near-duplicate detection, MinHash/LSH |
| RQ3 | Học máy (PhoBERT + nhãn yếu) trích kỹ năng tốt hơn từ điển tới đâu, ở phần nào? Có dùng được trên trang khác với trang huấn luyện không? | WM2 | Web content mining, trích xuất thông tin, NER |
| RQ4 | Review công ty nói gì về từng khía cạnh (lương, OT, quản lý…)? Mô hình nhận ra lời chê tốt tới đâu? | WM3 | Opinion mining, ABSA |
| RQ5 | Chỉ từ danh sách kỹ năng, chưa có lịch sử người dùng, có gợi ý được việc phù hợp không? | WM5 | Recommender systems, cold start |
| RQ6 | Thị trường kỹ năng IT có cấu trúc gì: nhóm nghề nào, kỹ năng nào là trung tâm? | WM6 | Link analysis (PageRank), community detection |
| RQ7 *(tùy chọn)* | Mở rộng truy vấn bằng alias và tìm kiếm lai có giúp tìm tin đúng hơn BM25 không? | WM4 | Information retrieval, xếp hạng |

## 2. Từng công nghệ: vì sao dùng, đánh giá ra sao, rút ra được gì

Mỗi mục có cùng 5 phần:
- Dùng để làm gì
- Vì sao chọn, so với lựa chọn khác
- Đánh giá thế nào
- Insight đã có hoặc sẽ có
- Giúp gì cho sản phẩm JobLens

### 2.1 Thu thập: Scrapy + sitemap + JSON-LD (RQ1)

- **Dùng để:** lấy tin tuyển dụng TopCV theo sitemap; đọc khối JSON-LD `JobPosting` (chuẩn schema.org) thay vì bóc HTML.
- **Vì sao chọn:**
  - JSON-LD là dữ liệu có cấu trúc trang web tự công bố cho máy tìm kiếm, nên ổn định hơn bóc HTML khi giao diện đổi.
  - Sitemap cho danh sách tin đang mở mà không phải dò trang danh sách.
  - Scrapy có sẵn điều tiết tốc độ, tôn trọng robots.txt, thống kê mã HTTP. Selenium nặng và không cần thiết vì trang không phụ thuộc JavaScript.
- **Đánh giá:**
  - Độ chính xác parse theo trường trên 50 trang kiểm tay: `<...>`.
  - Recall bộ lọc PII: `<...>`.
  - Số phản hồi 429/403 mỗi đợt.
  - Tỷ lệ tin khớp schema `job_posting.v1`.
- **Insight đã có (số thật, đợt 1, 304 tin IT):**
  - Chỉ khoảng **4% tin trên TopCV là IT** (4/20 trang khi thử; ~44.000 tin đang mở trong sitemap). Muốn đủ dữ liệu IT thì phải lọc sớm theo URL và danh mục.
  - **44% tin IT ghi lương "Thỏa thuận"**, chỉ 55% có số. Thống kê lương từ tin đăng bị thiên lệch: chỉ thấy phần công ty chịu công khai.
  - Tag "Kỹ năng cần có" do nhà tuyển dụng tự gắn **lẫn nhiều kỹ năng mềm**: trong top 6 tag có "Giao tiếp" (14) và "Làm việc nhóm" (11). Không dùng thẳng tag làm nhãn kỹ năng cứng được; đây là lý do cần WM2.
  - **Bài học vận hành:** sự cố ngày 12/10 có 4.673/5.507 request bị HTTP 429, vì cơ chế tự điều tiết của Scrapy rút ngắn khoảng cách khi lỗi trả về nhanh. Sau đó spider dừng ngay khi gặp 429/403, giãn ≥ 3 giây, crawl theo đợt nhỏ. Crawl "lịch sự" phải được **đo** bằng mã HTTP, không chỉ cấu hình.
  - **Pháp lý định hình phạm vi:**
    - Điều khoản ITviec (mục 2.2, bản 01/07/2023) yêu cầu đồng ý trước bằng văn bản cho việc truy xuất, tải xuống nội dung, trừ sử dụng cá nhân hợp lý. robots.txt chỉ chặn `/subscriptions/new`. Kế hoạch ban đầu là chưa crawl cho tới khi được đồng ý.
    - **Thực tế (quyết định 2026-11-17: giữ ITviec):** đã crawl ITviec ở quy mô nhỏ (144 trang review, 536 tin, ≤ 1 request/3 giây, không đăng nhập, chỉ phần công khai). Đồng ý bằng văn bản: `<chưa có / ngày gửi email, ngày trả lời>`. Ý kiến giảng viên: `<...>`. Giới hạn tự đặt: chỉ dùng cho môn học; không công khai lại dữ liệu hay HTML thô; không commit lên git; demo chỉ hiện kết quả phân tích kèm link gốc, không đăng lại nguyên văn review; không lưu tên người review.
    - TopCV cho phép trang tin trong robots.txt và cấm đường dẫn CV, nên crawler chặn cứng các đường dẫn đó.
- **Giúp sản phẩm:** dữ liệu tin mới, có `date_posted`, cho phép thống kê theo thời gian. Bộ dữ liệu công khai VietJobs không có ngày đăng.

### 2.2 Đóng băng dữ liệu: snapshot Parquet + manifest

- **Dùng để:** mọi tập train/test dựa trên một snapshot bất biến, kèm mã băm danh sách tin (`ids_sha256`).
- **Vì sao chọn:** web thay đổi liên tục (tin hết hạn, bị sửa). Không đóng băng thì không tái lập được kết quả.
- **Đánh giá:** chạy lại lệnh ra cùng `ids_sha256` và cùng metric.
- **Insight:** sitemap chỉ chứa tin đang mở. Dữ liệu đợt 1 trải từ 17/08 đến 12/10/2026, nên muốn phân tích xu hướng dài hơn phải crawl đều theo thời gian.

### 2.3 Tập vàng: Label Studio + guideline + κ

- **Dùng để:** nhóm tự gán nhãn câu kỹ năng (WM2), cặp tin trùng (WM1), câu review (WM3) để làm tập đánh giá.
- **Vì sao chọn:** không có tập vàng tiếng Việt công khai cho các bài này. Label Studio chạy cục bộ nên dữ liệu không rời máy. Guideline có phiên bản để gán nhất quán. κ đo độ đồng thuận giữa hai người gán độc lập.
- **Đánh giá:** Cohen's κ trên ~10% mỗi tập (`<...>`); số câu hoặc cặp; số câu bị đánh dấu khó.
- **Insight đã có (dev WM2, 300 câu):**
  - **57% câu trong tin tuyển dụng không chứa kỹ năng cứng nào.** Phần lớn văn bản là nhiệm vụ, quyền lợi, yêu cầu mềm. Đây cũng là lý do không dùng accuracy theo token.
  - "Kỹ năng" là khái niệm **mơ hồ** hơn tưởng:
    - Guideline phải sửa 3 lần (0.1 → 0.3).
    - Các quy tắc mới đều về ranh giới: nhiệm vụ hay kỹ năng, chỉ số hay phương pháp, chức danh hay kỹ năng, lược từ.
    - Rà lại sau khi gán thì sửa 13/300 câu, 9 câu phải bàn.
  - **Gợi ý sẵn bằng máy làm lệch tập vàng:** dev được gợi ý bằng từ điển, và người gán giữ nguyên 20/59 gợi ý. Vì vậy tập test được gán **không có gợi ý**. Đây là quyết định phương pháp có thể trình bày như một phát hiện.
- **Giúp sản phẩm:** định nghĩa rõ "kỹ năng" chính là định nghĩa thứ app hiển thị và so khớp.

### 2.4 WM2: Từ điển alias → PhoBERT với nhãn yếu (RQ3)

- **Dùng để:** tìm span kỹ năng trong mô tả tin, chuẩn hóa về `skill_id` / ESCO.
- **Vì sao chọn:**
  - **Từ điển** là baseline minh bạch, rẻ, giải thích được.
  - **PhoBERT-base-v2** là mô hình ngôn ngữ tiếng Việt huấn luyện sẵn, phù hợp gán nhãn chuỗi. Nó yêu cầu tách từ trước (underthesea).
  - **Nhãn yếu** thay cho hàng chục nghìn câu gán tay. Lúc đầu nhãn yếu lấy từ tag kỹ năng của nhà tuyển dụng dò lại trong văn bản, sau đó thêm luật làm sạch theo guideline và self-training.
  - **LLM chỉ đóng vai người gán nhãn train, không chạy trong sản phẩm.** Mô hình LLM (`gpt-6-luna`) đọc guideline gán nhãn của nhóm rồi gán span cho câu train VietJobs; PhoBERT học từ các nhãn đó. Sản phẩm vẫn chỉ chạy PhoBERT trên CPU, nên không tốn chi phí API lúc dùng và không phụ thuộc dịch vụ ngoài khi chạy. Để tái lập, file nhãn LLM được giữ lại cùng dữ liệu.
- **Đánh giá:**
  - F1 thực thể strict (seqeval) trên test 1.000 câu TopCV; P/R tách riêng.
  - Recall riêng trên kỹ năng chưa thấy trong nhãn yếu.
  - Chênh lệch dev (VietJobs) và test (TopCV).
  - Bootstrap ghép cặp theo tin (1.000 lần), 3 seed. Mỗi thí nghiệm đăng ký trước cấu hình và quy tắc kết luận, rồi chấm test đúng một lần.
- **Insight đã có (test `skill_test1`, 1.000 câu TopCV):**

  | Hệ | P | R | F1 |
  |---|---|---|---|
  | Từ điển alias (baseline) | 0,742 | 0,315 | 0,442 |
  | PhoBERT, nhãn yếu từ tag | 0,705 | 0,469 | 0,562 |
  | PhoBERT, nhãn yếu self-training | 0,715 | 0,543 | 0,617 |
  | **PhoBERT, nhãn yếu do LLM gán theo guideline** | **0,725** | **0,734** | **0,730** |

  - Từ điển **gán đúng nhưng bỏ sót hơn 2/3 kỹ năng**. Bỏ sót thuộc hai loại: cụm tiếng Việt ("vận hành máy CNC", "phân khúc khách hàng") và tên công cụ hiếm ("Digiwin T100", "IBM MQ", "Katalon"). Danh sách cố định không theo kịp cách viết tin.
  - 46% span vàng là kỹ năng không có trong nhãn yếu từ tag. Từ điển bắt được 0% nhóm này, PhoBERT bắt được 19–25%: mô hình có học được ngữ cảnh chứ không chỉ học thuộc danh sách.
  - **Nút thắt của WM2 là chất lượng nhãn train, không phải mô hình.** Hai thí nghiệm sửa phía mô hình đều không cải thiện: học tiếp PhoBERT trên văn bản tin tuyển dụng (DAPT, 0,607) và giảm trọng số token O khi train (0,615, khoảng tin cậy chứa 0). Thay nhãn yếu bằng nhãn LLM theo guideline thì tăng +0,11 F1, khoảng tin cậy nằm trên 0 ở cả 3 seed, tăng cả P lẫn R.
  - Nhãn LLM vẫn là nhãn yếu: so với nhãn tay trên dev được F1 0,849 (nhãn yếu theo luật: 0,600). Chi phí gán khoảng 20.700 câu là dưới 1 USD.
  - Chênh dev (VietJobs) và test (TopCV): 0,797 so với 0,730. Mô hình học chủ yếu trên văn bản VietJobs vẫn giữ được phần lớn chất lượng trên trang TopCV.
- **Insight sẽ có:**
  - Lỗi còn lại nằm ở ranh giới hay ở việc không nhận ra (khoảng cách strict − partial).
  - Kỹ năng được yêu cầu nhiều nhất theo nhóm nghề (bảng nhu cầu kỹ năng đã có bản đầu, xem `experiments/results.md`).
- **Giúp sản phẩm:** trích kỹ năng từ tin và từ CV dán vào, dùng chung một bộ từ vựng. Đây là nền cho gợi ý việc (WM5), khoảng trống kỹ năng (UC013), thống kê nhu cầu kỹ năng.

### 2.5 WM1: Shingling + MinHash LSH (RQ2)

- **Dùng để:** tìm tin cùng một việc đăng trên nhiều trang hoặc đăng lại.
- **Vì sao chọn:**
  - So từng cặp tin là O(n²), không mở rộng được.
  - MinHash ước lượng độ giống Jaccard bằng chữ ký ngắn. LSH chỉ đem so những cặp có khả năng giống, gần tuyến tính theo số tin.
  - Baseline so tiêu đề + công ty (rapidfuzz) để xem nội dung có thêm giá trị không.
  - Embedding ngữ nghĩa để làm hướng mở rộng, vì tin trùng thường giống gần nguyên văn.
- **Đánh giá:**
  - P/R/F1 trên 200 cặp test, lấy mẫu phân tầng theo độ giống.
  - Recall của bước blocking LSH.
  - κ trên cặp.
  - Chọn ngưỡng trên 100 cặp dev.
- **Insight sẽ có:**
  - **Bao nhiêu % tin IT bị đăng lặp** giữa các trang hoặc trên cùng trang (`<...>`).
  - Tin trùng khác nhau ở đâu: lương, địa điểm, mô tả rút gọn.
  - Tiêu đề + công ty đã đủ chưa, hay phải so nội dung.
- **Giúp sản phẩm:** người dùng thấy một việc một lần; số liệu thống kê (đếm tin theo kỹ năng, theo công ty) không bị đếm trùng.

### 2.6 WM3: Từ điển cảm xúc → PhoBERT / ViSoBERT (RQ4)

- **Dùng để:** gán khía cạnh (lương, quản lý, văn hóa, đào tạo, văn phòng, OT) và cảm xúc cho từng câu review.
- **Vì sao chọn:**
  - Đánh giá mức câu theo khía cạnh cho thông tin cụ thể hơn điểm sao tổng ("lương tốt nhưng OT nhiều").
  - ViSoBERT huấn luyện trên văn bản mạng xã hội tiếng Việt, hợp với văn phong review.
  - Từ điển cảm xúc làm baseline.
  - Điểm sao theo khía cạnh (nếu nguồn có) làm nhãn yếu.
- **Đánh giá:**
  - F1 phát hiện khía cạnh.
  - Macro-F1 cảm xúc trên test 700 câu, chia theo công ty.
  - Ma trận nhầm lẫn.
  - Tương quan Spearman giữa kết quả và điểm sao.
- **Insight sẽ có:**
  - Khía cạnh nào bị chê nhiều nhất trong ngành IT (`<...>`).
  - Mô hình nhầm trung tính với tiêu cực ở đâu.
  - Tổng hợp từ mô hình có khớp điểm sao của người viết không.
- **Phụ thuộc:** toàn bộ WM3 dùng review công khai ITviec (144 review). Căn cứ sử dụng xem mục 2.1; nếu ITviec từ chối thì phải đổi nguồn và gán lại.
- **Giúp sản phẩm:** UC "xem công ty bị chê về gì" trước khi ứng tuyển.

### 2.7 WM5: Độ phổ biến → content-based (TF-IDF, trùng kỹ năng) (RQ5)

- **Dùng để:** gợi ý 10 tin cho một hồ sơ kỹ năng.
- **Vì sao chọn:**
  - Người dùng mới chưa có lịch sử (cold start), nên lọc cộng tác (ALS) không dùng được ngay. Content-based dùng chính kỹ năng do WM2 trích ra, và giải thích được ("trùng 4/6 kỹ năng").
  - Độ phổ biến là baseline tối thiểu.
- **Đánh giá:**
  - nDCG@10 trên 30 hồ sơ do người chấm, không biết phương pháp nào gợi ý.
  - Recall@10 trên log synthetic, chỉ là bổ trợ, vì log tự sinh dễ thiên vị phương pháp cùng công thức.
  - Coverage danh mục; tỷ lệ gợi ý có kỹ năng trùng.
- **Insight sẽ có:**
  - Chỉ từ kỹ năng đã gợi ý tốt tới đâu (`<...>`).
  - Gợi ý theo độ phổ biến bỏ lỡ gì.
  - Coverage cho thấy hệ thống có đưa người dùng tới nhiều loại việc không.
- **Giúp sản phẩm:** UC012 gợi ý việc làm có lý do, chạy được ngay cho người dùng mới.

### 2.8 WM6: Đồ thị đồng xuất hiện kỹ năng + PageRank + Louvain (RQ6)

- **Dùng để:** coi mỗi kỹ năng là một đỉnh; hai kỹ năng cùng xuất hiện trong một tin thì nối cạnh.
- **Vì sao chọn:**
  - PageRank đo mức "trung tâm": kỹ năng nối với nhiều kỹ năng quan trọng khác, chứ không chỉ xuất hiện nhiều.
  - Louvain tìm cộng đồng mà không cần biết trước số nhóm.
  - Đây là phần link analysis của môn, áp dụng trên đồ thị suy ra từ nội dung web thay cho đồ thị siêu liên kết.
- **Đánh giá:**
  - Modularity so với đồ thị ngẫu nhiên giữ bậc.
  - Kendall τ giữa xếp hạng PageRank và tần suất.
  - Người xem đặt tên và nhận xét các cụm.
- **Insight sẽ có:**
  - Các nhóm nghề tự hình thành (frontend, data, hạ tầng…) (`<...>`).
  - **Kỹ năng trung tâm khác kỹ năng phổ biến** ở đâu, ví dụ một công cụ chung như Git, SQL đứng cao về PageRank dù không đứng đầu về tần suất. Ví dụ này cần kiểm trên dữ liệu.
  - Kỹ năng nào là cầu nối giữa hai nhóm nghề.
- **Giúp sản phẩm:** gợi ý "nên học kỹ năng nào trước" (UC013): ưu tiên kỹ năng trung tâm trong cụm nghề người dùng nhắm tới.

### 2.9 WM4 (tùy chọn): BM25 → BM25 + alias → hybrid (RQ7)

- **Vì sao chọn:**
  - BM25 là chuẩn của tìm kiếm từ khóa.
  - Mở rộng alias xử lý cách viết khác nhau ("reactjs" / "React").
  - Embedding (bge-m3) bắt truy vấn theo nghĩa.
- **Đánh giá:** nDCG@10, MRR trên 50 truy vấn × top-20, người chấm 0–2 không biết phương pháp.
- **Insight sẽ có:** alias giúp truy vấn viết tắt tới đâu; hybrid có lợi với loại truy vấn nào.

### 2.10 mining-service: FastAPI

- **Dùng để:** đưa WM2 và WM5 vào app (dán CV → kỹ năng → gợi ý ngay).
- **Đánh giá:** độ trễ p95 ≤ 3 giây trên CPU; 100% test hợp đồng; không lưu văn bản CV.
- **Insight:** chi phí đưa mô hình vào dùng thật, tức chọn mô hình nào khi cân bằng độ chính xác với tốc độ.

## 3. Phương pháp đánh giá chung (để giảng viên tin các con số)

| Nguyên tắc | Làm thế nào | Tránh được gì |
|---|---|---|
| Tách dev/test trước khi làm mô hình | Tinh chỉnh chỉ trên dev; test chạy một lần khi đã chốt | Học thuộc tập test |
| Chia theo nhóm | Theo tin, theo công ty, theo cặp | Cùng một tin ở cả train và test |
| Nhãn yếu không làm test | Nhãn yếu chỉ để train | Chấm mô hình bằng chính lỗi của nhãn yếu |
| Test gán không có gợi ý máy | Dev có gợi ý, test thì không | Tập vàng thiên về baseline |
| Luôn có baseline | Từ điển / độ phổ biến / tiêu đề + công ty | Không biết mô hình hơn được bao nhiêu |
| κ trên ~10% | Hai người gán độc lập | Tập vàng là ý riêng một người |
| Bootstrap 95% + 3 seed | Kèm mọi chênh lệch | Gọi "tốt hơn" khi chỉ là may |
| Đăng ký trước | Ghi cấu hình, dự đoán và quy tắc kết luận vào `experiments/results.md` trước khi chạy; chấm test một lần | Chỉnh theo số test rồi chọn kết quả đẹp |
| Người chấm không biết phương pháp | WM4, WM5 | Ưu ái phương pháp mới |
| Phân tích ≥ 30 lỗi theo loại | Mỗi bài | Chỉ có con số, không biết vì sao |
| Tái lập | Snapshot + seed + lệnh + commit cho mọi số | Số không kiểm được |

## 4. Bài học xuyên suốt (dùng cho phần Thảo luận)

1. **Chất lượng và quyền sử dụng dữ liệu quyết định phạm vi nhiều hơn mô hình.**
   - Điều khoản ITviec yêu cầu đồng ý bằng văn bản; nhóm vẫn dùng dữ liệu công khai ở quy mô nhỏ cho học tập và phải nêu rõ điều này (mục 2.1, mục 5).
   - 44% tin ẩn lương làm thống kê lương lệch.
   - Tag của nhà tuyển dụng lẫn kỹ năng mềm.
2. **Định nghĩa nhãn là phần khó nhất của trích kỹ năng,** không phải mô hình. Guideline phải chốt nhiều quy tắc ranh giới mới gán nhất quán được.
3. **Công cụ hỗ trợ gán nhãn có thể làm lệch đánh giá** (gợi ý sẵn → precision dev bị đẩy lên). Vì vậy tách quy trình dev và test.
4. **Crawl lịch sự phải được kiểm chứng bằng số** (mã HTTP), vì cấu hình mặc định có thể làm điều ngược lại.
5. **Dữ liệu web lệch theo nguồn:** chủ yếu Hà Nội (199/304) và TP.HCM (70/304); chỉ tin đang mở; chỉ một trang. Mọi kết luận về "thị trường" phải nêu giới hạn này.
6. **Với trích kỹ năng, sửa nhãn train hiệu quả hơn sửa mô hình.** DAPT và đổi hàm loss không giúp; cho LLM gán nhãn train theo đúng guideline của tập vàng thì F1 test tăng từ 0,617 lên 0,730 với chi phí dưới 1 USD. Guideline viết kỹ cho người gán cũng dùng lại được cho máy gán.

## 5. Hạn chế và mối đe dọa với kết luận

- **Phần lớn nhãn do một người gán;** κ chỉ đo trên ~10%.
- **Log người dùng của WM5 là synthetic.** Kết luận chính dựa trên tập chấm tay nhỏ (30 hồ sơ).
- **Quyền sử dụng dữ liệu ITviec:** điều khoản mục 2.2 yêu cầu đồng ý bằng văn bản. Trạng thái xin phép: `<...>`. Mọi kết quả WM3 và phần ITviec của WM1 phụ thuộc vào điểm này.
- **Dữ liệu:** một đến hai trang, khoảng 2 tháng tin đang mở, chỉ ngành IT. Không suy rộng cho toàn thị trường.
- **Tập test WM2 lấy từ cùng snapshot với dữ liệu crawl,** nhưng chọn theo tin, không trùng tin train.
- **Dev WM2 có gợi ý từ điển,** nên số trên dev chỉ để chọn tham số, không để báo cáo.
- **Nhãn train WM2 phụ thuộc một dịch vụ LLM bên ngoài.** Chỉ một mô hình, gán một lần, chưa đo độ ổn định giữa các lần gán; dịch vụ có thể đổi mô hình nên tái lập dựa vào file nhãn đã lưu. Chỉ câu VietJobs (giấy phép mở, có trích dẫn) được gửi đi; câu crawl TopCV/ITviec và câu test không rời máy.
- **30/1.000 câu test trùng nguyên văn một câu train** (câu mẫu lặp giữa các tin). Đã chấm lại khi bỏ các câu này: kết luận không đổi (0,731 so với 0,620).

## 6. Gợi ý trình tự trình bày (10–15 phút)

1. Bài toán và 6 câu hỏi (RQ1–RQ6), mỗi câu ứng với một chủ đề của môn: 1 slide.
2. Dữ liệu: nguồn, pháp lý, crawl lịch sự, số liệu đợt 1, sự cố 429 và cách sửa: 2 slide.
3. Tập vàng và phương pháp đánh giá (bảng mục 3): 1 slide.
4. Mỗi bài WM1, WM2, WM3, WM5, WM6 một slide: phương pháp → bảng baseline vs mô hình (có khoảng tin cậy) → **một insight** → lợi ích cho sản phẩm.
5. Demo: dán một tin mới → kỹ năng → gợi ý việc → khía cạnh review của công ty.
6. Bài học và hạn chế (mục 4, 5): 1 slide.
