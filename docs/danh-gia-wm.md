# Khung đánh giá – Mining Vietnamese Job Postings for Skill Demand and Company Reviews

*Cập nhật 23/11/2026. Nguồn cho chương "Thực nghiệm" và "Thảo luận" của báo cáo và cho buổi trình bày. Chỉ ghi các so sánh chính thức (phương pháp so với baseline trên tập kiểm tra); các phép thử đã bỏ không đưa vào đây. Số chưa đo để `<...>`.*

## 1. Câu hỏi nghiên cứu

Mỗi kỹ thuật được chọn để trả lời một câu hỏi cụ thể về dữ liệu tuyển dụng IT tiếng Việt.

| Mã | Câu hỏi | Bài | Chủ đề web mining |
|---|---|---|---|
| RQ1 | Thu thập được tin tuyển dụng tiếng Việt lịch sự, đúng quy định mà vẫn đủ chất lượng để khai phá không? | Thu thập | Web crawling, dữ liệu có cấu trúc trên web |
| RQ2 | Mô hình học máy trích kỹ năng tốt hơn từ điển ở đâu, và nguồn nhãn huấn luyện nào quyết định chất lượng? | T1 | Web content mining, trích xuất thông tin |
| RQ3 | Review công ty nói gì về từng khía cạnh, và nhận ra lời chê khó đến đâu? | T2 | Opinion mining, ABSA |
| RQ4 | Chỉ từ danh sách kỹ năng, chưa có lịch sử người dùng, có gợi ý được tin phù hợp không? | T3 | Recommender systems, cold start |
| RQ5 | Thị trường kỹ năng IT có cấu trúc gì: nhóm nghề nào, kỹ năng nào ở trung tâm? | Phân tích cấu trúc | Phân tích cấu trúc, phát hiện cộng đồng |

## 2. Từng bài: vì sao dùng, đánh giá ra sao, rút ra được gì

### 2.1 Thu thập (RQ1)

- **Dùng để:** lấy tin và review công khai từ các nguồn tuyển dụng (ví dụ TopCV, ITviec): đọc danh sách tin theo sitemap, đọc khối dữ liệu có cấu trúc `JobPosting` (schema.org) trong trang thay vì bóc HTML.
- **Vì sao chọn:** dữ liệu có cấu trúc do trang tự công bố ổn định hơn bóc HTML khi giao diện đổi; sitemap cho danh sách tin đang mở; Scrapy có sẵn điều tiết tốc độ, tôn trọng robots.txt và thống kê mã HTTP.
- **Đánh giá:** độ chính xác parse theo trường trên mẫu kiểm tay (`<...>`); recall bộ lọc dữ liệu cá nhân (`<...>`); số phản hồi 429 và 403 mỗi đợt.
- **Rút ra:**
  - Chỉ một phần nhỏ tin trên TopCV là IT, nên phải lọc sớm theo đường dẫn và danh mục.
  - Gần nửa tin IT ghi lương "Thỏa thuận", nên thống kê lương từ tin đăng bị lệch.
  - Tag "Kỹ năng cần có" do nhà tuyển dụng gắn lẫn nhiều kỹ năng mềm, nên không dùng thẳng làm nhãn kỹ năng.
  - Crawl lịch sự phải được đo bằng mã HTTP, không chỉ bằng cấu hình: một đợt đầu bị trả 429 ở phần lớn request vì cơ chế tự điều tiết rút ngắn khoảng cách khi lỗi trả về nhanh. Sau đó spider dừng ngay khi gặp 429 hoặc 403, giãn khoảng cách và crawl theo đợt nhỏ.
  - Điều khoản của ITviec yêu cầu đồng ý bằng văn bản cho việc truy xuất nội dung. Nhóm chỉ crawl phần công khai ở quy mô nhỏ, không đăng nhập, chỉ dùng cho học tập và không đăng lại dữ liệu. Trạng thái xin phép: `<...>`.
  - Quy mô thu thập nhỏ: 352 tin TopCV (ba đợt) và 536 tin ITviec khác nhau, tổng 888 tin; 144 review từ 144 công ty (mỗi công ty chỉ hiện công khai khoảng một review). Nguyên nhân chính là TopCV trả 429 rất sớm: đợt ngày 12/10 được khoảng 800 request, đợt ngày 18/11 chỉ 58 request. Với ngưỡng đó, thu thập đủ lớn cần nhiều tuần, không kịp trong thời gian của đề tài.
  - Mở rộng sang trang khác bị giới hạn bởi điều khoản và cơ chế chống bot (kiểm tra ngày 23/11): một số trang cấm robot hoặc scraper trong điều khoản sử dụng, một số trang hiện thử thách "xác nhận không phải robot" hoặc trả 403. Nhóm không dùng dữ liệu từ các trang này. Hướng còn lại là xin phép bằng văn bản hoặc dùng dữ liệu công khai có giấy phép rõ.

