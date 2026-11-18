# Nhật ký thay đổi – Web-mining-joblens

Chỉ ghi sự kiện đáng nhớ: đổi hợp đồng hoặc file cấu hình chung, ghép hệ thống, chốt số liệu, quyết định quan trọng. Việc thường ngày đã có lịch sử git. Mục mới đặt trên cùng, vài dòng là đủ – xem [repo-routing](https://github.com/BD-WM-SA-D/joblens/blob/main/docs/repo-routing.md), mục Nhật ký.

## 2026-11-18 · Hoang Le

- **Chốt số WM2 chính thức: nhãn yếu v3, F1 0,617 trên TEST.** Chọn v3 trước khi chấm (dev 0,644 ± 0,006 so với v2 0,642 ± 0,030), chấm một lần trên `skill_test1`. Ba seed 0,616/0,618/0,617 (lệch 0,001); từ điển 0,442; ΔF1 +0,174…+0,176, CI ghép cặp theo tin trong [+0,128; +0,224], p = 0,000. Mức tăng so với v1 (0,562) nằm gần hết ở recall (0,469 → 0,543). Đã ghi mục `skill-extractor` vào `models.yaml`. Ghép thêm từ điển không còn giúp (0,615).
- **WM3 có kết quả dương dưới một đích không do người gán tạo ra.** Phép đo mới `absa/company_eval.py`: đối chiếu đầu ra ABSA với điểm sao ITviec (1.241 bản ghi, 1.100 review bị che, mỗi bản ghi có sao 5 khía cạnh). Mức review (289 ô / 99 review ngoài dev): lai 0,329 so với luật `section` 0,239, **Δρ = +0,090, CI95 [+0,022; +0,161], p = 0,005**. Mức công ty, đích là sao của review bị che (278 ô / 96 công ty): từ điển **−0,052** (CI chứa 0, tức không mang tín hiệu mức công ty), `section` 0,154, lai 0,196; lai so với từ điển Δρ = +0,247, p = 0,000, nhưng lai so với `section` thì CI chứa 0. Kết luận "phần do học là không đáng kể" chỉ đúng với phép đo mức câu trên nhãn người – đã sửa lại trong `results.md` và `models.yaml`.
- **Bảng nhu cầu kỹ năng đầu tiên** (`experiments/skill_demand.py`), là lời hứa trung tâm của đề tài mà trước nay chưa có số nào. Bốn bảng + bề rộng ngành trên VietJobs đủ bộ (48.092 tin / 16 ngành). Hai điều đáng ghi: (1) **thiên lệch nguồn lớn hơn mọi khác biệt giữa các mô hình** – AI 27,2% ở TopCV so với 45,5% ở ITviec và 14,2% ở VietJobs, nên không được báo một con số gộp; (2) **không có xu hướng thời gian** khi tách theo nguồn (TopCV 09→10 phẳng) – đường "AI tăng 27% → 45%" của bản gộp chỉ là chuyển nguồn. Phát hiện phụ: ở cỡ 48.092 tin mới lộ lỗi từ điển alias một chữ (`R`, `C`, `Express` bắt nhầm hàng loạt).
- **Crawl TopCV bị 429 sau 58 request, giả định ngân sách crawl sai.** `--max-sitemaps 60 --max-jobs 400` cho 60 request (58×200, 2×429), spider tự dừng sau 221 giây, được 21 tin IT mới (331 → 352 tin). So với 12/10 (429 sau ~800 request) thì ngưỡng của TopCV thấp hơn một bậc: ngân sách thật có thể chỉ **50–60 request/ngày**, nên mục tiêu "đủ 1.800 tin IT" cần ~30 ngày và **không khả thi** trước hạn. Lần tới phải đo ngưỡng (`DOWNLOAD_DELAY` 10 giây, `--max-jobs 60`) trước khi hứa. Phần cần *bề rộng* chuyển sang VietJobs (đã có trên máy, giấy phép rõ); VietJobs vẫn không được dùng làm tập test.
- Thêm cờ `--skip-sitemaps` cho spider TopCV để chia việc đọc 220 sitemap theo nhiều ngày (có test).
- **Chưa làm, còn mở:** ESCO (cột `esco_uri` trong `skill_alias.csv` rỗng toàn bộ → `canonical_id` hiện không phải ESCO như hợp đồng ghi); chạy lại mọi số trên commit sạch + tag `report-wm-v1`; căn cứ pháp lý ITviec (đã gửi xin phép, chờ trả lời – `docs/danh-gia-wm.md` mục 2.1 vẫn ghi "chưa crawl ITviec", phải sửa cho khớp thực tế).

AI: Claude Code (Claude Opus 5) – chấm WM2 v3, phép đo WM3 theo điểm sao, bảng nhu cầu kỹ năng, cờ `--skip-sitemaps`; <người kiểm tra> chưa kiểm tra

- **Guideline WM1 0.2 và chấm lại.** Gán lại mù 47 cặp (project 12), đổi 4 nhãn, trùng 15 → 13. Báo cả hai bộ số: v1 F1 0,522 → 0,455; v2 F1 0,667 → 0,645; ΔF1 v2 − v1 +0,191 CI [+0,014; +0,369] (nhãn 0.1: CI chứa 0). Chênh lệch chủ yếu do đổi nhãn hai cặp MB Bank, không do hệ.
- **κ WM1 = 0,733, CI [0,493; 0,933]** trên 30 cặp làm giàu cặp trùng (Bốp, project 11). 4 cặp lệch, cả 4 là người 1 gán "trùng" còn người 2 "không trùng" (khác dải cấp bậc, khác ngôn ngữ yêu cầu, tiêu đề lệch). Cần chốt guideline 0.2 rồi chấm lại.
- **Chốt số WM1 trên 300 cặp** (15 trùng, 4 khác trang; một người gán, chưa có κ). baseline P 1,000 R 0,333 F1 0,500; MinHash J ≥ 0,5 F1 0,419; gộp hai tầng P 0,387 R 0,800 F1 0,522 (CI [0,324; 0,679]). 19/19 lỗi báo nhầm là hai tin khác vị trí của cùng công ty dùng chung khung mô tả. Bảng mẫu đã sửa giới hạn lặp tin/công ty trước khi gán xong (45 cặp đã gán giữ nguyên).
- **Dedup v2 (đăng ký trước, chạy một lần):** tiêu đề mềm + cắt khung công ty. F1 0,522 → 0,667, ΔF1 +0,145 CI [−0,020; +0,304] – chưa chắc chắn. Báo nhầm 19 → 7, khác trang bắt 4/4. Lỗi mới: ở công ty ít tin, chính hai tin trùng bị coi là khung và bị cắt (GON TECH J 0,79 → 0,00).

## 2026-11-17 · Hoang Le

- **Giữ dữ liệu ITviec** (144 review, 536 tin). Điều khoản ITviec mục 2.2 yêu cầu đồng ý bằng văn bản; trạng thái xin phép `<...>`. Ghi rõ căn cứ và giới hạn tự đặt trong `docs/danh-gia-wm.md` mục 2.1 và mục 5. Việc tiếp: gửi email xin phép (nếu chưa gửi), hỏi giảng viên, sửa `02-du-lieu.md` / `11-rui-ro…` bên repo `joblens` cho khớp thực tế.
- **Sửa sau phản biện.** Một bản phản biện vai người chấm (cục bộ) chỉ ra chỗ đo sai và phát biểu quá; bảng đầy đủ ở đầu `experiments/results.md`, mục "Sửa sau phản biện".
- **WM5 có lỗi thật, đổi số chính thức.** Bộ sinh log dồn 74% lượt xem vào ngày cuối (`min(..., last_day)`) và hàm chia đưa cả ngày đó sang test: "chia 70/30" thực tế là 26/74. Sửa cả hai, sinh log v2 (`reco_events_v2`, chia 75/25). content-tfidf nDCG@10 **0.181 → 0.071**, popularity 0.030 → 0.015; thứ tự các chiến lược giữ nguyên.
- **WM3:** xác nhận người gán nhìn thấy `section` trên Label Studio – chưa loại được giả thuyết nhãn suy từ `section`, cần lô mù. Bỏ `section` khỏi mô hình lai: dev 0.770 → 0.709 (từ điển 0.605). CV giờ chia fold theo review (0.770 → 0.769). κ lớp `negative` chỉ 0.657, CI [0.187; 1.000]; bỏ chữ "almost perfect".
- **WM2 và WM6 đứng vững khi đo chặt hơn:** bootstrap theo tin vẫn không chứa 0; 46% span vàng chưa có trong nhãn yếu và PhoBERT bắt được 19–25% số đó (từ điển 0%). PPR hơn phép đếm ở Recall@10 (+0.040, CI [+0.021; +0.059]) nhưng không hơn ở MRR.
- **Còn mở, cần nhóm quyết:** lô mù WM3, căn cứ pháp lý dữ liệu ITviec, một bản nhãn TEST WM3 làm chuẩn, chạy lại trên commit sạch.
- **Bắt đầu gán WM1 dedup** (project Label Studio 10, 300 cặp). Bỏ trường `stratum` khỏi task: Label Studio hiện mọi trường trong `data` ở bảng danh sách nên người gán thấy được cặp nào do thuật toán đề xuất; tầng lấy mẫu giữ trong manifest, khớp lại bằng `index`. Đã sửa `annotation/sample_dedup_pairs.py` và thêm test chặn.
- **Làm WM6 (đồ thị kỹ năng), chốt số.** Đồ thị đồng xuất hiện trên 867 tin (TopCV + ITviec), 163 đỉnh. Hai kết quả âm: (1) PageRank tương quan Spearman 0.986 với bậc có trọng số, top-10 trùng 10/10 nên **không thêm tri thức gì** trên đồ thị đồng xuất hiện đối xứng; (2) trên đồ thị thô (mật độ 0.27) modularity Q = 0.158 **không phân biệt được với đồ thị ngẫu nhiên giữ bậc** (0.148 ± 0.012, 9/50 lần ngẫu nhiên còn cao hơn).
- **Kết quả dương sau khi lọc cạnh theo NPMI ≥ 0.3:** 8 cụm, Q = **0.515** so với ngẫu nhiên 0.278 ± 0.011 (z = 22.1, 0/100 lần vượt), ổn định giữa 5 seed NMI 0.83–0.96. Tám cụm đọc ra được: BA/sản phẩm, frontend, backend Java, DevOps/cloud, ML, hệ thống/mạng, ERP/BI, mobile. Dựng lại bằng PhoBERT WM2 cho Q = 0.517 và phân hoạch trùng NMI 0.742 → kết luận không phụ thuộc bộ trích kỹ năng.
- **Ngưỡng NPMI chọn theo độ ổn định, không theo Q** (Q tăng đơn điệu theo ngưỡng nên chọn theo Q là chọn theo chính số sắp báo cáo). Tiêu chí là khoảng cách NMI so với mốc gán cụm ngẫu nhiên, đỉnh ở 0.3; ngưỡng cao hơn làm đồ thị vỡ vụn khiến NMI tăng giả (mốc ngẫu nhiên lên 0.46 ở ngưỡng 0.5).
- **Sửa kết luận PageRank của WM6.** Số 0.986 đo với trọng số là *số tin* – đó là lựa chọn sai, không phải tính chất của PageRank. Đổi sang trọng số NPMI thì tương quan với số tin rụng còn **0.689** và top-10 đổi hẳn (`AI`, `API`, `SQL` rơi ra; `Docker`, `PostgreSQL`, `RESTful API`, `Kafka` vào). Vẫn còn 0.898 với bậc có trọng số, nên kết luận âm được giữ nhưng phát biểu lại: PageRank toàn cục không hơn bậc có trọng số **trên cùng trọng số đó**. Đồ thị có hướng theo `P(v|u)` cũng không cứu được (0.983 với bậc vào, top-10 không đổi vị trí nào).
- **PageRank cá nhân hoá thắng phép đếm, mức vừa phải.** Bài đoán kỹ năng bị che trên tin thật, đồ thị dựng chỉ trên nửa train (`graph/recommend.py`): Recall@10 `popular` 0.358 → `count` 0.461 → `count-npmi` 0.489 → **`ppr` 0.529**, trung bình 4 lần chia. Δ so với `count-npmi` dương **4/4 lần** ở Recall@10 nhưng chỉ 3/4 ở MRR. `alpha` phải hạ 0.85 → **0.35**; để nguyên mặc định của networkx thì PPR thua cả `count`. Hai tham số chọn trên seed 1, số báo cáo đo trên seed 2–5.
- **Cụm phụ thuộc một phần vào nguồn:** chia hai nửa theo nguồn cho NMI 0.476, thấp hơn mốc chia ngẫu nhiên 0.615. Chia theo thời gian **không đọc được** vì hai snapshot lệch nhau về thời gian nên gần như chia theo nguồn.

- **Gán xong 300 câu TEST của WM3** (project Label Studio 7). 293 câu tính điểm, 331 cặp (khía cạnh, cực): 251 positive, 68 negative, 12 neutral.
- **Chốt số sơ bộ trên TEST:** khía cạnh F1 0.731; macro theo ô chỉ pos/neg 0.505 (từ điển + luật đề nghị) so với 0.536 (nhãn yếu). Luật đề nghị giữ lại: recall `negative` 0.191 → 0.412.
- **Dev đã bị dùng để sửa từ điển nên không còn dùng để đo:** khía cạnh F1 dev 0.933 vs test 0.731. Từ điển v2 thêm 50 cụm lấy từ chính các câu khó của lô dev. Con số báo cáo là của TEST.
- **Guideline lên 0.2.2:** bản 0.2 tự mâu thuẫn về chữ "môi trường" (mục 2c nói không gán, ví dụ mục 5 lại gán `culture_fun`). Chốt "môi trường + từ đánh giá chung" → `culture_fun`. Căn cứ: 29/35 câu TEST có chữ đó đã được gán `culture_fun`, và khía cạnh này tên là "Văn hóa & môi trường". Từ điển thêm lại `môi trường`/`environment`; khía cạnh F1 trên TEST 0.731 → 0.764.
- **Sửa 7 câu theo 0.2.2** bằng `annotation/relabel_absa.py` (công cụ mới, áp dụng theo file đặc tả và lưu bản gốc trước khi ghi). Khía cạnh F1 trên TEST 0.764 → **0.770**, dev → 0.945.
- **Mở rộng dev lên 207 câu** (`absa_dev2`, 150 câu rút từ đúng 45 review đã ở dev): 57 câu là quá ít để sửa từ điển theo phân tích lỗi mà không chạm TEST. Thêm `--only-reviews-of` và `--exclude-texts-of` vào công cụ rút mẫu; đã kiểm tra 0 câu và 0 review chồng lấn giữa dev và test.
- **Rút thêm 56 câu để đủ cặp negative:** lô 300 câu chỉ cho 68 cặp `negative`, thấp hơn mục tiêu 90–110. Pool còn 0 câu nhãn yếu negative nên rút theo **phần review**: 56 câu "Đề nghị cải thiện" còn lại (0,67 cặp negative/câu so với 0,04 ở phần "Điều tôi thích"), lấy hết cả tầng nên không lệch tập test.
- **ĐÓNG BĂNG TEST WM3: 356 câu** (348 câu tính điểm, 378 cặp, 272 pos / 92 neg / 14 neu). Bản ghi kèm sha256 file nhãn: `data/annotation/absa_test1.frozen.json`. Từ đây không sửa nhãn TEST.
- **Số nền phải vượt** (chấm một lần trên TEST đã đóng băng): khía cạnh F1 **0.743**; macro theo ô chỉ pos/neg **0.496** (từ điển + luật đề nghị) và **0.515** (nhãn yếu); recall `negative` 0.315. Tập test khó lên so với lúc 292 câu (0.770 / 0.412) vì 56 câu thêm vào toàn góp ý nói giảm.
- **Một khía cạnh không cứu được:** `culture_fun` chỉ có 2 cặp `negative` (dự đoán 6–9). Người viết không chê văn hóa ở phần "Đề nghị cải thiện", họ chê quản lý (`management_care` 43 cặp neg, nhiều hơn pos) và OT. Là tính chất của nguồn ITviec, hết câu để rút thêm → chỉ báo macro-F1 theo khía cạnh cho `management_care`, `work_life_balance`, `salary_benefits`.

- **Dev lên 200 câu, từ điển lên v3.** 150 câu dev mới cho khía cạnh F1 0.738, gần đúng bằng TEST (0.743) và cao hơn hẳn nếu chỉ tính 57 câu dev cũ – xác nhận dev cũ đã bị từ điển v2 học thuộc. Thêm cụm khía cạnh (211 → 247) và cụm cảm xúc (101 → 124); đáng kể nhất là `management_care` trước đây thiếu hẳn từ "sếp".
- **Hai luật cực tính mới** (chọn trên dev, không chạm TEST): "không có / chưa có <khía cạnh>" → `negative`; điểm cảm xúc hòa nhau mà câu *có* từ cảm xúc → `negative` chứ không `neutral`. Siết luật đề nghị: "need to" đứng một mình bắt nhầm "Rarely need to do OT", "cải thiện" bắt nhầm "luôn được học hỏi và cải thiện kỹ năng".
- **Chấm v3 trên TEST đã đóng băng:** khía cạnh F1 0.743 → **0.753**, recall `negative` 0.315 → **0.424**, macro pos/neg 0.496 → **0.518** (nhãn yếu 0.519). Mức tăng nhỏ hơn trên dev (0.605) vì v3 chỉnh trên dev; số TEST là số báo cáo.
- **Sửa lỗi công cụ chấm:** `eval_dev` gộp nhiều file nhãn theo văn bản làm TEST tụt 348 → 344 câu (hai review khác nhau có câu giống hệt nhau). Đổi sang gộp theo `sentence_id`.
- **Sửa một nhãn sai ở dev:** "Unfair performance review." gán `positive`, sửa thành `negative`.

- **Chốt κ của WM3: Cohen's κ = 0,871** trên ô (câu × khía cạnh, 4 lớp); 0,883 cho riêng việc phát hiện khía cạnh, 0,872 cho riêng cực cảm xúc. Người thứ hai gán lại 35 câu rút ngẫu nhiên từ TEST đã đóng băng (10%), trên project Label Studio riêng, không thấy nhãn người thứ nhất. Đạt mục tiêu ≥ 0,7 ngay vòng đầu, không cần đo lại vòng 2 (WM2 vòng 1 chỉ 0,591 vì phải khớp ranh giới span).
- **Guideline lên 0.2.3** sau khi soát 6 câu lệch: thêm "năng lực của sếp/lead" → `management_care`, "CLB, uống bia" → `culture_fun`, và luật "câu liệt kê nhiều thứ phải tra từng thứ" (3/6 câu lệch là kiểu này). **TEST không sửa theo bản mới** vì đã đóng băng và đã có mô hình chấm trên đó; còn khoảng 2–3 câu TEST gán khác guideline hiện hành, đều ở chỗ `management_care` ↔ `culture_fun` – ghi vào phần hạn chế của báo cáo.
- **Hệ quả cho việc đọc số:** `management_care` vừa là khía cạnh từ điển làm tệ nhất (F1 0,516) vừa là chỗ hai người gán lệch nhau nhiều nhất, nên một phần của 0,516 là nhiễu nhãn chứ không phải mô hình yếu.

- **Bỏ kế hoạch train WM3 trên nhãn yếu.** Nhãn yếu WM3 lấy cực tính từ điểm sao review, mà review công khai ITviec toàn điểm cao: pool ngoài review của TEST chỉ cho 50 cặp `negative` trên 455 câu, và chỉ **1 cặp** nếu bỏ thêm các câu đã là dev gold (bắt buộc bỏ, để dev còn sạch cho việc chọn mô hình). Không học được lời chê từ đó. 99/144 review đã vào TEST nên không mở rộng pool được.
- **Đổi sang học có giám sát trên 200 câu dev**, chọn mô hình bằng 5-fold CV trong dev, chấm TEST một lần. Ba mô hình học từ đầu đều thua từ điển về khía cạnh (TF-IDF 0.533, PhoBERT đóng băng 0.617, PhoBERT fine-tune 0.343 so với từ điển 0.833): 160 câu train không đủ để học 6 khía cạnh, trong khi từ điển đã có 247 cụm do người soạn.
- **Chốt mô hình lai: khía cạnh của từ điển + hồi quy logistic cho cực tính**, đặc trưng là 11 tín hiệu của chính từ điển (số từ khen/chê, ba cờ luật, phần review…) cộng TF-IDF. Thêm PhoBERT đóng băng không giúp gì so với TF-IDF.
- **Chốt số trên TEST đã đóng băng:** macro pos/neg theo ô **0.518 → 0.590**, R `negative` 0.424 → **0.533**, độ đúng cực trên ô nhận ra đúng khía cạnh 0.681 → **0.842**. Bootstrap ghép cặp 1.000 lần: Δ macro = +0.072, CI95 [+0.027; +0.120], p(Δ≤0) = 0.000. Khía cạnh F1 giữ 0.753 theo thiết kế (dùng chính khía cạnh của từ điển).
- **Kiểm lại thì mức tăng đó chủ yếu không phải do học.** Một luật một dòng "câu ở phần Đề nghị cải thiện → chê, ở phần Điều tôi thích → khen" được 0.774 trên dev (hơn mô hình lai 0.768) và 0.583 trên TEST (lai 0.590, Δ = +0.007, CI95 [−0.013; +0.031], p = 0.264 – không có ý nghĩa). Trên TEST, 83/127 ô ở phần cải thiện là chê còn ở phần khen chỉ 7/201, tức là cấu trúc form ITviec đã mang gần hết thông tin cực tính. Đường cong học trên dev phẳng từ 80 câu (0.737 → 0.770 từ 20 đến 160 câu) và không vượt mức 0 câu train, nên **gán thêm câu sẽ không nâng được số này**. Báo cáo phải để "luật phần review" làm baseline chứ không chỉ so với từ điển, và nói rõ đây là kết quả âm.
- **Một lỗi đã thấy nhưng CHƯA sửa:** luật "không có" gọi "Công ty không có OT đâu nhé" là chê, trong khi với `work_life_balance` thì "không có OT" là khen. Quan sát này đến từ xem lỗi trên TEST nên không được sửa rồi chấm lại TEST; phải kiểm trên dev và chỉ chấm lại khi có tập test mới.

AI: Claude Code (Claude Opus 5) – chấm TEST, phân tích lỗi, sửa guideline và từ điển, rút lô bổ sung, từ điển v3, đo κ, mô hình lai cho cực tính; <người kiểm tra> đã kiểm tra

## 2026-11-15 · Hoang Le

- **Sửa ranh giới câu ITviec:** `<br>` bị biến thành dấu cách ở 57,6% khối review, dán hai ý thành một câu. Sửa parser + bộ tách câu, thêm `crawler/itviec/reparse.py` parse lại HTML đã lưu (không gửi request nào). 942 → **1065 câu**. `sentence_id` đổi sang băm theo nội dung để nhãn đã gán không mất khi sửa bộ tách câu.
- **Chốt quy ước gán ABSA:** công ty làm đúng nghĩa vụ mà người viết nhắc ra thì gán `positive` (guideline 0.2.1 luật 10, sau tranh luận về câu "OT tính theo quy định"). Thêm phép thử đổi chiều cho `neutral`; `neutral` còn 1/69 cặp trên dev.
- **Chốt số liệu dev WM3** (53 câu, 59 cặp): từ điển v2 + luật đề nghị F1 khía cạnh **0,933**, macro-F1 2 lớp **0,607**, recall `negative` **0,645** (v1: 0,806 / 0,375 / 0,121). Số dev, đã chỉnh trên chính tập này – chưa phải số test.
- **Chia dev/test theo review** (45 review dev / 99 review test) để nhãn yếu không rò rỉ sang tập chấm. Rút `absa_test1` 300 câu, chưa gán.
- AI: Claude Code (Claude Opus 5) – sửa parser, từ điển v2, công cụ chấm, rút mẫu; <người kiểm tra> đã kiểm tra

## 2026-10-12 (2) · Hoang Le

- **Sự cố crawl:** TopCV trả HTTP 429 từ ~20:40; spider bản cũ thử lại → 5.507 request (4.673 bị 429). Đã sửa: gặp 429/403 dừng ngay, tối thiểu 3 giây/request, giới hạn thử lại. Không crawl lại trong ngày bị 429. Chi tiết: `experiments/results.md`.
- **Chốt số liệu đợt 1:** 304 tin IT TopCV (`data/crawl/topcv/2026-10-12/`, không commit).
- AI: Claude Code (Claude Opus 5.5) – chạy crawl, phân tích sự cố, sửa spider; <người kiểm tra> đã kiểm tra

## 2026-10-12 · Hoang Le

- **Quyết định dữ liệu:** tin crawl (TopCV, ITviec) là dữ liệu chính; VietJobs chỉ dùng cho nhãn yếu, từ điển alias, baseline (joblens docs/13).
- **WM2:** tập test (~1.000 câu, người gán) lấy từ tin TopCV đã crawl. Đợt `skill_batch1` (VietJobs) dừng ở ~300 câu, dùng làm dev set / luyện guideline.
- Thêm `ie/vietjobs.py` (tập IT cố định `it_v1`), `ie/skill_alias.py` + `ie/resources/skill_alias.csv` (bản nháp tự sinh, chưa xem tay), `annotation/sample_skill_batch.py`, `annotation/guideline_skill.md` (bản 0.2), `annotation/label_studio_skill.xml`, `experiments/results.md`.
- Việc mới từ ADR 0002 (joblens): `mining-service` + stub theo `schemas/api/mining.v1.yaml`; ghi `sentence_text` vào `silver.review_aspects`.
- AI: Claude Code (Claude Opus 5.5) – script chuẩn bị dữ liệu, guideline, nháp từ điển; <người kiểm tra> đã kiểm tra

## 2026-10-02 · Hoang Le · chưa có PR

- **Tạo:** –
- **Sửa:** `.env.example` (C – thêm biến đăng nhập S3/Trino, `JOBLENS_SEARCH_URL`, ADR 0001 D7); `AGENTS.md` (C – phạm vi repo theo ADR 0001); `.gitignore`, `.pre-commit-config.yaml` (C – chỉ đổi dòng chú thích đầu file)
- **Xóa:** –
- **Lý do:** đồng bộ file cấu hình chung sau khi repo `joblens` thêm hợp đồng dữ liệu và ADR 0001
- **Ảnh hưởng repo khác:** đồng bộ cùng lúc ở cả 4 repo – xem `joblens/NHAT-KY.md`
- **AI:** Claude Code (Claude Opus 5.5) – soạn schema, contract, script, sửa docs theo phương án đề xuất của ADR 0001; <người kiểm tra> đã kiểm tra

## 2026-10-02 · Hoang Le · chưa có PR

- **Tạo:** `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/joblens.mdc` (C – đồng bộ từ joblens, có dòng `ĐỒNG BỘ TỪ`)
- **Sửa:** –
- **Xóa:** –
- **Lý do:** quy tắc làm việc cho AI agent (Codex, Claude Code, Cursor): tra repo-routing trước khi tạo file, ghi nhật ký, những việc không được làm, phạm vi riêng của repo này
- **Ảnh hưởng repo khác:** đồng bộ cùng lúc ở cả 4 repo – xem `joblens/NHAT-KY.md`
- **AI:** Claude Code (Claude Opus 5.5) – soạn quy tắc và script đồng bộ; <người kiểm tra> đã kiểm tra

## 2026-10-02 · Hoang Le · không qua PR (giai đoạn khởi tạo)

- **Tạo:** `NHAT-KY.md` (D)
- **Sửa:** `.gitignore`, `.pre-commit-config.yaml`, `.env.example`, `.gitattributes`, `CONTRIBUTING.md` (C – đồng bộ từ joblens, thêm dòng `ĐỒNG BỘ TỪ`; CONTRIBUTING thêm bước tra repo-routing và ghi nhật ký)
- **Xóa:** –
- **Lý do:** áp dụng quy ước file nào lên repo nào và nhật ký thay đổi
- **Ảnh hưởng repo khác:** đồng bộ cùng lúc ở cả 4 repo – xem `joblens/NHAT-KY.md`
- **AI:** Claude Code – dựng khung, soạn nội dung; <người kiểm tra> đã kiểm tra

## 2026-10-02 · Hoang Le · không qua PR (giai đoạn khởi tạo)

- **Tạo:** khung thư mục `crawler/`, `ie/`, `absa/`, `retrieval/`, `recsys/`, `graph/`, `annotation/`, `experiments/`, `images/`, `docs/adr/` (B); `models.yaml` (B); `README.md` (D); file cấu hình chung (C)
- **Sửa:** –
- **Xóa:** –
- **Lý do:** khởi tạo repo theo docs/project-plan/08; gộp commit "Initial commit" do GitHub tự sinh, giữ README của repo
- **Ảnh hưởng repo khác:** không
- **AI:** Claude Code – dựng khung, soạn nội dung; <người kiểm tra> đã kiểm tra