### 2.2 Đóng băng dữ liệu

- **Dùng để:** mọi tập huấn luyện và kiểm tra dựa trên một bản chụp bất biến theo ngày, kèm mã băm danh sách tin.
- **Vì sao chọn:** tin hết hạn và bị sửa liên tục; không đóng băng thì không tái lập được kết quả.
- **Đánh giá:** chạy lại cho ra cùng mã băm và cùng chỉ số.

### 2.3 Tập gán nhãn

- **Dùng để:** nhóm tự gán nhãn câu kỹ năng (T1), câu review (T2), điểm phù hợp giữa hồ sơ và tin (T3) làm tập đánh giá.
- **Vì sao chọn:** không có tập vàng tiếng Việt công khai cho các bài này. Gán trên công cụ chạy cục bộ nên dữ liệu không rời máy; guideline viết thành văn bản để gán nhất quán; độ đồng thuận giữa hai người đo bằng Cohen's κ trên khoảng 10% mỗi tập.
- **Rút ra:**
  - Hơn một nửa câu trong tin tuyển dụng không chứa kỹ năng cứng nào, nên không dùng accuracy theo token.
  - "Kỹ năng" là khái niệm mơ hồ hơn dự kiến; guideline phải sửa nhiều lần, chủ yếu ở quy tắc ranh giới (nhiệm vụ hay kỹ năng, chức danh hay kỹ năng).
  - Gợi ý sẵn bằng máy làm lệch tập vàng, vì người gán thường giữ nguyên gợi ý. Vì vậy tập kiểm tra được gán không có gợi ý.

### 2.4 T1: trích kỹ năng (RQ2)

- **Dùng để:** tìm đoạn nói về kỹ năng trong mô tả và yêu cầu của tin, chuẩn hóa về một tên chuẩn qua từ điển alias.
- **Vì sao chọn:**
  - Từ điển là baseline minh bạch, rẻ, giải thích được.
  - PhoBERT-base-v2 là mô hình ngôn ngữ tiếng Việt huấn luyện sẵn, phù hợp gán nhãn chuỗi.
  - Nhãn yếu thay cho hàng chục nghìn câu gán tay. Nguồn nhãn được thử theo thứ tự tăng dần mức giám sát: tag của nhà tuyển dụng, thêm luật và self-training, rồi nhãn do LLM gán theo đúng guideline của tập kiểm tra.
  - LLM chỉ đóng vai người gán nhãn cho dữ liệu huấn luyện công khai, không chạy khi dùng mô hình.
- **Đánh giá:** F1 thực thể khớp chặt (seqeval strict) trên 1.000 câu từ tin đã crawl; báo cả precision và recall; bootstrap ghép cặp theo tin, 3 seed; mỗi thí nghiệm đăng ký trước và chấm tập kiểm tra một lần.
- **Kết quả:**

  | Hệ | Precision | Recall | F1 |
  |---|---|---|---|
  | Baseline: từ điển alias | 0,742 | 0,315 | 0,442 |
  | PhoBERT, nhãn yếu từ tag và từ điển | 0,705 | 0,469 | 0,562 |
  | PhoBERT, nhãn yếu thêm luật và self-training | 0,715 | 0,543 | 0,617 |
  | **PhoBERT, nhãn do LLM gán theo guideline** | **0,725** | **0,734** | **0,730** |

- **Rút ra:** từ điển gán đúng nhưng bỏ sót hơn hai phần ba kỹ năng, gồm cụm tiếng Việt và tên công cụ hiếm. Nút thắt là chất lượng nhãn huấn luyện chứ không phải mô hình: nhãn LLM tăng F1 thêm 0,109 đến 0,117 so với nhãn self-training, khoảng tin cậy trên 0 ở cả ba seed, tăng cả precision lẫn recall. Lỗi còn lại chủ yếu ở ranh giới đoạn (F1 khớp một phần 0,811 so với 0,729 khớp chặt).

### 2.5 T2: khai phá quan điểm theo khía cạnh (RQ3)

- **Dùng để:** gán khía cạnh (lương và phúc lợi, đào tạo, quản lý, cân bằng công việc, văn hóa, văn phòng) và cực tính cho từng câu review.
- **Vì sao chọn:** mức câu cho thông tin cụ thể hơn điểm sao tổng ("lương tốt nhưng OT nhiều"). Từ điển cảm xúc là baseline; luật dùng phần của review (điều thích, góp ý) là baseline mạnh thứ hai để biết mô hình học được gì ngoài bố cục trang.
- **Đánh giá:** F1 khía cạnh, macro-F1 giữa tích cực và tiêu cực, recall của lời chê, trên 348 câu kiểm tra chia theo review; tương quan Spearman giữa kết quả và điểm sao theo khía cạnh, là tín hiệu mà người gán không tạo ra.
- **Kết quả:**

  | Hệ | F1 khía cạnh | Macro-F1 cực tính | Recall lời chê |
  |---|---|---|---|
  | Baseline: từ điển cảm xúc | 0,753 | 0,518 | 0,424 |
  | Luật: cực tính theo phần của review | 0,753 | 0,583 | n/a |
  | **Lai: từ điển cho khía cạnh, hồi quy logistic cho cực tính** | **0,753** | **0,590** | **0,533** |

- **Rút ra:** review công khai gần như toàn tích cực nên nhãn suy từ điểm sao gần như không có lời chê. Mô hình lai hơn từ điển (+0,072, CI95 [+0,027; +0,120]) nhưng chưa hơn luật theo phần review, cho thấy bố cục trang tiết lộ nhiều. Đối chiếu với điểm sao: tương quan mức review 0,329 cho mô hình lai và 0,239 cho luật (chênh +0,090, CI95 [+0,022; +0,161]), tức mô hình lai bắt được nội dung quan điểm mà bố cục không có.

### 2.6 T3: gợi ý tin theo kỹ năng (RQ4)

- **Dùng để:** gợi ý 10 tin cho một hồ sơ kỹ năng.
- **Vì sao chọn:** người dùng mới chưa có lịch sử nên lọc cộng tác chưa dùng được; phương pháp dựa trên nội dung dùng kỹ năng từ T1 và giải thích được. Độ phổ biến là baseline tối thiểu.
- **Đánh giá:** nDCG@10 và Precision@10 (tỷ lệ tin trong top 10 có điểm ≥ 1) trên 20 hồ sơ kỹ năng; kết quả top 10 của bốn phương pháp được gộp lại và chấm mù theo thang 0, 1, 2 (503 cặp hồ sơ và tin); bootstrap ghép cặp theo hồ sơ.
- **Kết quả:**

  | Phương pháp | nDCG@10 | Precision@10 | ΔnDCG so với baseline [CI95] |
  |---|---|---|---|
  | Baseline: tin xem nhiều nhất | 0,061 | 0,065 | n/a |
  | Trùng kỹ năng, trọng số IDF | 0,775 | 0,740 | +0,714 [+0,615; +0,799] |
  | **TF-IDF giữa hồ sơ và nội dung tin** | **0,837** | **0,810** | +0,776 [+0,665; +0,862] |
  | TF-IDF cộng 0,1 lần độ phổ biến | 0,812 | 0,780 | +0,752 [+0,659; +0,821] |

- **Rút ra:** cả ba phương pháp dựa trên nội dung vượt xa baseline nhưng không phân biệt được với nhau (TF-IDF trừ trùng kỹ năng: +0,062, CI95 [−0,047; +0,172]); mỗi cách thắng ở những hồ sơ khác nhau. Chưa có log hành vi thật nên không so được với lọc cộng tác. Chỉ tin trong tập đã chấm được tính nên giá trị tuyệt đối nghiêng cao.

### 2.7 Phân tích cấu trúc: đồ thị đồng xuất hiện kỹ năng (RQ5)

- **Dùng để:** mỗi kỹ năng là một đỉnh, hai kỹ năng cùng xuất hiện trong một tin thì nối cạnh. PageRank đo mức trung tâm; Louvain tìm cộng đồng mà không cần biết trước số nhóm. Đây là phân tích cấu trúc áp trên đồ thị suy ra từ nội dung web thay cho đồ thị siêu liên kết.
- **Đánh giá:** modularity so với đồ thị ngẫu nhiên giữ nguyên bậc; xem xét định tính các cụm.
- **Kết quả:** đồ thị dựng từ kỹ năng do T1 trích, chỉ giữ cạnh có NPMI ≥ 0,3, còn 145 kỹ năng và 558 cạnh. Louvain chia thành 8 cộng đồng với modularity 0,517, so với 0,305 ở đồ thị ngẫu nhiên giữ nguyên bậc. Các cộng đồng ứng với nhóm nghề đọc ra được, ví dụ backend Java, cloud và DevOps, học máy.

### 2.8 Dịch vụ HTTP

- **Dùng để:** đưa trích kỹ năng và gợi ý thành hai điểm vào của một dịch vụ.
- **Đánh giá:** độ trễ p95 ≤ 3 giây trên CPU; không lưu văn bản đầu vào.
- **Kết quả:** với mô hình PhoBERT trên CPU 2 luồng, p50 0,07 giây, p95 0,21 giây, tối đa 0,35 giây mỗi yêu cầu.

## 3. Phương pháp đánh giá chung

| Nguyên tắc | Làm thế nào | Tránh được gì |
|---|---|---|
| Tách dev và test trước khi làm mô hình | Tinh chỉnh chỉ trên dev; test chấm một lần khi đã chốt | Học thuộc tập test |
| Chia theo nhóm | Theo tin, theo công ty, theo review | Cùng một tin ở cả train và test |
| Nhãn yếu và nhãn LLM không làm test | Chỉ dùng để huấn luyện | Chấm mô hình bằng chính lỗi của nhãn |
| Test gán không có gợi ý máy | Dev có gợi ý, test thì không | Tập vàng thiên về baseline |
| Luôn có baseline | Từ điển, độ phổ biến | Không biết mô hình hơn bao nhiêu |
| κ trên khoảng 10% | Hai người gán độc lập | Tập vàng là ý riêng một người |
| Bootstrap 95% và 3 seed | Kèm mọi chênh lệch | Gọi "tốt hơn" khi chỉ là may |
| Đăng ký trước | Ghi cấu hình và quy tắc kết luận trước khi chạy; chấm test một lần | Chỉnh theo số test rồi chọn kết quả đẹp |
| Người chấm không biết phương pháp | T3 | Ưu ái phương pháp mới |
| Tái lập | Bản chụp dữ liệu, seed, lệnh và commit cho mọi số | Số không kiểm được |

## 4. Bài học xuyên suốt

1. **Chất lượng và quyền sử dụng dữ liệu quyết định phạm vi nhiều hơn mô hình.** Điều khoản của trang nguồn, lương bị ẩn và tag lẫn kỹ năng mềm đều giới hạn những gì kết luận được.
2. **Định nghĩa nhãn là phần khó nhất của trích kỹ năng,** không phải mô hình. Guideline phải chốt nhiều quy tắc ranh giới mới gán nhất quán được.
3. **Công cụ hỗ trợ gán nhãn có thể làm lệch đánh giá.** Gợi ý sẵn đẩy precision của tập dev lên, nên tập kiểm tra gán không có gợi ý.
4. **Crawl lịch sự phải kiểm chứng bằng số** (mã HTTP), vì cấu hình mặc định có thể làm điều ngược lại.
5. **Dữ liệu web lệch theo nguồn:** chủ yếu Hà Nội và TP.HCM, chỉ tin đang mở, chỉ một hai trang. Mọi kết luận về "thị trường" phải nêu giới hạn này.
6. **Với trích kỹ năng, sửa nhãn huấn luyện hiệu quả hơn sửa mô hình.** Cho LLM gán nhãn huấn luyện theo đúng guideline của tập kiểm tra tăng F1 từ 0,617 lên 0,730 với chi phí dưới 1 USD. Guideline viết kỹ cho người gán dùng lại được cho máy gán.
7. **Bố cục trang có thể thay cho nội dung.** Ở review, phần "điều thích" và "góp ý" đoán được cực tính khá tốt; baseline theo bố cục là phép kiểm tra cần có.

## 5. Hạn chế

- Phần lớn nhãn do một người gán; κ chỉ đo trên khoảng 10% mỗi tập.
- T3 chưa có log hành vi thật; kết luận dựa trên 20 hồ sơ do nhóm soạn và chấm mù, tập tin để chấm lấy từ một bản chụp.
- Quyền sử dụng dữ liệu ITviec: điều khoản yêu cầu đồng ý bằng văn bản, trạng thái `<...>`. Kết quả T2 và phần ITviec của thu thập phụ thuộc vào điểm này.
- Quy mô crawl nhỏ: 888 tin từ hai trang, 144 review từ 144 công ty (mỗi công ty chỉ hiện công khai khoảng một review). Tập kiểm tra T1 (1.000 câu) lấy từ một đợt crawl TopCV; chưa có tập kiểm tra từ trang thứ hai nên chưa biết mô hình lệch nguồn đến đâu.
- Dữ liệu từ một đến hai trang, khoảng hai tháng tin đang mở, chỉ ngành IT; không suy rộng cho toàn thị trường. Các trang tuyển dụng khác bị loại vì điều khoản hoặc chống bot.
- Review công khai gần như toàn tích cực nên ít ví dụ lời chê để đánh giá. Trong 144 review, 73 review điểm 5, 57 review điểm 4, 14 review điểm 3, không có review dưới 3 sao. Trên một mẫu thăm dò 16 công ty, các review bị làm mờ khi chưa đăng nhập (không crawl) có cả điểm 1 và 2 còn review công khai thì không, nên phần lời chê của tập crawl chủ yếu là góp ý nhẹ trong review điểm cao. Số nhãn lời chê của từng khía cạnh trong tập kiểm tra T2 rất ít (chỉ vài nhãn cho văn hóa và văn phòng), nên chỉ báo cáo F1 của lớp tiêu cực với những khía cạnh đủ nhãn.
- Nhãn huấn luyện T1 phụ thuộc một dịch vụ LLM bên ngoài: một mô hình, gán một lần, chưa đo độ ổn định giữa các lần gán. Chỉ câu từ bộ dữ liệu công khai được gửi đi; câu crawl và câu kiểm tra không rời máy.
- Một số câu kiểm tra T1 trùng nguyên văn câu huấn luyện (câu mẫu lặp giữa các tin); đã chấm lại khi bỏ các câu này, kết luận không đổi.

## 6. Gợi ý trình tự trình bày (10 đến 15 phút)

1. Bài toán và các câu hỏi nghiên cứu, mỗi câu ứng với một chủ đề web mining: 1 slide.
2. Dữ liệu: nguồn, crawl lịch sự, đặc điểm tin và review: 2 slide.
3. Tập gán nhãn và phương pháp đánh giá (bảng mục 3): 1 slide.
4. Mỗi bài T1, T2, T3 một slide, thêm một slide cho đồ thị kỹ năng: phương pháp, bảng baseline so với phương pháp chính (có khoảng tin cậy), một điều rút ra.
5. Demo hệ thống gợi ý: nhập hồ sơ, xem kỹ năng trích được, nhận 10 tin kèm kỹ năng khớp và còn thiếu, xem tóm tắt khía cạnh của công ty.
6. Bài học và hạn chế: 1 slide.
