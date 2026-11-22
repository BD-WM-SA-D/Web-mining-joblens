# Kết quả thực nghiệm Web Mining

Chỉ ghi số liệu, không ghi dữ liệu gốc. Mỗi số kèm snapshot dữ liệu và lệnh tạo ra nó.

**Tên gọi dùng trong file này.** Mỗi mô hình gọi theo cách làm ra nó, không đánh số phiên bản.

| Bài | Tên | Nghĩa |
|---|---|---|
| WM2 | nhãn yếu từ tag (`tag`) | tag "Kỹ năng cần có" của nhà tuyển dụng + từ điển alias |
| WM2 | nhãn yếu theo luật (`rules`) | như trên, thêm luật làm sạch theo guideline 0.4 |
| WM2 | nhãn yếu self-training (`selftrain`) | nhãn theo luật + span mà ba model PhoBERT cùng đoán |
| WM2 | nhãn yếu kho tag chung (`globaltag`) | self-training + từ điển gom từ tag của mọi tin |
| WM2 | nhãn yếu LLM (`llm`) | câu VietJobs do LLM gán theo guideline 0.4, câu TopCV giữ nhãn self-training |
| WM1 | MinHash / MinHash cắt khung | khóa tiêu đề + công ty ∪ MinHash; bản cắt khung thêm tiêu đề mềm và bỏ phần mô tả chung của công ty |
| WM3 | từ điển cơ bản / mở rộng / đủ luật | chỉ đếm từ cảm xúc; thêm bảng 2c và luật đề nghị; thêm luật "không có" và luật hòa (`absa-dict`) |
| WM5 | log cũ / log đã sửa | log synthetic trước và sau khi sửa lỗi dồn lượt xem về ngày cuối |
| Dữ liệu | `topcv_<ngày>`, `itviec_<ngày>`, `vietjobs_it` | snapshot đặt theo ngày tạo; `vietjobs_it` là tập tin IT của VietJobs |

## Sửa sau phản biện (2026-11-17)

Một bản phản biện ở vai người chấm (`data/phan-bien-wm-2026-11-17.md`, cục bộ) chỉ ra các chỗ đo sai
hoặc phát biểu quá. Bảng dưới là những gì đã đo lại; mỗi mục gốc cũng có ghi chú *(Sửa sau phản biện…)*
tại chỗ. Không chấm thêm hệ mới nào trên TEST: các phép đo WM2/WM3 dưới đây dùng lại dự đoán đã có.

| Mục | Hỏi | Kết quả đo lại | Kết luận cũ |
|---|---|---|---|
| WM5 | Mốc 70% mà train 929 / test 2.612? | **Lỗi thật, hai lỗi chồng nhau**: bộ sinh log dồn 74% lượt xem vào một ngày, hàm chia đưa cả ngày đó sang test. Sửa cả hai, sinh lại log. content-tfidf nDCG@10 **0,181 → 0,071** | Thứ tự giữ, số giảm một nửa; "6 lần" → 4,7 lần |
| WM2 | CI theo câu hẹp giả? (1.000 câu / 125 tin) | Bootstrap **theo tin**: ΔF1 seed 1 [+0,077; +0,149] (theo câu [+0,086; +0,143]) | Đứng – CI rộng hơn nhưng không chứa 0 |
| WM2 | F1 partial? | Từ điển 0,525; PhoBERT 0,632 / 0,669 / 0,641. Khoảng strict–partial ~0,08 ở **cả hai** hệ | Đứng – PhoBERT hơn không phải nhờ cắt mép |
| WM2 | Chỉ nội suy từ điển? | 528/1.149 span vàng (46%) **chưa thấy** trong nhãn yếu từ tag. Recall trên nhóm đó: từ điển 0,000, PhoBERT **0,19–0,25** | Đứng – hơn nửa phần recall PhoBERT tăng thêm là ở kỹ năng chưa thấy |
| WM2 | Câu bị đoán rỗng? | Trong câu có kỹ năng: từ điển rỗng **49,5%**, PhoBERT 27–32%. Tìm đúng ≥ 1 span: 0,410 so với 0,54–0,58 | Bổ sung |
| WM3 | Người gán thấy `section`? | **Đúng** – config Label Studio hiện `phần: $section`. Chưa kiểm được nhãn có suy từ `section` không: cần lô mù (gán lại khi ẩn `section`) | **Đang mở** |
| WM3 | Bỏ `section` khỏi mô hình? | Dev: 0,770 → **0,709**, vẫn hơn từ điển 0,605. Nhưng riêng luật `section` được 0,774 trên dev, và chia fold theo review thì mô hình lai cho **đúng từng số** như luật `section` | Mô hình học được phần ngoài `section` (~0,10 trên dev), nhưng không vượt được `section` |
| WM3 | CV chia theo câu rò rỉ? | Đúng. Chia theo review (`folds` đã sửa): 0,770 → **0,769** | Đứng |
| WM3 | CI theo review? | Δ so với từ điển [+0,025; +0,117] (theo câu [+0,027; +0,120]); so với `section` [−0,012; +0,031] | Đứng |
| WM3 | Tách vi/en? | 85 câu en / 263 vi. Lai hơn `section` +0,025 ở en, **+0,001 ở vi** | Bổ sung – phần hơn `section` gần như chỉ ở câu tiếng Anh |
| WM3 | Trần do một cực/câu? | 61 câu nhiều khía cạnh, chỉ **3** có hai cực. Trần 0,989 | Không phải giới hạn thật |
| WM3 | κ lớp `negative`? | **0,657, CI [0,187; 1,000]** (7 và 5 cặp chê). κ ô 4 lớp 0,871 CI [0,754; 0,964] | Bỏ "almost perfect" |
| WM6 | Kiểm định PPR? | Recall@10 +0,040 CI [+0,021; +0,059], dấu 89/39; MRR +0,007 CI [−0,007; +0,020] | Sửa: hơn ở Recall@10, không hơn ở MRR |
| WM6 | "8 cụm khớp vai trò nghề thật"? | Không có mốc ngoài; NMI theo nguồn 0,476 < mốc ngẫu nhiên 0,615 | Sửa phát biểu |

**Còn mở, cần quyết định chứ không phải đo:** lô mù cho WM3 (ai gán, rút từ đâu), căn cứ pháp lý khi
dùng dữ liệu ITviec (tài liệu đánh giá ghi "chưa crawl ITviec" vì điều khoản), chọn một bản nhãn TEST
WM3 làm chuẩn rồi chấm lại mọi hệ trên đúng bản đó, chạy lại mọi số trên một commit sạch.

Lệnh: `uv run python -m experiments.diag_wm2`, `uv run python -m experiments.diag_wm3`,
`uv run python -m experiments.paired_wm3 --baseline section`, `uv run python -m graph.recommend`,
`uv run python -m annotation.kappa_absa --a data/annotation/absa_test1.absa.jsonl --b data/annotation/absa_kappa1_p2.absa.jsonl`

## Chạy lại một lượt (2026-11-18)

`bash experiments/run_all.sh` chạy lại mọi số chính thức, không crawl. Lượt đầu trên `217f81c-dirty`
(train lại PhoBERT nhãn tag, ~55 phút; log `data/logs/run_all-20261118-1555` và `-1641`). **Lượt chính thức trên
commit sạch `a2f03a8`** (31 bước, ~17 phút, log `data/logs/run_all-20261118-1655`): mọi file
`experiments/runs/2026-11-18-*-test-*.json` ghi `git_commit: a2f03a8`; chỉ còn 6 file dev của lần train lại
PhoBERT nhãn tag mang `217f81c-dirty` (số dev, không phải số báo cáo). Hai lượt ra cùng số. Kết quả so với số đã ghi:

| Bài | Khớp? | Ghi chú |
|---|---|---|
| WM1 dedup (nhãn 0.1 và 0.2), κ | Khớp từng số | |
| WM2 từ điển, PhoBERT self-training (hệ chính lúc đó) | Khớp từng số | Dự đoán giống hệt từng byte lần chấm trước |
| WM2 PhoBERT nhãn tag (số cũ) | Trung bình khớp (0,562 ± 0,015) | Model nhãn tag bị xóa nhầm khi dọn ổ, train lại 3 seed; từng seed lệch ≤ 0,009 (0,547 / 0,577 / 0,563 so với 0,555 / 0,578 / 0,554) do GPU không tất định. Kết luận giữ nguyên |
| WM2 κ | Không tái lập được 0,650 | Xem mục κ WM2: nhãn người 1 đã sửa sau khi đo, ra 0,675 |
| WM3 TEST, so với từ điển và luật `section`, đối chiếu sao, κ | Khớp | CV dev của mô hình lai 0,774 (đã ghi 0,768; nằm trong khoảng 5 seed 0,768–0,779) |
| WM5 | Khớp từng số | Log đã sửa sinh lại giống hệt (cùng sha256) |
| WM6 | Khớp | |
| Nhu cầu kỹ năng | Chạy được | |

## Độ bền với nhiễu – đăng ký trước (2026-11-18, ghi TRƯỚC khi chạy)

Câu hỏi: dedup (WM1) và trích kỹ năng (WM2) giữ được bao nhiêu khi văn bản tin bị biến dạng như ngoài thực tế
(đăng lại không dấu, thêm chữ vào tiêu đề, gõ sai, cắt bớt mô tả)? **Chỉ đo, không chỉnh hệ nào**: hệ, ngưỡng,
từ điển, model giữ nguyên như số đã báo; tập đánh giá là 300 cặp WM1 (nhãn 0.2) và `skill_test1` (WM2).
Nhãn không đổi vì nhiễu không đổi nghĩa tin. Cùng ý tưởng với thí nghiệm nhiễu của Big Data nhưng khác đối
tượng: BD đo pipeline chuẩn hóa trường có sẵn, ở đây đo mô hình khai phá; code và số viết riêng.

| Nhiễu | WM1: áp vào | WM2: áp vào | Cách làm |
|---|---|---|---|
| `bo_dau` | tiêu đề + mô tả + yêu cầu | mọi token | bỏ dấu tiếng Việt (đ → d) |
| `go_sai` | mô tả + yêu cầu | mọi câu | đảo hai ký tự kề nhau ở giữa 10% số từ dài ≥ 4 |
| `tieu_de_them` | tiêu đề | – | thêm một trong "(Tuyển gấp)", "- Lương upto 2000$", "[Hà Nội]", "- Urgent" |
| `cat_mo_ta` | mô tả + yêu cầu | – | giữ 60% số ký tự đầu |
| `chu_thuong` | – | mọi token | chữ thường hết |

- WM1: mỗi tin bị nhiễu độc lập với xác suất **0,5** (để khoảng một nửa số cặp có hai bản khác nhau), seed
  20261118. Báo P/R/F1 của baseline, bản MinHash, bản cắt khung cho từng loại nhiễu cạnh số khi không nhiễu.
- WM2: mọi câu của TEST bị nhiễu (go_sai: 10% từ). Báo F1 strict của từ điển và PhoBERT self-training (3 seed, trung bình).
- Dự đoán trước (để đối chiếu, không để chọn): baseline khóa tiêu đề hỏng nặng với `tieu_de_them` và `bo_dau`;
  MinHash chịu `go_sai` tốt hơn khóa tiêu đề; từ điển hỏng nặng với `bo_dau`, PhoBERT ít hơn.

### Kết quả độ bền (2026-11-18, chạy một lần theo đăng ký trên)

**WM1** – 300 cặp, nhãn 0.2 (13 cặp trùng; mỗi cặp trùng bắt được hay không làm R đổi 0,077, nên chỉ đọc
chênh lệch lớn):

| Nhiễu | baseline P / R / F1 | bản MinHash P / R / F1 | bản cắt khung P / R / F1 | cặp có bản nhiễu |
|---|---|---|---|---|
| không | 1,000 / 0,385 / 0,556 | 0,323 / 0,769 / 0,455 | 0,556 / 0,769 / **0,645** | 0 |
| `bo_dau` | 1,000 / 0,231 / 0,375 | 0,333 / 0,538 / 0,412 | 0,571 / 0,615 / 0,593 | 138 |
| `go_sai` | 1,000 / 0,385 / 0,556 | 0,500 / 0,692 / 0,581 | 0,667 / 0,615 / 0,640 | 238 |
| `tieu_de_them` | 1,000 / 0,308 / 0,471 | 0,310 / 0,692 / 0,429 | 0,556 / 0,769 / **0,645** | 222 |
| `cat_mo_ta` | 1,000 / 0,385 / 0,556 | 0,429 / 0,462 / 0,444 | 0,500 / 0,538 / **0,519** | 231 |

- Đúng dự đoán: khóa tiêu đề chính xác (baseline) mất cặp trùng khi tiêu đề bị thêm chữ (R 0,385 → 0,308) hoặc
  mất dấu (→ 0,231). **bản cắt khung không bị `tieu_de_them` ảnh hưởng** (vẫn 0,645): tiêu đề mềm bỏ được địa điểm và
  ngoặc, phần còn lại do MinHash trên mô tả gánh.
- Điểm yếu thật của bản cắt khung là **mô tả bị cắt** (F1 0,645 → 0,519): MinHash so tập shingle nên bản ngắn hơn 40% kéo
  Jaccard xuống dưới 0,5. Bỏ dấu cũng làm mất 2/10 cặp bản cắt khung đang bắt.
- Gõ sai 10% từ gần như không ảnh hưởng bản cắt khung; với bản MinHash còn làm *tăng* P (báo nhầm cùng công ty có Jaccard sát 0,5
  bị đẩy xuống dưới ngưỡng) – không phải ưu điểm, chỉ là các cặp sát ngưỡng.

**WM2** – `skill_test1`, 1.000 câu, mọi câu bị nhiễu:

| Nhiễu | từ điển F1 | PhoBERT self-training F1 (seed 1 / 2 / 3) | PhoBERT TB | PhoBERT − từ điển |
|---|---|---|---|---|
| không | 0,442 | 0,616 / 0,618 / 0,617 | **0,617** | +0,175 |
| `bo_dau` | 0,426 | 0,519 / 0,527 / 0,518 | 0,521 (−0,096) | +0,095 |
| `chu_thuong` | 0,398 | 0,552 / 0,550 / 0,559 | 0,554 (−0,063) | +0,156 |
| `go_sai` | 0,417 | 0,600 / 0,599 / 0,601 | 0,600 (−0,017) | +0,183 |

- **Sai dự đoán:** bỏ dấu làm PhoBERT tụt nhiều hơn từ điển (−0,096 so với −0,016). Lý do: từ điển chủ yếu là
  tên kỹ năng Latin (Java, Docker…) vốn không có dấu, còn PhoBERT dựa vào ngữ cảnh tiếng Việt có dấu và mất phần
  lớn cụm tiếng Việt ("kiểm thử tự động" → "kiem thu tu dong" là chuỗi PhoBERT chưa từng thấy). PhoBERT vẫn hơn
  từ điển ở mọi loại nhiễu.
- Chữ thường làm cả hai cùng tụt: từ điển vì alias ≤ 3 ký tự phân biệt hoa thường ("AI", "Go"), PhoBERT vì
  mất tín hiệu viết hoa của tên riêng.
- Ứng dụng: nếu nguồn tin mới đăng không dấu (một số trang tổng hợp), nên báo F1 kỳ vọng khoảng 0,52 chứ không
  phải 0,62. Không sửa gì trên TEST; muốn bền hơn với bỏ dấu thì thử thêm bản không dấu vào nhãn yếu, chọn trên dev.

Lệnh: `uv run python -m experiments.robustness wm1`, `uv run python -m experiments.robustness wm2`.

## VietJobs cho WM6 và WM2 – đăng ký trước (2026-11-18, ghi TRƯỚC khi chạy)

VietJobs (Pham Dinh et al., LREC 2026) không có tên công ty, nguồn, review nên không dùng được cho WM1, WM3
hay làm tập test. Hai chỗ nó giúp được là chỗ cần **nhiều văn bản**: kiểm cụm kỹ năng WM6 trên một kho tin
khác, và cho PhoBERT đọc văn bản tin tuyển dụng trước khi fine-tune WM2. Không chỉnh hệ nào trên TEST.

### A. WM6 – cụm kỹ năng có lặp lại trên VietJobs không

- Dữ liệu: VietJobs `vietjobs_it` (1.906 tin ngành CNTT). Đồ thị đối chiếu: đồ thị crawl đã báo (TopCV `topcv_20261115` +
  ITviec `itviec_20261113`, 867 tin).
- Cách dựng giữ nguyên: từ điển alias trên tiêu đề + mô tả + yêu cầu, `min_df` 5, `min_weight` 3, NPMI ≥ 0,3,
  Louvain seed 1, resolution 1. **Không** dùng cột `technical_skills` của VietJobs (sinh bằng LLM, khác loại với
  tag nhà tuyển dụng). Vì đồ thị crawl có dùng tag nhà tuyển dụng, dựng thêm bản crawl **không tag** để so cùng cách.
- Đo:
  1. Q so với đồ thị ngẫu nhiên giữ bậc (100 lần) trên đồ thị VietJobs.
  2. NMI/ARI giữa phân hoạch crawl và phân hoạch VietJobs trên đỉnh chung; mốc xáo nhãn ngẫu nhiên (200 lần);
     đối chiếu hai mốc đã có trong crawl: chia ngẫu nhiên 0,615, chia theo nguồn 0,476.
  3. Spearman thứ hạng số tin (df) trên đỉnh chung; số kỹ năng chung trong top-20.
  4. Bảng cụm VietJobs, đọc định tính.
- Dự đoán (để đối chiếu, không để chọn): Q VietJobs vượt ngẫu nhiên rõ; NMI crawl–VietJobs khoảng 0,35–0,5, thấp
  hơn chia theo nguồn vì VietJobs khác thời gian và có nhiều vị trí phần cứng/hỗ trợ; cụm DevOps, Mobile,
  Frontend lặp lại, cụm BA/ERP khác.

### B. WM2 – tiền huấn luyện thích nghi miền (DAPT) trên VietJobs

- Câu hỏi: cho PhoBERT-base-v2 học tiếp masked LM trên văn bản tin tuyển dụng trước khi fine-tune có làm F1 trích
  kỹ năng tăng không.
- Corpus: tiêu đề + mô tả + yêu cầu của 48.092 tin VietJobs, tách dòng/câu, token như lúc fine-tune (TOKEN_RE),
  tách từ underthesea. Không dùng văn bản crawl TopCV/ITviec (chứa câu của `skill_test1`), không dùng nhãn.
- Chống rò rỉ: bỏ khỏi corpus mọi câu trùng nguyên văn (sau khi chuẩn hóa khoảng trắng, chữ thường) với một câu
  của `skill_test1`; báo số câu đã bỏ.
- Cấu hình cố định: che 15% subword, độ dài tối đa 256, lr 5e-5, warmup 6%, weight decay 0,01, batch hiệu dụng 32,
  1 epoch, seed 1, fp16. Nếu ước lượng thời gian > 4 giờ trên RTX 3050 Ti thì lấy mẫu ngẫu nhiên (seed 1) bớt câu
  cho vừa, ghi số câu thật đã dùng.
- Fine-tune: đúng công thức chuẩn (nhãn yếu self-training, lr 3e-5, 3 epoch, bs 16, neg_ratio 0,3, chọn epoch trên dev
  `skill_batch1`), seed 1–3, **chỉ thay mô hình gốc**.
- Chấm `skill_test1` **một lần**. Số chính: F1 trung bình 3 seed so với bản self-training (0,617); ΔF1 giữa DAPT + self-training và bản self-training cùng
  seed, bootstrap ghép cặp theo tin (1.000 lần).
- Quy tắc kết luận: chỉ viết "DAPT tốt hơn" nếu CI95 của ΔF1 nằm hẳn trên 0 ở cả 3 seed; ngược lại viết "không
  khác biệt" hoặc "kém hơn". Image `skill-extractor` chỉ đổi sang DAPT nếu tốt hơn theo quy tắc này.
- Dự đoán: tăng nhỏ, +0,005 đến +0,02, chủ yếu ở recall cụm tiếng Việt.

### Kết quả A – WM6 trên VietJobs (2026-11-18, chạy một lần theo đăng ký trên)

**Có cấu trúc cụm.** Đồ thị VietJobs IT: 1.533/1.906 tin có kỹ năng (5,5 kỹ năng/tin), 194 đỉnh; NPMI ≥ 0,3 còn
193 đỉnh, 1.388 cạnh. Louvain 7 cụm, Q = **0,497** (ngẫu nhiên giữ bậc 0,199 ± 0,009, z = 33,2, 0/100 lần vượt),
ổn định giữa seed NMI 0,80–0,94.

**Cụm của crawl lặp lại phần lớn trên VietJobs:**

| So với VietJobs | Đỉnh chung | NMI | ARI | mốc xáo (NMI) |
|---|---|---|---|---|
| đồ thị crawl đã báo (có tag nhà tuyển dụng) | 160 | **0,595** | 0,442 | 0,073 |
| đồ thị crawl không tag (cùng cách dựng với VietJobs) | 160 | 0,605 | 0,445 | 0,065 |
| *mốc trong crawl:* chia ngẫu nhiên hai nửa | 140 | 0,615 | 0,542 | 0,057 |
| *mốc trong crawl:* TopCV so với ITviec | 134 | 0,476 | 0,399 | 0,056 |

Bỏ tag nhà tuyển dụng gần như không đổi kết quả (crawl có tag so với không tag: NMI 0,816).

| Cụm crawl | Kỹ năng nhiều tin nhất | Rơi vào cụm VietJobs | Tỉ lệ |
|---|---|---|---|
| BA / quản lý sản phẩm | API, Agile, Jira, Phân tích yêu cầu, Scrum | BA / quản lý dự án (có cả ERP, CRM, Excel) | 25/35 |
| Frontend và .NET | JavaScript, TypeScript, ReactJS, C#, Node.js | Web (Git, JavaScript, ReactJS, HTML, PHP) | 21/28 |
| Backend Java | Java, Git, PostgreSQL, Microservices | Backend / CSDL (Java, MySQL, Oracle, C#) | 21/27 |
| DevOps / cloud | CI/CD, Docker, AWS, Kubernetes | DevOps / cloud (cùng Python, Linux) | 20/22 |
| Hệ thống / mạng | Linux, Bash, Firewall, TCP/IP | DevOps / cloud | 14/14 |
| Mobile | Kotlin, Swift, Flutter, XCode | Web | 7/8 |
| ML / dữ liệu | Python, Machine Learning, C++, R | AI / phân tích dữ liệu | 8/15 |
| ERP / BI | ERP, CRM, ETL, Power BI | AI / phân tích dữ liệu | 6/11 |

VietJobs có thêm hai cụm crawl không có: **thiết kế** (Photoshop, Illustrator, Figma, InDesign, Canva) và
**3D / CAD** (AutoCAD, 3ds Max, SketchUp, Blender). Ngành "CNTT, kỹ thuật số" của VietJobs rộng hơn tập tin
IT đã crawl.

**Thứ hạng độ phổ biến khác nhiều hơn cụm:** Spearman số tin trên 163 đỉnh chung 0,748; top-20 chung 11/20.
Crawl nghiêng về cloud/DevOps (Azure, GCP, Kubernetes, Microservices chỉ ở top crawl), VietJobs nghiêng về thiết
kế và phân tích (Photoshop, Figma, Phân tích dữ liệu, Quản lý dự án chỉ ở top VietJobs). Khớp với bảng nhu cầu kỹ
năng đã có: ITviec chủ yếu công ty IT nước ngoài.

**Đối chiếu dự đoán:**
- Q vượt ngẫu nhiên: đúng.
- NMI dự đoán 0,35–0,5, đo được **0,595**: cao hơn dự đoán, gần bằng mốc chia ngẫu nhiên trong crawl và cao hơn
  mốc TopCV–ITviec.
- DevOps, Frontend lặp lại: đúng. Mobile không thành cụm riêng mà gộp vào Web. BA lặp lại; ERP bị kéo sang nhóm
  dữ liệu.

**Đọc đúng:** nhóm kỹ năng lớn (web, backend, DevOps, BA, dữ liệu) **không chỉ là nếp riêng của TopCV và
ITviec**: chúng lặp lại trên một kho tin khác, khác thời gian, lớn gấp đôi. Phần không lặp lại là cụm nhỏ
(mobile, mạng) và ranh giới ERP/dữ liệu.

**Hạn chế của phép so này:**
- Từ điển alias dựng một phần từ tag `technical_skills` của VietJobs, nên hai đồ thị dùng chung bộ đỉnh có sẵn.
  Phép so đo cách các kỹ năng *gom nhóm*, không đo độ phủ kỹ năng.
- Không so được trực tiếp với mốc "chia ngẫu nhiên hai nửa" (0,615): mỗi nửa crawl chỉ khoảng 430 tin, VietJobs
  1.533 tin. Đồ thị lớn hơn thì ổn định hơn, nên NMI 0,595 có thể bị đẩy lên một phần vì cỡ dữ liệu.
- VietJobs có thể chứa tin cùng vị trí với tin crawl (cùng thị trường), không gộp được vì VietJobs không có tên
  công ty.

Lệnh: `uv run python -m graph.build --snapshots data/vietjobs/vietjobs_it.parquet --no-tags --out data/graph/skill_graph_vietjobs.json`;
`uv run python -m graph.build --no-tags --out data/graph/skill_graph_dict_notags.json`;
`uv run python -m graph.analyze cluster --graph data/graph/skill_graph_vietjobs.json --min-npmi 0.3 --n-null 100`;
`uv run python -m graph.analyze compare --other data/graph/skill_graph_vietjobs.json` (thêm `--graph data/graph/skill_graph_dict_notags.json` cho bản không tag).

### Kiểm tra rò rỉ: câu `skill_test1` có nằm trong dữ liệu train không (2026-11-19)

Làm khi dựng corpus DAPT: so nguyên văn (chữ thường, gộp khoảng trắng) từng câu TEST với dữ liệu khác.

- **Corpus DAPT (VietJobs 567.888 câu):** 397 câu trùng một câu TEST → đã bỏ trước khi train, theo đăng ký.
- **Nhãn yếu từ tag, theo luật và self-training (24.144 câu, dùng để train mọi bản PhoBERT đã báo):** 57 câu trùng, ứng với **30 câu TEST**
  (29 câu khác nhau; 33 câu từ VietJobs, 24 từ TopCV). Không có tin TopCV nào chung giữa nhãn yếu và TEST (0/125):
  trùng là do câu chung chung ("Tiếng Anh giao tiếp tốt.", "Mô tả công việc") và một tin tuyển game được đăng lại
  dưới mã tin khác. 8/30 câu có kỹ năng trong nhãn vàng.
- Dev `skill_batch1` không trùng TEST.

Ảnh hưởng tới số đã báo – chấm lại trên 970 câu sau khi bỏ 30 câu trùng (cùng dự đoán, không train lại):

| | F1 trên 1.000 câu | F1 trên 970 câu |
|---|---|---|
| từ điển | 0,442 | 0,443 |
| PhoBERT self-training seed 1 / 2 / 3 | 0,616 / 0,618 / 0,617 | 0,619 / 0,621 / 0,620 |

Bỏ câu trùng làm F1 *tăng* nhẹ, nên số 0,617 không được đẩy lên nhờ rò rỉ. Số chính thức giữ nguyên trên 1.000
câu; ghi kiểm tra này vào phần hạn chế. Lô nhãn yếu sau (nếu có) nên lọc câu TEST ngay khi sinh.

### Kết quả B – DAPT (2026-11-19, chạy và chấm TEST một lần theo đăng ký trên)

**DAPT (học tiếp MLM):**

- Corpus: 48.092 tin, 567.888 câu; bỏ 397 câu trùng TEST.
- Dữ liệu train: 58.182 đoạn, 9,4M subword. Dùng hết, không lấy mẫu bớt vì ước lượng 166 phút < 4 giờ.
- Thời gian: 167 phút trên RTX 3050 Ti.
- Loss MLM trên 500 đoạn giữ lại: **1,951 → 1,217** (perplexity 7,0 → 3,4). Mô hình đã quen văn phong tin tuyển dụng.

**Fine-tune bản self-training từ mô hình DAPT, chấm `skill_test1` (1.000 câu):**

| Seed | dev F1 | TEST P | TEST R | TEST F1 | bản self-training TEST F1 | ΔF1 (CI95, bootstrap theo tin) |
|---|---|---|---|---|---|---|
| 1 | 0,650 | 0,702 | 0,546 | 0,614 | 0,616 | −0,002 [−0,014; +0,011] |
| 2 | 0,657 | 0,695 | 0,545 | 0,611 | 0,618 | −0,007 [−0,021; +0,006] |
| 3 | 0,635 | 0,724 | 0,508 | 0,597 | 0,617 | **−0,020 [−0,037; −0,005]** |
| TB | 0,647 ± 0,011 | 0,707 | 0,533 | **0,607 ± 0,009** | 0,617 | |

Nhận xét:

- Dev F1 trung bình gần như bằng bản self-training (0,647 so với 0,644).
- Ghép thêm từ điển (`phobert+dict`) cũng không đổi kết luận: TEST 0,612 / 0,609 / 0,596.

**Kết luận theo quy tắc đã đăng ký:** DAPT **không tốt hơn** bản self-training.

- Seed 1 và 2: không khác biệt, vì CI chứa 0.
- Seed 3: kém hơn, vì CI nằm hẳn dưới 0.
- Image `skill-extractor` giữ PhoBERT self-training, không đổi.

**Đối chiếu dự đoán:** dự đoán tăng +0,005 đến +0,02 là **sai**. Thực tế F1 trung bình giảm 0,010, recall không tăng.

Cách hiểu (giả thuyết, chưa kiểm chứng):

- PhoBERT-base-v2 vốn đã học trên tin tức và Wikipedia tiếng Việt, nên phần chữ thường trong tin tuyển dụng không mới với nó.
- Loss MLM giảm phần lớn nhờ các đoạn khuôn mẫu lặp lại giữa các tin ("Mô tả công việc", phúc lợi). Những đoạn này không giúp nhận ranh giới span kỹ năng.
- Nút thắt của WM2 là nhãn yếu bỏ sót (recall thấp ở mọi bản), không phải biểu diễn ngôn ngữ.

Hạn chế: chỉ thử một cấu hình (1 epoch, lr 5e-5), không dò thêm vì đã đăng ký trước. Lúc chấm, repo có thay đổi chưa commit (`ie/dapt.py`, `--base`/`--tag` trong `ie/phobert.py`); khi commit thì ghi gitsha ở đây.

Lệnh:

    uv run python -m ie.dapt corpus && uv run python -m ie.dapt train
    uv run python -m ie.phobert train --weak selftrain --base data/models/phobert-dapt-vietjobs --tag dapt --seed <N>
    uv run python -m ie.phobert eval --weak selftrain --tag dapt --model data/models/wm2-phobert-selftrain-dapt-s<N> \
        --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --seed <N>
    uv run python -m experiments.paired_wm2 --bio data/annotation/skill_test1.bio.jsonl --prefix wm2-phobert-selftrain-dapt \
        --out data/eval/skill_test1_preds_selftrain_dapt.json --against data/eval/skill_test1_preds_selftrain.json

## Cải thiện nhãn yếu WM2 – đăng ký trước (2026-11-19, ghi TRƯỚC khi chạy)

Kết quả DAPT cho thấy nút thắt của WM2 là nhãn yếu bỏ sót: recall nhãn yếu theo luật trên dev chỉ 0,48. Thử hai cách,
mỗi cách đúng **một** cấu hình cố định dưới đây, không dò tham số. Không dùng gì rút ra từ phân tích lỗi TEST.

**Cách 1 – từ điển từ kho tag toàn cục (nhãn yếu kho tag chung).**
- Hiện mỗi tin chỉ được dò bằng tag của chính nó. Bản kho tag chung gom thêm `technical_skills` của **toàn bộ** VietJobs
  (mọi ngành, 48k tin) và `skill_tags` của TopCV (`topcv_20261118`) thành một từ điển chung.
- Lọc tag bằng `clean_tags` như cũ (bỏ kỹ năng mềm, ≤ 5 token), rồi giữ tag xuất hiện ở **≥ 3 tin khác nhau**.
  Bỏ hẳn tin thuộc dev/test (`skill_batch1`, `skill_test1`) khi đếm.
- Bản kho tag chung = nhãn self-training + span dò bằng từ điển chung ở chỗ bản self-training còn trống (không đè span cũ), rồi qua luật 0.4 (`refine`).
- Đo độ nhiễu trên dev như hai bộ nhãn từ tag và theo luật: cách gán bản nhãn luật (tag + từ điển + luật) so với bản nhãn luật + từ điển chung.

**Cách 3 – giảm phạt token O khi train.** Nhãn yếu thiếu nhiều kỹ năng, nên token gán O không chắc là O.
Loss của token nhãn O nhân hệ số **0,5**, token B/I giữ 1. Mọi thứ khác như bản self-training.

**Thí nghiệm:** công thức chuẩn (lr 3e-5, 3 epoch, bs 16, neg_ratio 0,3, chọn epoch theo dev), seed 1–3:
- A: nhãn kho tag chung;
- B: nhãn self-training + hệ số O 0,5;
- C: nhãn kho tag chung + hệ số O 0,5.

**Chọn và chấm:**
- Chọn cấu hình theo F1 `phobert` trung bình 3 seed **trên dev**.
- Chỉ đem sang TEST nếu cấu hình tốt nhất có dev cao hơn bản self-training (0,644); nếu không thì ghi "không cải thiện" và dừng,
  không chấm TEST.
- Cấu hình được chọn chấm `skill_test1` **một lần**, so ghép cặp với bản self-training cùng seed (bootstrap theo tin, 1.000 lần).
- Quy tắc kết luận giống DAPT: chỉ viết "tốt hơn" nếu CI95 của ΔF1 nằm hẳn trên 0 ở cả 3 seed. Image
  `skill-extractor` chỉ đổi khi thỏa điều đó.

**Dự đoán:**
- Cách 1: recall nhãn yếu trên dev tăng 0,03–0,08, precision giảm ≤ 0,03.
- Cách 3: recall mô hình tăng, precision giảm, F1 tăng 0–0,02.
- Khả năng cao không cấu hình nào đạt quy tắc "tốt hơn ở cả 3 seed".

### Kết quả cải thiện nhãn yếu (2026-11-19, chạy và chấm TEST một lần theo đăng ký trên)

**Độ nhiễu nhãn yếu trên dev (cách 1):**

| Nhãn yếu (dev, so với nhãn tay) | P | R | F1 |
|---|---|---|---|
| Bản nhãn luật: tag + từ điển + luật | 0,812 | 0,476 | 0,600 |
| Bản nhãn luật + kho tag chung (cách gán của bản kho tag chung) | 0,447 | 0,610 | 0,516 |

- Kho tag có 48.194 tin và 12.054 tag; giữ lại 2.934 tag có ở ≥ 3 tin.
- Bản kho tag chung thêm 18.393 span, nâng số câu có kỹ năng từ 7.350 lên 14.704.
- Span thêm nhiều nhất là từ chung: `công nghệ` (850), `CNTT` (611), `hình ảnh` (415), `nhanh` (349), `thương hiệu`, `doanh nghiệp`, `quảng cáo`.
- Nguyên nhân: tag `technical_skills` của VietJobs do LLM sinh, có nhiều danh từ chung; lọc theo tần suất không loại được, vì từ càng chung càng xuất hiện nhiều.

**Dev, F1 `phobert` theo seed 1 / 2 / 3:**

| Cấu hình | Dev F1 | Trung bình |
|---|---|---|
| Bản self-training (mốc) | | 0,644 |
| A: nhãn kho tag chung | 0,543 / 0,530 / 0,535 | 0,536 |
| B: bản self-training + hệ số O 0,5 | 0,664 / 0,676 / 0,664 | **0,668 ± 0,007** |
| C: bản kho tag chung + hệ số O 0,5 | 0,556 / 0,533 / 0,541 | 0,543 |

- A và C: precision dev khoảng 0,46. Mô hình học đúng theo nhãn bẩn.
- B là cấu hình duy nhất vượt bản self-training trên dev, nên đem sang TEST theo đăng ký.

**TEST `skill_test1` (1.000 câu), cấu hình B, chấm một lần:**

| Seed | P | R | F1 | bản self-training F1 | ΔF1 (CI95, bootstrap theo tin) |
|---|---|---|---|---|---|
| 1 | 0,692 | 0,530 | 0,600 | 0,616 | −0,016 [−0,032; +0,002] |
| 2 | 0,655 | 0,601 | 0,627 | 0,618 | +0,009 [−0,007; +0,025] |
| 3 | 0,644 | 0,596 | 0,619 | 0,617 | +0,002 [−0,015; +0,020] |
| TB | 0,664 | 0,576 | **0,615 ± 0,014** | 0,617 | |

Ghép thêm từ điển (`phobert+dict`): 0,598 / 0,625 / 0,618.

**Kết luận theo quy tắc đã đăng ký:**
- B **không khác biệt** so với bản self-training: CI chứa 0 ở cả 3 seed.
- Image `skill-extractor` giữ PhoBERT self-training.
- Cách 1 (bản kho tag chung) **làm kém đi** rõ rệt trên dev, nên không đem sang TEST.

**Đối chiếu dự đoán:**
- Cách 1: recall nhãn tăng 0,134, vượt khoảng dự đoán 0,03–0,08. Precision giảm 0,365 thay vì ≤ 0,03. Dự đoán **sai**.
- Cách 3:
  - Đúng chiều: recall tăng (seed 2–3 khoảng 0,60, so với khoảng 0,53 của bản self-training và DAPT), precision giảm.
  - F1 không tăng: −0,002, nằm ngoài khoảng 0 đến +0,02 đã dự đoán, nhưng sát mép dưới.
- Dự đoán chung "không cấu hình nào đạt quy tắc" là đúng.

**Nhận xét:**
- Dev tăng +0,024 nhưng TEST không tăng. Một phần do chọn epoch theo dev 300 câu, phần lạc quan trên dev ở đây cỡ 0,02–0,05, giống chênh dev–TEST đã thấy ở bản self-training. Ghi vào hạn chế: dev 300 câu quá nhỏ để chọn giữa các cấu hình chênh nhau dưới 0,03.
- Hệ số O chỉ dời điểm cân bằng giữa precision và recall, không thêm thông tin mới. Muốn F1 tăng thật thì cần nhãn có thêm thông tin đúng. Cách khả thi nhất là gán tay thêm câu train (cách 4).
- Nếu thử lại kho tag chung thì phải lọc theo loại tag (ví dụ chỉ tên riêng Latin), và đăng ký trước như một bản mới.

Repo chưa commit lúc chấm (`ie/weak_global.py`, `--o-weight` trong `ie/phobert.py`); ghi gitsha khi commit.

Lệnh:

    uv run python -m ie.weak_global
    uv run python -m ie.phobert train --weak globaltag --seed <N>
    uv run python -m ie.phobert train --weak selftrain --o-weight 0.5 --tag ow05 --seed <N>
    uv run python -m ie.phobert train --weak globaltag --o-weight 0.5 --tag ow05 --seed <N>
    uv run python -m ie.phobert eval --weak selftrain --tag ow05 --model data/models/wm2-phobert-selftrain-ow05-s<N> \
        --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --seed <N>
    uv run python -m experiments.paired_wm2 --bio data/annotation/skill_test1.bio.jsonl --prefix wm2-phobert-selftrain-ow05 \
        --out data/eval/skill_test1_preds_selftrain_ow05.json --against data/eval/skill_test1_preds_selftrain.json

## Nhãn yếu bằng LLM theo guideline – đăng ký trước (2026-11-19, ghi TRƯỚC khi chạy)

Hai thí nghiệm trước cho thấy WM2 bị giới hạn bởi nhãn yếu bỏ sót. Thử cho LLM gán nhãn câu train theo guideline 0.4.

**Ràng buộc:**
- Chỉ gửi câu **VietJobs** (bộ công khai, Pham Dinh et al., LREC 2026) ra API. Code chặn mọi câu không thuộc `vietjobs_it`; không gửi câu crawl TopCV/ITviec, không gửi câu TEST.
- Guideline gửi kèm bỏ phần quy trình, lịch sử, và mọi dòng ví dụ là chuỗi con của một câu `skill_test1` (3 dòng).
- Nhãn LLM là nhãn yếu: chỉ dùng để train, không bao giờ làm test.
- Ngân sách: tổng ≤ $3 (key OpenAI có sẵn). Bước thử dừng nếu vượt $0,50.

**Bước thử (dev `skill_batch1`, 300 câu VietJobs):**
- Gán bằng `gpt-6-luna` và `gpt-6.1-sol`, mỗi lần 20 câu, reasoning effort thấp.
- Chấm như nhãn yếu từ tag và theo luật: seqeval strict so với nhãn tay. Mốc: nhãn yếu theo luật có P 0,812 / R 0,476 / F1 0,600.
- **Đi tiếp** nếu có mô hình đạt F1 ≥ 0,65 trên dev và chi phí ước cho toàn tập train vừa ngân sách; chọn mô hình rẻ nhất đạt mức này. Không mô hình nào đạt thì ghi lại và dừng.
- Dev đã dùng để chọn cấu hình nhiều lần; ở bước này nó chỉ đo chất lượng nhãn, không chọn tham số mô hình.

**Nếu đi tiếp (đăng ký phần train trước khi chạy, ghi ở mục kết quả bước thử):** gán toàn bộ câu train VietJobs, train PhoBERT theo công thức chuẩn (3 seed), chọn theo dev, chấm TEST một lần, quy tắc kết luận như DAPT.

**Dự đoán:** Sol đạt F1 0,65–0,75 trên dev; Luna thấp hơn, khoảng 0,55–0,65.

### Kết quả bước thử nhãn LLM trên dev (2026-11-19)

| Nhãn trên dev `skill_batch1` (300 câu, so với nhãn tay) | P | R | F1 | Chi phí ước |
|---|---|---|---|---|
| Nhãn yếu theo luật (tag + từ điển + luật) | 0,812 | 0,476 | 0,600 | 0 |
| `gpt-6-luna`, effort low | 0,864 | 0,834 | **0,849** | $0,006 |
| `gpt-6.1-sol`, effort low | 0,846 | 0,907 | **0,875** | $0,095 |

- Cả hai vượt xa mức đi tiếp 0,65; recall gần gấp đôi nhãn yếu mà precision không giảm.
- Token: 95k vào, phần lớn trúng cache (guideline); ra 8,5k (Luna) và 5,2k (Sol). Span không dò lại được trên token: 4 (Luna), 1 (Sol).
- Dự đoán sai theo chiều tốt: dự đoán Sol 0,65–0,75, Luna 0,55–0,65.
- Kiểm tra rò rỉ ngược: 2/300 câu dev chứa nguyên một ví dụ guideline; bỏ 2 câu đó thì Luna 0,846, Sol 0,873. Còn một phần lạc quan không đo được: nhiều quy tắc 0.3 được viết khi gán chính đợt dev này, nên nhãn LLM trên dev có thể khớp guideline tốt hơn trên câu lạ.
- Theo quy tắc đã đăng ký: chọn **Luna** (rẻ nhất đạt mức). Ước cho 20.659 câu train VietJobs: ~$0,45. Sol ước ~$6,5, vượt ngân sách $3.

**Đăng ký trước bước train (ghi TRƯỚC khi gán tập train):**
- Nhãn `wm2_weak_llm` = file bản self-training, thay nhãn của mọi câu VietJobs (20.659 câu) bằng nhãn Luna. Câu TopCV (3.485 câu) giữ nhãn self-training, vì không được gửi ra API.
- Train PhoBERT công thức chuẩn (lr 3e-5, 3 epoch, bs 16, neg_ratio 0,3, hệ số O 1), seed 1–3, chọn epoch theo dev.
- Chỉ chấm TEST nếu dev trung bình > 0,644; chấm `skill_test1` một lần, so ghép cặp với bản self-training. Quy tắc kết luận như DAPT: "tốt hơn" chỉ khi CI95 của ΔF1 > 0 ở cả 3 seed; khi đó image `skill-extractor` đổi sang bản nhãn LLM.
- Dự đoán: dev 0,68–0,75; TEST tăng +0,03 đến +0,08, chủ yếu nhờ recall. TEST là câu TopCV, khác nguồn với nhãn LLM, nên phần tăng có thể nhỏ hơn dev.

### Kết quả PhoBERT trên nhãn LLM `wm2_weak_llm` (2026-11-19, chạy và chấm TEST một lần theo đăng ký trên)

**Gán nhãn:**
- `gpt-6-luna` gán 20.659 câu train VietJobs, ~$0,43, khoảng 1 giờ 50 phút.
- 94 span không dò lại được trên token, đã bỏ.
- Code chặn 3.485 câu TopCV, giữ nhãn self-training.
- Bản nhãn LLM có 8.859 câu có kỹ năng và 21.891 span; bản self-training có 7.350 câu và 16.282 span.
- Tổng chi phí API cả thí nghiệm (thử + gán) ~$0,54, tính từ số token và giá trang tổng hợp. Chưa đối chiếu hóa đơn OpenAI.

| | Dev F1 (seed 1 / 2 / 3) | TB dev | TEST P | TEST R | TEST F1 (seed 1 / 2 / 3) | TB TEST |
|---|---|---|---|---|---|---|
| từ điển | | | | | | 0,442 |
| PhoBERT self-training | | 0,644 | | | 0,616 / 0,618 / 0,617 | 0,617 |
| **PhoBERT nhãn LLM** | 0,794 / 0,801 / 0,796 | **0,797** | 0,725 | 0,734 | 0,729 / 0,727 / 0,734 | **0,730 ± 0,004** |

**So ghép cặp với bản self-training cùng seed (bootstrap theo tin, 1.000 lần):**
- Seed 1: ΔF1 +0,113 [+0,084; +0,144]
- Seed 2: ΔF1 +0,109 [+0,080; +0,138]
- Seed 3: ΔF1 +0,117 [+0,089; +0,147]
- So với từ điển: +0,284 đến +0,292.

**Kết luận theo quy tắc đã đăng ký:**
- Bản nhãn LLM **tốt hơn** bản self-training: CI95 nằm hẳn trên 0 ở cả 3 seed.
- Theo quy tắc, image `skill-extractor` đổi sang PhoBERT nhãn LLM (seed 1). Đã build lại bản full 0.2.0 ngày 2026-11-19 và chạy thử trên 30 tin cục bộ; xem `models.yaml`.

**Kiểm tra rò rỉ:**
- 30 câu TEST trùng nguyên văn một câu train, giống lần kiểm tra trước. Ở bản nhãn LLM, nhãn train của các câu này do LLM gán theo cùng guideline với nhãn vàng, nên đã chấm lại trên 970 câu còn lại.
- Kết quả trên 970 câu: bản nhãn LLM 0,729 / 0,728 / 0,736 (TB 0,731); bản self-training TB 0,620. Phần tăng không đến từ câu trùng.

**Đối chiếu dự đoán:**
- Dev: dự đoán 0,68–0,75, thực tế 0,797, cao hơn.
- TEST: dự đoán +0,03 đến +0,08, thực tế +0,113, cao hơn.
- Phần tăng đến từ cả hai phía:
  - Recall tăng từ 0,53 lên 0,73.
  - Precision tăng từ khoảng 0,70 lên 0,725. Các cách trước đều đổi precision lấy recall; cách này thì không.
- Chênh dev–TEST còn 0,067 (bản self-training là 0,027). Phần chênh có thể do nhãn LLM trên câu VietJobs khớp dev (cũng là VietJobs) hơn câu TopCV.

**Ý nghĩa cho báo cáo:**
- Hai thí nghiệm âm tính trước (DAPT, hệ số O) và thí nghiệm này cùng chỉ ra: chất lượng nhãn train là nút thắt của WM2.
- Thay nhãn yếu từ tag và từ điển bằng nhãn LLM theo guideline nâng F1 TEST từ 0,617 lên 0,730, với chi phí dưới $1.

**Hạn chế:**
- Nhãn LLM vẫn là nhãn yếu: F1 so với nhãn tay trên dev là 0,849.
- Chỉ dùng một mô hình LLM, một lần gán, không đo độ ổn định giữa các lần gán.
- Giá là ước lượng. Kết quả phụ thuộc dịch vụ ngoài: tái lập cần cùng phiên bản mô hình, nên file nhãn `train_luna.bio.jsonl` phải được giữ lại (không commit; lưu cùng dữ liệu).
- Repo chưa commit lúc chấm (`ie/llm_label.py`, `ie/weak_llm.py`); ghi gitsha khi commit.

Lệnh:

    uv run python -m ie.llm_label --model gpt-6-luna --bio data/annotation/skill_batch1.bio.jsonl --name dev_gpt-6-luna --eval
    uv run python -m ie.llm_label --model gpt-6-luna --bio data/weak/wm2_weak_selftrain.bio.jsonl --name train_luna --budget 1.0
    uv run python -m ie.weak_llm --llm data/llm/train_luna.bio.jsonl
    uv run python -m ie.phobert train --weak llm --seed <N>
    uv run python -m ie.phobert eval --weak llm --model data/models/wm2-phobert-llm-s<N> \
        --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --seed <N>
    uv run python -m experiments.paired_wm2 --bio data/annotation/skill_test1.bio.jsonl --prefix wm2-phobert-llm \
        --out data/eval/skill_test1_preds_llm.json --against data/eval/skill_test1_preds_selftrain.json

## Self-training trên nhãn LLM – đăng ký trước (2026-11-20, ghi TRƯỚC khi chạy)

Câu TopCV trong tập train (3.485 câu) không được gửi ra API nên vẫn mang nhãn self-training cũ. Thử dùng chính
mô hình nhãn LLM để bổ sung nhãn, không gửi dữ liệu nào ra ngoài.

- Ba mô hình nhãn LLM (seed 1–3) đoán lại toàn bộ câu train; span nào **cả ba cùng đoán**, không chồng span sẵn có
  và không bị luật guideline 0.4 loại thì được thêm vào nhãn (cách self-training đã dùng trước đây, không bỏ span nào).
  Bộ nhãn mới gọi là `llmself`.
- Train PhoBERT công thức chuẩn (lr 3e-5, 3 epoch, bs 16, neg_ratio 0,3, hệ số O 1), seed 1–3, chọn epoch theo dev.
- Chỉ chấm TEST nếu dev trung bình > 0,797 (mức của mô hình nhãn LLM). Chấm `skill_test1` một lần, so ghép cặp với
  mô hình nhãn LLM cùng seed (bootstrap theo tin, 1.000 lần).
- "Tốt hơn" chỉ khi CI95 của ΔF1 > 0 ở cả 3 seed; khi đó image đổi. Không thì giữ image 0.2.0.
- Dự đoán: dev +0,00 đến +0,01; nhiều khả năng không qua ngưỡng dev hoặc "không khác biệt" trên TEST, vì nhãn LLM đã
  bắt phần lớn kỹ năng (lần self-training trước chỉ thêm 0,002 dev).

### Kết quả self-training trên nhãn LLM (2026-11-20, chạy và chấm TEST một lần theo đăng ký trên)

- Ba mô hình nhãn LLM cùng đoán thêm **2.259 span** (24.144 câu train; 9.974 câu có kỹ năng). Span thêm nhiều nhất:
  AI (39), ERP (26), quản lý dự án (19), thiết kế hình ảnh (19), UI (18).
- Dev: 0,811 / 0,821 / 0,804, **trung bình 0,812** > 0,797 → đem sang TEST theo đăng ký.

| Seed | TEST P | TEST R | TEST F1 | F1 mô hình nhãn LLM | ΔF1 (CI95, bootstrap theo tin) |
|---|---|---|---|---|---|
| 1 | 0,724 | 0,734 | 0,729 | 0,729 | +0,000 [−0,012; +0,012] |
| 2 | 0,735 | 0,743 | 0,739 | 0,727 | +0,013 [+0,001; +0,025] |
| 3 | 0,728 | 0,744 | 0,736 | 0,734 | +0,002 [−0,013; +0,017] |

- **Kết luận theo quy tắc đã đăng ký: không tốt hơn** (CI chứa 0 ở seed 1 và 3). Trung bình 0,735 so với 0,730.
  Image giữ 0.2.0. Đúng dự đoán: dev tăng nhẹ, TEST gần như không đổi.
- Thêm span đồng thuận chủ yếu là từ chung ("AI", "UI") – đúng loại mà phân tích lỗi cho thấy mô hình đã hay báo
  thừa, nên không giúp precision.

Lệnh: `bash data/logs/run_llmself.sh` (self_train `--src llm --dst llmself` + train 3 seed);
`uv run python -m ie.phobert eval --weak llmself --model data/models/wm2-phobert-llmself-s<N> --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --seed <N>`;
`uv run python -m experiments.paired_wm2 --bio data/annotation/skill_test1.bio.jsonl --prefix wm2-phobert-llmself --out data/eval/skill_test1_preds_llmself.json --against data/eval/skill_test1_preds_llm.json`

## Dữ liệu

> Dữ liệu chính là tin tự crawl (TopCV, ITviec). VietJobs chỉ dùng cho nhãn yếu, từ điển alias và baseline – không dùng làm tập test.

### VietJobs – tập IT `vietjobs_it` (2026-10-07)

- Nguồn: `dinhieufam/VietJobs`, revision `ea140511b77935704e93d21c2973b72f46d48902`, CSV sha256 `85862b06…c49d477`. Trích dẫn Pham Dinh et al., LREC 2026.
- Lọc `category == công_nghệ_thông_tin_kỹ_thuật_số`: 1.906 / 48.092 tin. Nhóm này có cả vị trí không kỹ thuật (kinh doanh, thiết kế đồ họa).
- Lệnh: `uv run python -m ie.vietjobs`

### Từ điển kỹ năng nháp (`ie/resources/skill_alias.csv`)

- 200 kỹ năng chuẩn, 442 cách viết (bản tự sinh, chưa xem tay).
- Từ điển phủ 54,9% số lần gắn tag `technical_skills` trong tập IT (phần còn lại là đuôi dài, 3.771 tag khác nhau).
- 84,4% số tag xuất hiện nguyên văn trong mô tả/yêu cầu. Đây là giới hạn trên cho nhãn yếu dạng span của WM2.
- Lệnh: `uv run python -m ie.skill_alias --top 200`

### Đợt gán nhãn kỹ năng 1 (`skill_batch1`)

- 1.507 câu từ 125 tin (seed 20261007), trong đó 153 câu của 12 tin được hai người gán để đo κ.
- Lệnh: `uv run python -m annotation.sample_skill_batch --sentences 1500`
- κ: `<...>` (153 câu `double` đã có nhãn người thứ nhất, chưa có người thứ hai)
- Vai trò (quyết định 2026-10-12): **dev set / luyện guideline**, gán đến ~300 câu thì dừng. Tập test WM2 lấy từ tin TopCV tự crawl.
- **Đã gán xong dev (2026-10-18):** 300 câu đầu (24 tin, 7.301 token), 1 người gán.
  - 129 câu có kỹ năng, 171 câu rỗng (57%); 294 span SKILL.
  - Gợi ý sẵn bằng từ điển (`annotation/preannotate_dict.py`, `dict-alias`) cho 300 câu chưa gán; 59 câu có gợi ý, người gán giữ nguyên 20 câu, sửa 39 câu.
  - Rà lại toàn bộ sau khi gán: sửa 13 câu sai hoặc lệch quy tắc; 15 span dính khoảng trắng/dấu câu ở mép được cắt tự động khi đổi BIO; 0 span lệch ranh giới token.
  - 9 câu tick "khó / cần bàn" → các quy tắc chốt vào guideline bản 0.3.
  - Lệnh: `uv run python -m annotation.export_bio --project 1 --batch skill_batch1` → `data/annotation/skill_batch1.bio.jsonl`.

## WM2 – trích kỹ năng

### Baseline từ điển trên dev `skill_batch1` (2026-10-18)

| Tập | Câu | Span vàng | P | R | F1 (seqeval strict) |
|---|---|---|---|---|---|
| dev `skill_batch1` | 300 | 294 | 0,869 | 0,361 | 0,510 |

- F1 khoảng tin cậy 95% (bootstrap 1.000 lần theo câu): [0,440; 0,582] – dev chỉ 300 câu nên khoảng còn rộng.
- **Cập nhật 2026-11-12 (nhãn dev sửa theo guideline 0.4, 3 câu; còn 290 span):** dict P 0,869 / R 0,365 / F1 0,515, CI95 [0,444; 0,584].
  PhoBERT (nhãn yếu `wm2_weak_tag`, 3 seed) chấm lại trên cùng dev: F1 0,596 ± 0,022; PhoBERT + từ điển: F1 0,606 ± 0,022.
  Lệnh: `uv run python -m ie.phobert eval --model data/models/wm2-phobert-tag-s<N> --eval-set skill_batch1 --split dev --seed <N>`; bảng: `uv run python -m experiments.aggregate --task WM2`.
  Các run cũ (nhãn dev bản 0.3) chuyển vào `experiments/runs/superseded-guideline-0.3/`.
- Lệnh: `uv run python -m ie.baseline_dict --bio data/annotation/skill_batch1.bio.jsonl --eval-set skill_batch1 --split dev` (ghi thêm `experiments/runs/<run_id>.json`)
- **P trên dev bị đẩy lên:** 257/300 câu được gợi ý sẵn bằng chính từ điển này trước khi người gán sửa, và từ điển dựng từ tag VietJobs cùng nguồn. Số chính thức phải đo trên test `skill_test1` (TopCV, gán không có gợi ý).
- Bỏ sót chủ yếu: (1) kỹ năng dạng cụm tiếng Việt không có trong từ điển (`vận hành máy CNC`, `vẽ tay`, `thiết kế thumbnail`, `mô hình dữ liệu`, `phân khúc khách hàng`); (2) tên công cụ ngoài top 200 (`Digiwin T100`, `IBM MQ`, `Katalon`, `Mastercam`, `ELK`); (3) một số alias thiếu dù có nhóm (`Agile`, `Scrum` khi viết "Agile/Scrum").
- Gán thừa: `API` (quá chung theo guideline), `C` đứng riêng, "Agile/Scrum" khớp thành một span thay vì hai, và lệch ranh giới (`React` trong "ReactJS…", `phân tích yêu cầu` khi người gán lấy cụm dài hơn).

### Nhãn yếu cho train PhoBERT `wm2_weak_tag` (2026-11-09)

- Cách gán: tag kỹ năng của chính tin (VietJobs `technical_skills`, TopCV `skill_tags`; bỏ kỹ năng mềm theo từ vựng
  `soft_skills` của VietJobs, bỏ tag > 5 token) cộng từ điển alias, dò khớp dài nhất trên token.
- Loại toàn bộ 250 tin thuộc dev `skill_batch1` và test `skill_test1` (theo job_uid trong manifest).
- Kết quả: 1.781 tin VietJobs + 179 tin TopCV → 24.144 câu, 6.438 câu có kỹ năng (27%), 14.390 span.
- Độ nhiễu, đo bằng cách áp cùng cách gán lên 300 câu dev đã gán tay (seqeval strict):

| Cách gán | P | R | F1 |
|---|---|---|---|
| Chỉ từ điển (= baseline) | 0,869 | 0,361 | 0,510 |
| Chỉ tag của tin | 0,757 | 0,180 | 0,291 |
| Tag + từ điển (dùng cho train) | 0,799 | 0,405 | 0,537 |

- Nhận xét: nhãn yếu bắt được ~40% kỹ năng thật → mô hình train trên đó dễ học thói "bỏ sót" (câu có kỹ năng nhưng bị
  gán toàn O). Hướng xử lý khi train: bỏ bớt câu không có span nào, hoặc chỉ tính loss trên token đã gán B/I.
- Lệnh: `uv run python -m ie.weak_labels` → `data/weak/wm2_weak_tag.bio.jsonl`

### Nhãn yếu theo luật `wm2_weak_rules` theo guideline 0.4 (2026-11-12)

- Thêm luật `ie/weak_rules.py`, lấy **từ guideline 0.4 và ví dụ trong guideline**, không lấy từ lỗi trên test:
  thêm ~120 khái niệm guideline coi là kỹ năng (wireframe/prototype, cloud/AI đứng riêng, loại kiểm thử, loại quản lý chính thức,
  nghiệp vụ ngành, cụm tiếng Việt có từ làm rõ); bỏ span thuộc danh sách "không gán" (tài liệu BA, thiết bị hạ tầng,
  bảo mật chung chung, từ chung, động từ chung + việc); tách span qua "/" trừ tên viết liền (CI/CD, UI/UX…);
  bỏ `AI`/`cloud` khi chỉ là bổ ngữ (`AI solutions`, "giải pháp AI").
- Cùng 1.960 tin, cùng loại trừ dev/test: 24.144 câu, 6.590 câu có kỹ năng, 14.969 span.
- Độ nhiễu trên dev (tag + từ điển, so với nhãn tay 0.4): bản nhãn tag P 0,799 / R 0,410 / F1 0,542 → **bản nhãn luật P 0,807 / R 0,476 / F1 0,599**.
- PhoBERT train trên bản nhãn luật (cùng siêu tham số với bản nhãn tag: lr 3e-5, 3 epoch, bs 16, neg_ratio 0,3; chọn epoch theo dev), chấm trên dev:

| Phương pháp (dev, 3 seed) | P | R | F1 |
|---|---|---|---|
| PhoBERT nhãn yếu từ tag | 0,792 | 0,478 | 0,596 ± 0,022 |
| PhoBERT nhãn yếu theo luật | 0,783 | 0,547 | **0,642 ± 0,030** |
| PhoBERT nhãn luật + từ điển | 0,775 | 0,560 | 0,648 ± 0,029 |

- Chủ yếu tăng recall (+0,07), precision gần như giữ nguyên. Epoch được chọn theo chính dev nên số dev hơi lạc quan cho cả bản nhãn tag lẫn bản nhãn luật.
- Lệnh: `uv run python -m ie.weak_labels --version rules`; `uv run python -m ie.phobert train --weak rules --seed <N>` (model ở `data/models/wm2-phobert-rules-s<N>`).

### Self-training `wm2_weak_selftrain` (2026-11-12)

- Ba model nhãn luật (seed 1–3) đoán lại chính tập train; span nào **cả ba cùng đoán**, không chồng span nhãn yếu sẵn có
  và không bị luật 0.4 loại thì được thêm vào nhãn. Không bỏ span nhãn yếu nào (chỉ nhằm giảm bỏ sót).
- Thêm 1.307 span → 16.282 span, 7.350/24.144 câu có kỹ năng. Span thêm nhiều nhất: `UX`, `thiết kế game`,
  `automation test`, `Zabbix`, `MLOps`, `ISO 27001`, `LangChain`, `ISTQB`, `Cypress` (phần lớn là tên hiếm nhãn yếu bỏ sót).

| Phương pháp (dev, 3 seed) | P | R | F1 |
|---|---|---|---|
| PhoBERT nhãn tag | 0,792 | 0,478 | 0,596 ± 0,022 |
| PhoBERT nhãn luật | 0,783 | 0,547 | 0,642 ± 0,030 |
| PhoBERT self-training | 0,813 | 0,533 | 0,644 ± 0,006 |
| PhoBERT self-training + từ điển | 0,801 | 0,546 | **0,649 ± 0,006** |

- F1 bản self-training ≈ bản nhãn luật (chênh 0,002, nhỏ hơn độ lệch giữa các seed) nhưng **ổn định hơn hẳn**: std 0,006 so với 0,030,
  và precision cao hơn (0,813 so với 0,783) đổi lấy recall thấp hơn chút. Self-training ở đây chủ yếu làm
  mô hình nhất quán giữa các seed, không mở rộng thêm độ phủ.
- Lệnh: `uv run python -m ie.self_train --src rules --dst selftrain --models wm2-phobert-rules-s1 wm2-phobert-rules-s2 wm2-phobert-rules-s3`;
  `uv run python -m ie.phobert train --weak selftrain --seed <N>`.
- **Chưa chấm trên test** – chờ chốt bản cuối (nhãn luật hay self-training) rồi chấm một lần.

## WM1 – thu thập và phát hiện tin trùng

### Code dedup hai tầng (2026-11-12)

- `crawler/dedup.py`: baseline khóa `tiêu đề + công ty` (chuẩn hóa, cắt đuôi quảng cáo "tuyển gấp", "lương upto…")
  và MinHash LSH trên shingle 3 từ của `title + description + requirements_text` (128 permutation).
- Chạy thử trên snapshot `topcv_20261012` (304 tin, **một nguồn** nên chỉ có tin đăng lại, chưa có tin trùng liên trang):

| Ngưỡng Jaccard | Số cặp ứng viên |
|---|---|
| baseline tiêu đề + công ty | 1 |
| MinHash ≥ 0,5 | 0 |
| MinHash ≥ 0,3 | 1 (Jaccard 0,41) |
| MinHash ≥ 0,2 | 6 |

- Cặp baseline duy nhất: hai tin "Nhân Viên IT Helpdesk" cùng một công ty, Jaccard nội dung thật 0,267 –
  tức **cùng vị trí nhưng mô tả viết lại**, đúng loại tin dedup cần bắt mà ngưỡng 0,5 bỏ sót.
- **Kết luận cho tập gán nhãn:** 304 tin một nguồn là quá ít (≈ 6 cặp ở ngưỡng 0,2). Phải crawl ITviec
  và crawl thêm TopCV trước khi rút 300 cặp; ngưỡng rút ứng viên nên hạ về **0,2** và lấy theo tầng.
- Lệnh: `uv run python -m crawler.dedup --snapshots data/crawl/topcv/topcv_20261012.parquet --out data/eval/dedup_topcv_20261012.csv`

### Crawl TopCV đợt 2 và chuẩn hóa tên công ty (2026-11-15)

**Crawl bị chặn lại ở 429.** Chạy `--max-jobs 200 --max-sitemaps 50 --since 2026-10-13`, 3,5 giây/request:

| Số liệu | Giá trị |
|---|---|
| `downloader/request_count` | 65 |
| `response_status_count/200` | 63 |
| `response_status_count/429` | **2** |
| `finish_reason` | `blocked_http_429` |
| Tin IT lưu được | 27 (0 lỗi parse, 26 tin bị loại vì không phải IT) |
| Thời gian | 227 giây |

Spider tự dừng đúng quy tắc, không thử lại, không chạy lại trong ngày. **Giới hạn thật của TopCV chặt hơn
1 request/3,5 giây**: lần 2026-10-12 trụ được hơn 600 request, lần này chặn ở 65. Kết luận cho kế hoạch:
mỗi ngày chỉ nên tính khoảng **25–60 tin TopCV**, không thể dựa vào TopCV để tăng dữ liệu nhanh.

**Chuẩn hóa tên công ty** (`norm_company` trong `crawler/dedup.py`): bỏ tiền tố/hậu tố pháp lý vì TopCV ghi
tên đầy đủ ("Công ty TNHH LG CNS Việt Nam") còn ITviec ghi tên thương hiệu ("LG CNS Việt Nam").
Công ty chung giữa hai nguồn: **4 → 9**.

**Snapshot `topcv_20261115`**: 331 tin, ids_sha256 `6f5e64cddb531131c1f863a800cfb75ccace20a055669adb6f60e4e0866cff7b`,
`date_posted` 2026-08-17 → 2026-10-24. (ITviec `itviec_20261113`: 536 tin, 2026-09-24 → 2026-11-12.)

### Cặp ứng viên trên hai nguồn (2026-11-15)

`uv run python -m crawler.dedup --snapshots data/crawl/topcv/topcv_20261115.parquet data/crawl/itviec-jobs/itviec_20261113.parquet --threshold 0.2 --out data/eval/dedup_pairs_cross.csv`

867 tin (itviec 536, topcv 331) → **371 cặp ứng viên**: baseline 5, MinHash ≥ 0,2 371, **khác nguồn chỉ 4**.
Jaccard: min 0,203, trung vị 0,328, max 1,000. Cùng công ty 366/371.

**27 tin TopCV mới không thêm được công ty chung nào và không thêm cặp khác nguồn nào.** Nguyên nhân gốc
không phải lệch thời gian mà là **hai nguồn gần như không chung khách hàng**: 331 tin TopCV + 536 tin ITviec
chỉ có 9 công ty chung (42 tin). ITviec là trang chuyên IT, khách hàng chủ yếu là công ty product/outsourcing;
TopCV là trang tổng hợp.

Chất lượng cặp theo dải Jaccard – đủ tốt để gán nhãn có ý nghĩa:

| Dải Jaccard | Số cặp | Loại cặp |
|---|---|---|
| 0,8–1,0 | 6 | tin trùng thật, kể cả **khác nguồn** (DevOps Engineer @ Con Cưng, 0,88) và **khác ngôn ngữ** (Kingfoodmart: "Product Business Analyst" ↔ "Chuyên viên Sản phẩm Phân tích Nghiệp vụ", 0,98); một cặp Jaccard 1,00 là tin đăng y nguyên hai lần trong TopCV |
| 0,5–0,8 | 22 | **cặp âm khó**: MB Bank dùng gần như cùng một mô tả cho "BackEnd Engineer Java" và "FullStack Developer Java, Go" (0,52–0,78) – khác vị trí thật |
| 0,2–0,3 | 138 | cặp âm: cùng công ty, dùng chung khung mô tả, vị trí khác hẳn (LG CNS, Bosch) |

Câu hỏi thực nghiệm của WM1 vì thế rõ ra: **phân biệt "tin đăng lại" với "cùng công ty, dùng chung khung
mô tả"**, chứ không phải chuyện tìm tin giống nhau nói chung. Đó là chỗ MinHash dễ sai nhất.

### Tập 300 cặp để gán nhãn (2026-11-15)

`uv run python -m annotation.sample_dedup_pairs --snapshots data/crawl/topcv/topcv_20261115.parquet data/crawl/itviec-jobs/itviec_20261113.parquet --n 300`

Số cặp có thể rút, theo tầng:

| Tầng | Số cặp | trong đó khác nguồn |
|---|---|---|
| `baseline` | 5 | 2 |
| `minhash_high` (≥ 0,5) | 26 | 1 |
| `minhash_low` (0,2–0,5) | 340 | 1 |
| `same_company` (thuật toán **không** đề xuất) | 795 | 78 |

Đã rút: 300 cặp, seed 20261113 – baseline 5, minhash_high 26, minhash_low 134, same_company 135,
**khác nguồn 82**. Tầng `same_company` là tầng đo **recall**: nếu chỉ gán cặp thuật toán đề xuất thì không
bao giờ biết thuật toán bỏ sót bao nhiêu. 82 cặp khác nguồn đủ để báo cáo riêng số liệu liên trang.

*(Đã gán xong 2026-11-18, kết quả ở mục dưới.)* Việc tiếp lúc đó: nhập `data/annotation/dedup_batch1.labelstudio.json` vào Label Studio
(cấu hình `annotation/label_studio_dedup.xml`), Hoang Le gán 300 cặp, Bốp gán 30 cặp để tính κ.

### Rút lại phần chưa gán: giới hạn lặp tin và công ty (2026-11-17)

Lúc gán, người gán thấy cùng một tin lặp lại nhiều lần. Kiểm tra thì đúng: tầng `same_company` ghép mọi tin
của một công ty với nhau, nên **MB Bank chiếm 72/300 cặp, LG CNS 73**, có tin nằm trong 12 cặp. Sửa
`pick`: mỗi tin tối đa 3 cặp, mỗi công ty tối đa 15 cặp cùng nguồn; không giới hạn tầng `baseline`,
`minhash_high` (nơi có cặp trùng) và cặp khác nguồn. Giữ nguyên 45 cặp đã gán (`--keep`), rút lại 255 cặp.
Sau sửa: 336 tin khác nhau (trước 232), MB Bank 21 cặp, LG CNS 17. Cặp khác nguồn 82 → 34, vì 60/82 cặp
khác nguồn cũ là của riêng LG CNS.

### Kết quả trên 300 cặp đã gán (2026-11-18)

Hoang Le gán đủ 300 cặp (project Label Studio 10, guideline 0.1). **15 cặp trùng** (4 khác trang), 4 cặp
tick "khó". Chưa có người thứ hai gán nên **chưa có κ**.

| Tầng | cỡ tầng | rút | trùng |
|---|---|---|---|
| baseline | 5 | 5 | 5 |
| minhash_high (J ≥ 0,5) | 26 | 26 | 7 |
| minhash_low (0,2 ≤ J < 0,5) | 340 | 134 | 2 |
| same_company | 795 | 135 | 1 |

Ngưỡng MinHash 0,5 **đặt trước khi có nhãn** (mặc định của `crawler.dedup`). CI95 bootstrap theo cặp, 2.000 lần.
Cột "có trọng số" nhân mỗi cặp với `cỡ tầng / số cặp rút`, ước lượng cho toàn bộ cặp (xấp xỉ).

| Hệ | P | R | F1 | F1 CI95 | P / R / F1 có trọng số |
|---|---|---|---|---|---|
| baseline tiêu đề + công ty | 1,000 | 0,333 | 0,500 | [0,160; 0,750] | 1,000 / 0,218 / 0,358 |
| MinHash J ≥ 0,5 | 0,321 | 0,600 | 0,419 | [0,216; 0,585] | 0,321 / 0,392 / 0,353 |
| **baseline ∪ MinHash ≥ 0,5** | 0,387 | **0,800** | **0,522** | [0,324; 0,679] | 0,387 / 0,523 / 0,445 |

Quét ngưỡng (chỉ đọc xu hướng – chọn ngưỡng trên chính tập này là lạc quan): F1 cao nhất 0,552 ở J ≥ 0,7
(P 0,571, R 0,533); J ≥ 0,9 cho P 1,000 nhưng R 0,267.

**Đọc kết quả:**
- **Baseline không bao giờ báo nhầm** (5/5) nhưng chỉ bắt 1/3 số cặp trùng. Gộp với MinHash thì recall lên
  0,800, đổi lại precision rơi xuống 0,387.
- **19/19 lỗi báo nhầm đều là hai tin khác vị trí của cùng một công ty** (MB Bank 8, ANDPAD, H3Tech…): đúng
  dự đoán ở mục "Cặp ứng viên". Mô tả tin dùng chung đoạn giới thiệu công ty và phúc lợi, nên Jaccard
  trên shingle lên tới 0,85 dù vị trí khác hẳn ("Principal Android Native Engineer" và "Principal iOS
  Native Engineer"). MinHash đang đo "cùng mẫu tin của công ty", chưa đo "cùng tin".
- **Khác trang: 4 cặp trùng, bắt được 3** (P 1,000, R 0,750). Cặp bỏ sót (FINPROS, "Data Science Intern
  On-site" và "Data Science Intern") có **J = 0,03**: hai trang viết mô tả khác hẳn, và baseline trượt vì
  chữ "On-site". So nội dung không cứu được loại này; cần so tiêu đề mềm hơn.
- **Số rất nhỏ:** 15 cặp trùng, CI của F1 rộng ~0,35. Kết luận chắc chắn được là chiều lỗi (báo nhầm do mẫu
  tin chung của công ty), chưa phải con số F1.

**Hướng cải thiện (chưa làm, cần tập riêng để chọn tham số):** bỏ shingle lặp ở nhiều tin của cùng công ty
trước khi tính MinHash (khử phần "khung" của công ty); so khớp tiêu đề mềm (bỏ "On-site", "Remote", cấp bậc
gộp). Muốn chọn tham số cho hai việc này mà không chạm 300 cặp thì phải gán thêm một lô dev.

Lệnh: `uv run python -m crawler.eval_dedup --from-ls 10` (lưu nhãn vào `data/annotation/dedup_batch1.labels.jsonl`),
sau đó `uv run python -m crawler.eval_dedup`.

### Đăng ký trước: dedup cắt khung – cắt khung công ty + so tiêu đề mềm (2026-11-18, ghi TRƯỚC khi chạy)

Mục này viết trước khi chạy bất kỳ phép đo nào của bản cắt khung. Mọi tham số chọn theo lý lẽ, **không chỉnh theo điểm
trên 300 cặp**. Chạy đúng một lần; kết quả ra sao báo vậy, kể cả khi kém hơn bản MinHash. Muốn chỉnh tiếp thì phải
gán lô dev riêng.

1. **Cắt khung công ty** (sửa báo nhầm): nhóm tin theo (nguồn, `norm_company`). Nhóm có **≥ 3 tin** thì bỏ
   mọi shingle xuất hiện ở **≥ 50% số tin của nhóm**, trước khi tính MinHash. Cắt xong rỗng thì dùng lại
   tập shingle đầy đủ. Ngưỡng MinHash giữ **0,5**.
2. **Tiêu đề mềm** (sửa bỏ sót): trước khóa baseline, bỏ các từ chỉ hình thức làm việc và địa điểm
   (`on-site`, `onsite`, `remote`, `hybrid`, `wfh`, `work from home`, `hà nội`, `ha noi`, `hanoi`, `hn`,
   `hồ chí minh`, `ho chi minh`, `hcm`, `tp hcm`, `tphcm`, `sài gòn`, `saigon`, `đà nẵng`, `da nang`,
   `danang`, `việt nam`, `vietnam`, `tại`). **Giữ cấp bậc**: guideline coi Junior và Senior là khác tin.
3. **Hệ chính (cắt khung)** = baseline mềm ∪ MinHash cắt khung ≥ 0,5. So với hệ MinHash (baseline ∪ MinHash ≥ 0,5
   = F1 0,522) bằng bootstrap ghép cặp ΔF1, 2.000 lần, theo cặp. Báo cả từng thành phần riêng lẻ.

### Kết quả dedup cắt khung – chạy một lần theo đăng ký trước (2026-11-18)

Cùng 300 cặp, cùng nhãn, tham số đúng như mục đăng ký ở trên, không chỉnh gì sau khi xem số.

| Hệ | P | R | F1 | F1 CI95 | P / R / F1 có trọng số |
|---|---|---|---|---|---|
| MinHash: baseline ∪ MinHash ≥ 0,5 | 0,387 | 0,800 | 0,522 | [0,324; 0,679] | 0,387 / 0,523 / 0,445 |
| baseline mềm | 1,000 | 0,400 | 0,571 | [0,250; 0,800] | 1,000 / 0,474 / 0,643 |
| MinHash cắt khung ≥ 0,5 | 0,533 | 0,533 | 0,533 | [0,276; 0,732] | 0,484 / 0,348 / 0,405 |
| **Cắt khung: baseline mềm ∪ MinHash cắt khung ≥ 0,5** | **0,611** | 0,733 | **0,667** | [0,444; 0,829] | 0,650 / 0,692 / 0,671 |

**ΔF1 cắt khung − MinHash = +0,145, CI95 [−0,020; +0,304]**, p(Δ ≤ 0) = 0,044. Khoảng tin cậy hai phía vẫn chứa 0
nên **chưa đủ để nói chắc bản cắt khung hơn bản MinHash**; chiều tăng thì nhất quán (ước lượng có trọng số 0,445 → 0,671).

- **Báo nhầm 19 → 7.** Cắt khung công ty làm đúng việc của nó ở phần lớn cặp. 6/7 cặp còn lại vẫn là
  hai vị trí của cùng công ty, khác nhau ở mảng kỹ thuật (Android/iOS, Java/PHP) hoặc cấp bậc, nằm trong
  phần mô tả riêng chứ không phải khung.
- **Khác trang: bắt đủ 4/4** (FINPROS nhờ tiêu đề mềm), P 0,800 (1 báo nhầm: LG CNS "Senior SAP FI
  Consultant – Tax & VAT" và "SAP FI Consultant").
- **Tác dụng phụ – bỏ sót 3 → 4, và có một lỗi mới do chính cách cắt.** GON TECH có 3 tin, trong đó 2 tin
  là một (tiêu đề đảo thứ tự "Middle/Senior Backend Engineer Python" và "Backend Engineer Python -
  Middle/Senior"). Phần chung của hai tin trùng xuất hiện ở 2/3 = 67% số tin của công ty → bị coi là khung
  và cắt hết: Jaccard 0,79 → **0,00**. Nghĩa là **tin trùng tự làm mình thành "khung"** ở công ty ít tin.
  Cách sửa có lý (chưa làm, vì đã hứa không chỉnh trên tập này): đếm khung trên các tin *khác tiêu đề*,
  hoặc nâng ngưỡng số tin tối thiểu của một công ty.

Lệnh: `uv run python -m crawler.eval_dedup` (in cả `J` và `J_cắt` cho từng cặp lỗi).

### Đồng thuận hai người gán WM1: κ = 0,733 (2026-11-18)

Người 2 (Bốp) gán 30 cặp trên project riêng (Label Studio 11), không thấy nhãn người 1. Lô **làm giàu cặp
trùng có chủ đích**: cả 15 cặp người 1 gán "trùng", các cặp tick "khó", phần còn lại rút ngẫu nhiên trong
cặp "không trùng" theo tầng (`annotation/kappa_dedup.py`, seed 20261118). κ đo trên lô này, không phải trên
phân bố 5% trùng của 300 cặp.

- Khớp 26/30. Người 1 gán trùng 15, người 2 gán 11. **κ = 0,733, CI95 [0,493; 0,933]** (bootstrap theo cặp).
- **Cả 4 cặp lệch đều cùng một chiều: người 1 gán "trùng", người 2 gán "không trùng".** Người 1 dễ dãi hơn:

| Cặp | Kiểu | Guideline 0.1 nói gì |
|---|---|---|
| Biplus: "IT Comtor – Tiếng Thái" và "– Tiếng Indonesian" (người 1 tick "khó") | khác yêu cầu ngôn ngữ | gần mục 6 (khác công nghệ chính → không trùng) |
| MB Bank: "Middle, Senior BackEnd Engineer" và "All Level BackEnd Engineer" | khác dải cấp bậc | mục 5 và 11 → không trùng |
| MB Bank: "AI Software Engineer … AI Agents" và "Agentic Engineer … Backend AI Agents" | tiêu đề khác, cùng nhóm | chưa có quy tắc |
| Hải Long, khác trang: "Trưởng Nhóm Hạ Tầng Và Bảo Mật CNTT" và "Infrastructure Security Manager" | Việt / Anh, tên chức danh lệch | mục 3 (Việt/Anh cùng vị trí → trùng), nhưng "trưởng nhóm" ≠ "manager"? |

Hệ quả: số cặp trùng trong 300 cặp **phụ thuộc người gán, khoảng 11–15**, và mọi P/R/F1 của WM1 ở trên tính
theo nhãn người 1 (dễ dãi hơn). Cần chốt guideline 0.2 cho 4 kiểu trên rồi chấm lại; báo cả hai bộ số.

Lệnh: `uv run python -m annotation.kappa_dedup score --from-ls 11`.

### Chấm lại WM1 theo nhãn guideline 0.2 (2026-11-18)

Người 1 gán lại **mù** 47 cặp trên project riêng (Label Studio 12, không thấy nhãn cũ): mọi cặp đã gán
"trùng", mọi cặp tick "khó", mọi cặp khác trang. Lô chọn theo nhãn và nguồn, không theo dự đoán của hệ.
253 cặp còn lại giữ nhãn 0.1. File nhãn: `dedup_batch1.relabeled.jsonl`.

**Đổi 4 nhãn, số cặp trùng 15 → 13 (5 khác trang):**

| index | Cặp | 0.1 → 0.2 |
|---|---|---|
| 95 | MB Bank: "AI Software Engineer … AI Agents" / "Agentic Engineer … Backend AI Agents" | trùng → không trùng |
| 64 | MB Bank: "Middle, Senior BackEnd Engineer" / "All Level BackEnd Engineer" | trùng → không trùng |
| 90 | Biplus: "IT Comtor – Tiếng Thái" / "– Tiếng Indonesian" | trùng → không trùng |
| 148 | LG CNS, khác trang: "Senior SAP FI Consultant – Tax & VAT" / "SAP FI Consultant" | không trùng → trùng |

Ba cặp đầu chính là ba trong bốn cặp lệch κ, nay theo người 2. Cặp Hải Long (Việt/Anh) giữ "trùng".

**Cả hai bộ số** (cùng 300 cặp, cùng hệ, không chỉnh tham số):

| Hệ | Nhãn 0.1: P / R / F1 | Nhãn 0.2: P / R / F1 | F1 CI95 (0.2) | F1 có trọng số 0.1 → 0.2 |
|---|---|---|---|---|
| baseline title+company | 1,000 / 0,333 / 0,500 | 1,000 / 0,385 / 0,556 | [0,200; 0,800] | → 0,385 |
| MinHash: baseline ∪ MinHash ≥ 0,5 | 0,387 / 0,800 / 0,522 | 0,323 / 0,769 / 0,455 | [0,250; 0,621] | 0,445 → 0,385 |
| Cắt khung: baseline mềm ∪ MinHash cắt khung ≥ 0,5 | 0,611 / 0,733 / 0,667 | 0,556 / 0,769 / 0,645 | [0,417; 0,815] | 0,671 → 0,724 |

- **ΔF1 cắt khung − MinHash = +0,191, CI95 [+0,014; +0,369]**, p(Δ ≤ 0) = 0,018 (nhãn 0.1: +0,145, CI [−0,020; +0,304]).
  Theo nhãn 0.2 khoảng tin cậy không còn chứa 0. Cần đọc cẩn thận: chênh lệch chủ yếu đến từ việc đổi nhãn
  cặp 95 và 64 (cả bản MinHash và bản cắt khung đều báo trùng, nay thành báo nhầm, bản MinHash mất nhiều hơn vì P thấp hơn), không phải
  từ thay đổi của hệ. Nên báo cả hai bộ số, không chọn bộ đẹp hơn.
- Khác trang: bản cắt khung bắt **5/5, không báo nhầm** (cặp LG CNS trước là báo nhầm, nay là trùng).
- Cùng trang: bản cắt khung P 0,385 R 0,625. 8 báo nhầm, phần lớn là MB Bank: hai tin **mô tả gần như y hệt**
  (J_cắt 0,95–0,98) nhưng khác cấp bậc hoặc khác tiêu đề. Đây là giới hạn của so khớp văn bản: chỗ khác
  nhau nằm ở vài chữ trong tiêu đề.
- **Một điểm cần ghi:** cặp 95 có J_cắt = 0,98, tức phần nhiệm vụ gần như trùng khít, nhưng nhãn 0.2 là
  "không trùng". Quy tắc 8 (tiêu đề khác → quyết theo mô tả) lẽ ra cho "trùng". Không sửa nhãn sau khi đã
  chấm; ghi lại như một chỗ guideline chưa rõ (khi mô tả giống mà tiêu đề nói hai vai trò khác nhau).

Lệnh: `uv run python -m annotation.kappa_dedup merge --from-ls 12`,
`uv run python -m crawler.eval_dedup --labels data/annotation/dedup_batch1.relabeled.jsonl`.

### Crawl nhắm đúng đích theo trang công ty (chuẩn bị, 2026-11-15)

Quét sitemap cho ra tin rải khắp các công ty nên hai nguồn gần như không chung công ty – crawl thêm theo
cách đó không sửa được. Cách khác: **lấy công ty đã biết có mặt ở cả hai trang, vào trang công ty của họ
trên TopCV và lấy hết tin ở đó.**

Mỗi trang tin TopCV đều trỏ về `https://www.topcv.vn/cong-ty/<slug>/<id>.html`. Dựng được bảng
"tin → trang công ty" từ **HTML đã lưu trên máy, 0 request**: đủ cho 333/333 trang đã lưu, ra 258 công ty.

`uv run python -m crawler.topcv.shared_companies` → 9/9 công ty chung đều có trang công ty:

| Công ty | tin TopCV | tin ITviec |
|---|---|---|
| lg cns việt nam | 6 | 10 |
| fpt software | 4 | 2 |
| digital innovation | 2 | 1 |
| globaltech, con cưng, finpros, edufit, ntq solution | 1 mỗi | 2 mỗi |
| cmc openai | 1 | 1 |

Spider mới `crawler/topcv/company_spider.py`: **không lọc slug IT** (đã biết công ty có trên ITviec nên
lấy hết tin, tin trùng liên trang hay viết tiêu đề khác nhau), lấy link tin **theo mẫu URL chứ không theo
class CSS** (class TopCV đổi thường xuyên; mẫu `/viec-lam/<slug>/<id>.html` thì ổn định). Dùng chung
`seen_ids.txt` nên không tải lại tin đã có. Giữ nguyên `POLITE_SETTINGS`.

Ước lượng cho lần chạy tới: 9–27 request danh sách + tối đa 50 request tin. Vừa trong hạn ~65 request/ngày.

Test: fixture HTML **tự soạn** `tests/fixtures/topcv/company_page.html` (có cố ý thêm link công ty khác,
link lặp, link `/xem-cv/` bị chặn) – 9 test, chưa gửi request nào tới TopCV.

`crawler/topcv/probe_robots.py` gửi **đúng 1 request** đọc robots.txt và kết luận `/cong-ty/<slug>/<id>.html`
có được phép hay không, cùng `Crawl-delay` mà robots yêu cầu. Phải chạy script này **trước** spider:
`/cong-ty/` là đường dẫn chưa từng crawl.

Việc cho ngày mai (TopCV hôm nay đã trả 429, không chạm nữa): `probe_robots` → nếu được phép thì
`run_companies --max-jobs 50`.

## WM3 – review công ty ITviec

### Crawl thăm dò và đo thiên lệch (2026-11-12)

- **robots.txt ITviec** (xem 2026-11-12): chỉ `Disallow: /subscriptions/new`, không cấm trang review, không có `Crawl-delay`.
  Sitemap chính thức `twinnings_companies_review_vn.xml`: **12.422 trang review** `/nha-tuyen-dung/<slug>/danh-gia`.
- **Đã crawl 19 request** (1 robots + 1 sitemap + 17 trang), tất cả HTTP 200, không bị chặn, 3 giây/request.

**Phát hiện 1 – review bị che chứa văn bản giả.** Mỗi trang hiện 10 review nhưng chỉ **1 review công khai**;
9 review còn lại nằm trong `div.details-review.blur` với **cùng một đoạn văn giả ở mọi công ty**
("The salary is really good, the manager always tries to increase my salary…"). Parser phải loại chúng
(review thật dùng `<h4>Điều tôi thích:</h4>`, khối bị che dùng `<p>`), nếu không tập WM3 sẽ toàn câu giả.
Có test riêng (`tests/test_itviec_parser.py::test_khong_lay_van_ban_gia_cua_khoi_bi_che`).

**Phát hiện 2 – trang 2 không có review công khai.** `ntt-data-vietnam` (43 review): trang 1 cho 1 review,
trang 2 cho 0 → **1 review công khai mỗi công ty**, không lật trang được.

**Phát hiện 3 – điểm sao của review bị che vẫn hiện** → đo được thiên lệch mà không cần đăng nhập:

| Chỉ số (17 trang, 14 công ty) | Giá trị |
|---|---|
| Công ty có review công khai | 7/14 (6/6 công ty IT lớn, 0/8 công ty rút ngẫu nhiên từ sitemap) |
| Review công khai / bị che (chỉ có sao) | 7 / 73 |
| Số câu mỗi review công khai | trung bình **6,1** (từ 2 đến 11) |
| Sao trung bình review công khai | **4,57** |
| Sao trung bình review bị che | **3,82** |
| Chênh lệch trong cùng công ty | **+0,62 sao** (7 công ty) |
| Tháng của review công khai | 2026-03 … 2026-11 |

- Review xếp theo **thời gian giảm dần**, không theo điểm sao (ntt-data: 2026-10 → 2020-10), nên ITviec không
  đẩy review khen lên đầu. Nhưng review mới nhất **tích cực hơn** phần còn lại +0,62 sao → tập WM3 sẽ lệch
  về phía tích cực và về thời gian gần đây. Phải ghi vào hạn chế, kèm đúng con số này.
- **Ước lượng khối lượng:** 6,1 câu/công ty → cần **~165 công ty có review** để đủ 1.000 câu.
  Lấy ngẫu nhiên từ sitemap thì 0/8 có review → phải chọn công ty IT lớn, không rút ngẫu nhiên.
- Lệnh: `uv run python -m crawler.itviec.sitemap --fetch --out <file>`;
  `uv run python -m crawler.itviec.run --companies-file <file> --max-pages 1`;
  `uv run python -m crawler.itviec.coverage` (đo lại từ HTML đã lưu, không gửi request).

### Crawl đợt 1 – 200 công ty (2026-11-12)

**Chọn công ty:** rút ngẫu nhiên từ sitemap cho 0/8 công ty có review → chuyển sang lọc qua
`twinnings_jobs_desc_vn.xml` (615 tin IT đang mở): tách slug công ty từ URL việc làm được
**304 công ty đang tuyển IT**, không tốn request nào. Crawl 200 công ty đầu (xếp theo số tin đang tuyển).

| Chỉ số | Giá trị |
|---|---|
| Trang crawl | 200 (tất cả HTTP 200, 6,4 giây/trang, không bị chặn) |
| Công ty **có** review công khai | **104 / 200 (52%)** |
| Review công khai | 108 (gồm 7 lần thử trước), **1 review/công ty** |
| **Tổng số câu** | **553** – 382 câu "Điều tôi thích", 171 câu "Đề nghị cải thiện" |
| Bản ghi điểm sao (`review_ratings.jsonl`) | 912, trong đó **808 review bị che** |
| Số câu mỗi review | trung bình 5,1 |

**ITviec CHỌN review tích cực, không xếp theo thời gian.** (Kết luận "xếp theo thời gian" ở mục trên
dựa trên 1 công ty là sai; 104 công ty cho kết quả khác.)

| | Review công khai | Review bị che |
|---|---|---|
| "Không khuyến khích" | **0 / 104** | 147 / 808 (18%) |
| Review 1 sao / 2 sao | **0 / 0** | 14 / 40 |
| Sao trung bình | 4,41 | 4,15 |
| Là review mới nhất của công ty | 61% | – |
| Có sao cao nhất trang | 56% | – |

- Nếu chọn ngẫu nhiên, xác suất cả 104 review công khai đều "Khuyến khích" ≈ 0,82¹⁰⁴ ≈ 10⁻⁹ → **chọn có chủ đích**.
- Chênh lệch thật trong cùng công ty: **+0,27 sao** (n=104, sd 0,67) – nhỏ hơn +0,62 đo trên 7 công ty ở mục trên.
- **Bài vẫn làm được nhờ phần "Đề nghị cải thiện"**: 106/108 review có phần này, và nó chê thật dù review 4–5 sao
  ("Lương tăng khá chán… như tăng auto chứ không có sếp review lương" – review 5 sao).
  Cấu trúc 2 phần cũng cho **nhãn yếu** mạnh hơn điểm sao: câu phần "thích" thiên `positive`, phần "góp ý" thiên `negative`.
  Có ngoại lệ ngược chiều nên guideline quy định gán theo nội dung câu, không theo phần (xem `annotation/guideline_absa.md` mục 3).
- **Hạn chế:** thiếu câu phê phán nặng; lớp `negative` sẽ ít mẫu → báo macro-F1 kèm số lượng từng lớp.

### Crawl đợt 2 và tổng kết dữ liệu WM3 (2026-11-13)

Crawl nốt 104 công ty còn lại trong danh sách 304 công ty đang tuyển IT (104 trang, tất cả HTTP 200):
36 review mới, 329 bản ghi điểm sao. **Đã crawl hết danh sách.**

| Chỉ số (gộp cả 2 đợt) | Giá trị |
|---|---|
| Trang crawl | 304 + 17 trang thăm dò |
| **Review công khai** | **144** (1 review/công ty, 144 công ty khác nhau) |
| Tỷ lệ công ty có review | 144 / 304 (47%) |
| **Tổng số câu** | **779** – 543 câu "Điều tôi thích", 236 câu "Đề nghị cải thiện" |
| Bản ghi điểm sao | **1.241**, trong đó 1.100 review bị che |
| Review có tiếng Việt | 116 / 144 (81%); còn lại thuần tiếng Anh |
| Phân bố sao công khai | 3 sao: 14, 4 sao: 55, 5 sao: 72 (**không có 1–2 sao**) |
| "Không khuyến khích" | **0 / 141** |
| Chênh lệch sao cùng công ty | **+0,27** (n=141, không đổi so với đợt 1) |

- **Chốt khối lượng gán nhãn WM3: ~779 câu** thay vì 1.000 như kế hoạch ban đầu. Đã dùng hết nguồn công ty
  đang tuyển IT; crawl ngoài danh sách này thì tỉ lệ có review rất thấp (0/8 khi rút ngẫu nhiên).
- Snapshot dữ liệu: `data/crawl/itviec/2026-11-12/` và `2026-11-13/` (reviews.jsonl + review_ratings.jsonl).
- Việc tiếp theo: tách câu → tạo project Label Studio cho ABSA → gán thử 50 câu → chốt guideline 0.2.

### Tách câu và baseline từ điển (2026-11-15)

`uv run python -m absa.split` – 144 review công khai → **942 câu**.

| Chia theo | Số câu |
|---|---|
| ngôn ngữ | tiếng Việt 698, tiếng Anh 244 |
| phần review | `liked` 572, `improvement` 245, `title` 125 |

Hai chỗ phải xử lý riêng, ghi lại để báo cáo:
1. **Gạch đầu dòng.** Người viết review ITviec liệt kê "- Đồng nghiệp thân thiện. - Lương thấp.";
   `underthesea.sent_tokenize` không cắt ở dấu "-" nên phải cắt gạch đầu dòng trước rồi mới tách câu.
2. **Hai ngôn ngữ.** 244/942 câu tiếng Anh. PhoBERT chỉ hiểu tiếng Việt → phải báo cáo metric riêng
   từng ngôn ngữ, không gộp một số.

Câu ngắn hơn 15 ký tự hoặc không có chữ cái bị bỏ ("- ", "N/A", ":))").

**Baseline từ điển** (`absa/lexicon.py`, 153 cụm khía cạnh + 100 cụm cảm xúc, cả Việt và Anh):
so khớp theo biên từ, cụm dài ưu tiên ("work life balance" trước "balance"), có **đảo dấu khi phủ định**
("không tốt" → tiêu cực, cửa sổ 3 từ). Chưa đo trên tập nhãn (chưa có nhãn).

Hai điểm yếu đã thấy của baseline, giữ lại cho phần phân tích lỗi:
- "Lương và thưởng **nên được điều chỉnh** để theo kịp thị trường" → *trung tính* (đúng là tiêu cực).
  Từ điển mù với cách nói vòng.
- "Công ty không có **văn hóa** OT thường xuyên" → nhận thêm `culture_fun` sai, vì "văn hóa" nằm trong
  từ điển khía cạnh.

### Nhãn yếu từ điểm sao (2026-11-15)

`uv run python -m absa.weak_labels` – `absa/weak_labels.py`, phiên bản `aspect-dict+stars`.

Quy tắc: khía cạnh lấy từ từ điển; **cực tính lấy từ điểm sao theo khía cạnh của review** (≥4 → tích cực,
≤2 → tiêu cực), sao = 3 hoặc khía cạnh không có sao thì theo phần review (`liked` → tích cực,
`improvement` → tiêu cực). Cực tính **không** lấy từ từ điển cảm xúc, để nhãn yếu độc lập với baseline –
dùng chung từ điển thì mô hình học từ nhãn yếu chỉ học lại baseline và so sánh mất ý nghĩa.

| Số liệu | Giá trị |
|---|---|
| Câu có ít nhất 1 khía cạnh | 644 / 942 (**68,4%**) |
| Nguồn cực tính | sao 621, phần review 311 |
| Theo cực tính | tích cực 835, tiêu cực 91, trung tính 6 |

Theo khía cạnh: `culture_fun` 265, `work_life_balance` 209, `salary_benefits` 176, `management_care` 103,
`training_learning` 101, `office_workspace` 78.

**Lệch lớp rất mạnh: 835 tích cực / 91 tiêu cực (9:1).** Hai nguyên nhân cộng dồn: ITviec chỉ cho khách
xem một review đã được chọn mỗi công ty và review đó thiên về tích cực (đo 2026-11-13: +0,27 sao so với
review bị mờ, 0/141 nói "Không khuyến khích"), cộng với phần `liked` dài hơn phần `improvement` (572 vs 245 câu).

Ba nguồn nhiễu đã biết của nhãn yếu:
1. Sao theo khía cạnh là của **cả review**, câu nói một ý trái chiều sẽ bị gán sai.
2. Phần `liked` vẫn có câu tiêu cực ("OT nhiều lúc gần deadline") và ngược lại.
3. `work_life_balance` **không có sao** trên ITviec → chỉ còn tín hiệu phần, yếu nhất trong 6 khía cạnh.

### Rút câu để gán nhãn (2026-11-15)

Rút ngẫu nhiên với lệch 9:1 thì tập nhãn gần như sạch câu tiêu cực và Macro-F1 mất ý nghĩa. Vì vậy
`annotation/sample_absa_batch.py` **chia hạn mức theo nhãn yếu**: 20% cho câu từ điển không nhận ra khía
cạnh nào (cần để đo phần bỏ sót), phần còn lại chia đều 6 khía cạnh × 2 cực, nhóm tiêu cực lấy trước.
Nhãn yếu chỉ dùng để *rút mẫu*, không ghi vào file gán nhãn và không hiện cho người gán.

Lô thử `absa_trial` (seed 20261115, 60 câu): tiếng Việt 47 / tiếng Anh 13; `improvement` 30, `liked` 26,
`title` 4; đúng 4 câu mỗi nhóm `pos_*`/`neg_*` cho cả 6 khía cạnh, cộng 12 câu `no_aspect`.

Chưa gán nhãn. Việc tiếp: nhập `data/annotation/absa_trial.labelstudio.json` vào Label Studio
(cấu hình `annotation/label_studio_absa.xml`), Hoang Le gán 60 câu thử để chốt guideline 0.2, rồi mới
rút lô đầy đủ. Giao diện **không hiện điểm sao** vì sao là nhãn yếu – nhìn vào sẽ gán theo sao chứ không theo câu.

### Lô thử 60 câu: kết quả gán và điểm baseline (2026-11-15)

Gán xong `absa_trial` trong Label Studio (project 6). Export bằng `annotation/export_absa.py`
(`data/annotation/absa_trial.export.2026-11-15.json`, không commit). 60/60 câu có nhãn, bỏ 3 câu người
gán tick "không gán được" → **57 câu tính điểm**.

Phân bố nhãn vàng: 61 cặp (khía cạnh, cực) trên 57 câu. 9 câu không thuộc khía cạnh nào, 38 câu một
khía cạnh, 7 câu hai, 3 câu ba. Theo khía cạnh: `work_life_balance` 14, `office_workspace` 13,
`salary_benefits` 11, `training_learning` 11, `management_care` 6, `culture_fun` 6. Theo cực:
positive 29, negative 26, neutral 6. Hạn mức lúc rút mẫu đã làm được việc của nó: nhãn yếu lệch 9:1
(835 pos / 91 neg) mà tập gán ra gần 1:1.

Điểm trên 57 câu (`absa/score.py`; khía cạnh P/R/F1 vi mô, cực macro-F1 3 lớp theo ô câu × 6 khía cạnh):

| Hệ | Khía cạnh P | R | F1 | Cực macro-F1 (trên khía cạnh trùng) | Tổng hợp macro-F1 3 lớp |
|---|---|---|---|---|---|
| Baseline từ điển | 0,750 | 0,738 | **0,744** | 0,380 | **0,280** |
| Nhãn yếu `aspect-dict+stars` | 0,750 | 0,738 | 0,744 | 0,527 | **0,393** |

Khía cạnh giống nhau vì nhãn yếu dùng lại `match_aspects` của từ điển; chỉ phần cực là khác. F1 theo
lớp của baseline: positive 0,526 – negative **0,194** – neutral 0,121. Nhãn yếu: positive 0,603 –
negative **0,577** – neutral 0,000.

Ba điều rút ra:

1. **Từ điển cảm xúc gần như mù với câu tiêu cực** (recall negative 0,115). Nguyên nhân đọc được ngay
   trong lỗi: người Việt chê bằng cách đề nghị – "Cần chú ý thêm chế độ thưởng OT", "Công ty nên mua
   thêm máy", "Cải thiện cơ sở vật chất" – những câu này không chứa một từ cảm xúc xấu nào. 12/25 lỗi
   cực là đúng kiểu này.
2. **Nhãn yếu theo sao tốt hơn từ điển ở phần cực** (0,393 so với 0,280), nên dùng nhãn yếu làm thầy
   cho PhoBERT là có cơ sở, không phải chỉ vì tiện.
3. **Phủ định cần ngữ nghĩa, không chỉ cửa sổ từ.** "Không có kế hoạch training rõ ràng" bị từ điển
   chấm `positive` (bắt được "rõ ràng", `NEG_WINDOW` 3 từ không với tới "không"); nhưng nới cửa sổ thì
   "Gần như không có OT" – vốn là `positive` – lại thành `negative`. "Không có X" tốt hay xấu phụ thuộc
   X là thứ đáng có hay đáng tránh. Đây là lý do cần mô hình học, ghi vào phần phân tích lỗi của báo cáo.

**Tin cậy của nhãn vàng:** 11/57 câu (19%) bị tick "khó / cần bàn", nên con số trên là *baseline trên
tập dev*, chưa phải kết quả cuối. Soi lại 11 câu đó cho ra guideline 0.2 (mục 2c bảng tra thuật ngữ,
luật 8–9 siết `neutral`). Dò tự động theo bảng 2c thấy **10 câu cần gán lại** (thiếu khía cạnh) và
**5/6 nhãn `neutral` dùng sai** – phần lớn là chê nhẹ hoặc lời đề nghị, đáng ra `negative`. Tổng cộng
16 câu phải sửa, danh sách ở `data/annotation/absa_trial.relabel.md` (không commit).

Tranh luận đáng ghi lại: người gán đề nghị để `neutral` cho "OT được tính theo quy định" với lý do luật
đã bắt trả tiền OT nên không tính là khen. Bác bằng ba điểm: (a) WM3 đo quan điểm người viết về công ty
họ, không so với thị trường; (b) nhãn dựa vào kiến thức ngoài câu thì mô hình không học được và hai
người gán khó khớp; (c) **chính dữ liệu phủ định tiền đề** – 12/942 câu chê "OT không lương", "không
được tính lương OT đầy đủ", nên trả tiền OT không phải mức sàn của ngành. Thêm nữa người gán đã chấm
`positive` cho "trả lương đúng hạn" và "Lương về ting ting đúng giờ" – cùng loại việc, nên để `neutral`
ở câu OT là hai tiêu chuẩn. Chốt: **làm đúng nghĩa vụ mà người viết nhắc ra = `positive`** (guideline
0.2.1 luật 10). Phép thử đổi chiều ở mục 2d là công cụ để quyết `neutral` từ nay.

Đo thêm để kiểm tra lo ngại "gán thiên về positive": không có thiên lệch. Theo ô review, `liked` cho
22 pos / 2 neg / 4 neu, `improvement` cho 2 pos / 23 neg / 2 neu – người gán không gán máy móc theo ô.
Nhưng 4/6 nhãn `neutral` nằm ở ô `liked`, tức `neutral` đang bị dùng như ô "chưa chắc"; mục 2d nói rõ
chỗ đó phải tick "khó / cần bàn".

**Lỗi parser ITviec (nhỏ, cần sửa trước lô đầy đủ):** 3/144 review có `liked_text` dính cả phần
improvement, trong khi `improvement_text` chỉ lấy được phần đầu – hai selector bắt vào node lồng nhau.
Ví dụ: `improvement_text` là tiền tố đúng của `liked_text`. Ảnh hưởng 2% review nhưng làm sai `section`,
mà `section` là một nguồn nhãn yếu.

**`neutral` rất hiếm ở mức câu.** Sau khi sửa theo luật 8–9 chỉ còn khoảng 1–2 câu `neutral` trong 57
(~3%). Contract `silver.review_aspects` quy định ba giá trị `positive | negative | neutral` nên vẫn giữ
nhãn, nhưng macro-F1 3 lớp sẽ bị một lớp 1–2 mẫu kéo lệch. Báo cáo sẽ ghi cả macro-F1 3 lớp và
macro-F1 chỉ trên positive/negative, kèm support từng lớp, để số có thể đọc được.

Việc tiếp: gán lại 10 câu + 5 nhãn `neutral` theo guideline 0.2 → chạy lại `export_absa` để có nhãn
vàng dev chốt → bổ sung từ điển các thuật ngữ ở bảng 2c (career path, performance review, pantry, nhà
xe, thang máy, hybrid…) và luật "đề nghị = tiêu cực" cho `absa/lexicon.py` bản mở rộng, báo cáo cả bản cơ bản và bản mở rộng →
rút lô đầy đủ 942 câu. Bốp gán ~80 câu để đo κ.

### Nhãn vàng dev sau khi gán lại theo 0.2.1 (2026-11-15)

Gán lại 16 câu theo guideline 0.2.1 rồi export lại. Nhãn vàng dev chốt: **69 cặp (khía cạnh, cực) trên
57 câu** (trước khi sửa là 61 cặp). Câu không thuộc khía cạnh nào giảm 9 → 3. Theo cực: **35 positive,
33 negative, 1 neutral**. Theo khía cạnh: `work_life_balance` 14, `salary_benefits` 14,
`office_workspace` 13, `training_learning` 13, `management_care` 8, `culture_fun` 7.

| Hệ | Khía cạnh P | R | F1 | Cực macro-F1 | Theo ô, 3 lớp | Theo ô, chỉ pos/neg |
|---|---|---|---|---|---|---|
| Baseline từ điển | 0,867 | 0,754 | **0,806** | 0,325 | 0,250 | **0,375** |
| Nhãn yếu `aspect-dict+stars` | 0,867 | 0,754 | 0,806 | 0,517 | 0,416 | **0,624** |

So với nhãn vàng đợt đầu: F1 khía cạnh **0,744 → 0,806**, chủ yếu do precision lên 0,750 → 0,867. Nghĩa
là phần lớn khía cạnh trước bị tính là "từ điển bắt sai" thật ra **từ điển đúng, nhãn vàng thiếu** –
đúng những thuật ngữ sau đó vào bảng 2c (career path, performance review, company trip, pantry). Đây là
lý do phải gán thử một lô nhỏ rồi chốt guideline trước khi gán lô lớn; nếu gán thẳng 942 câu thì baseline
bị chấm oan và không ai biết.

Phần cực không khá lên: recall `negative` của từ điển vẫn 0,121 (trước 0,115). Gán lại không cứu được
chỗ này vì nguyên nhân nằm ở từ điển, không ở nhãn – người Việt chê bằng cách đề nghị. Nhãn yếu vẫn hơn
rõ: 0,624 so với 0,375 (macro 2 lớp).

`neutral` còn **1/69** sau khi áp ba cổng ở mục 2d. Macro-F1 3 lớp vì thế bị lớp một mẫu kéo xuống; từ
đây báo cáo cả hai số, 3 lớp để đối chiếu với contract và 2 lớp để đọc.

Việc tiếp: sửa lỗi parser ITviec (3/144 review lẫn `liked`/`improvement`) → nâng từ điển lên bản mở rộng (thuật
ngữ bảng 2c + luật "đề nghị = tiêu cực"), báo cáo cả bản cơ bản và bản mở rộng trên đúng 57 câu này → rút lô đầy đủ 942
câu theo hạn mức, Bốp gán ~80 câu đo κ. Cờ "khó / cần bàn" của lô thử chưa bỏ tick (11 câu) nhưng các
câu đó đã xử lý xong; lô sau đọc cờ thì nhớ mốc này.

### Sửa ranh giới câu `<br>` và parse lại (2026-11-15)

Khi truy nguồn mấy câu lẫn khen với chê, phát hiện **`<br>` bị biến thành dấu cách**: `_text` dùng
`itertext()` nên hai ý người viết gõ trên hai dòng bị dán thành một câu. Đo trên HTML đã lưu:
**166/288 khối liked/improvement (57,6%) có `<br>`**, 52 khối có nhiều hơn một. Hậu quả là những "câu"
như *"Cơ sở vật chất tốt, có bàn nâng hạ đỡ mỏi lưng, có chỗ ngủ trưa Bản thân tôi chưa bao giờ phải
OT"* – hai nhận xét về hai khía cạnh khác nhau, không thể gán một cực.

Lưu ý một giả thuyết đã bị loại: ban đầu tưởng hai selector `liked`/`improvement` bắt vào node lồng
nhau, vì có 3/144 review mà `improvement_text` là tiền tố đúng của `liked_text`. Đọc HTML thật thì hai
khối tách biệt đúng; phần trùng là **nội dung người viết gõ trùng ở cả hai ô**. Parser không sai chỗ đó.

Sửa: `crawler/itviec/parser.py` thêm `_node_text` giữ `<br>` thành `
` và gộp khoảng trắng theo từng
dòng; `absa/split.py` coi `
` là ranh giới ý cứng, cắt trước khi gộp khoảng trắng.

Thêm `crawler/itviec/reparse.py`: parse lại HTML đã lưu ở `data/raw-html/itviec/`, **không gửi request
nào**. 317 file → 144 review, khớp đúng số review đã có. Dùng lại được mỗi lần sửa parser.

Kết quả tách câu: **942 → 1065 câu** (+123, +13%). Tiếng Việt 808 / tiếng Anh 257; `liked` 679,
`improvement` 261, `title` 125.

`sentence_id` đổi cách băm: bỏ chỉ số câu, băm theo `(source_review_id, section, text, lần lặp)`. Lý do:
`source_review_id` là `content_hash(payload)` nên sửa parser làm id review đổi, mà id câu cũ lại phụ
thuộc thứ tự nên một câu bị tách ở đầu đoạn làm đổi id mọi câu sau. Băm theo nội dung thì câu nào không
đổi vẫn giữ id. `annotation/export_absa.py` khớp nhãn **theo văn bản** trước, theo id sau.

Nhãn lô thử sau khi parse lại: **53/57 câu còn dùng được**. 4 câu mất đúng là 4 câu dính nhau, giờ đã
tách đôi – nghĩa là bản sửa này trực tiếp xử lý 4 trong số các ca gán nhãn khó nhất:

| Câu cũ (bị dán) | Tách thành |
|---|---|
| "Cơ sở vật chất tốt… có chỗ ngủ trưa Bản thân tôi chưa bao giờ phải OT…" | văn phòng + OT |
| "Có Team building quý để gắn kết member, quà sinh nhật Gần như không có OT." | văn hóa + OT |
| "Được cung cấp đầy đủ trang thiết bị, có hợp đồng giống freelancer Không có OT vào các ngày…" | lương + OT |
| "5h30 là tan làm mà toàn thấy OT đến 7h mới về CSVC thấy hơi …" | OT + văn phòng |

### Từ điển mở rộng (2026-11-15)

Hai thay đổi, cả hai rút từ phân tích lỗi trên tập dev 53 câu:

1. **Luật đề nghị** (`absa/lexicon.py: is_advice`): câu có dấu hiệu đề nghị chưa bị phủ định
   ("nên", "cần", "mong", "cải thiện", "nâng cấp", "xem lại", "should", "improve"…) thì cực tính là
   `negative`, kể cả khi trong câu có từ khen. Phủ định dùng cửa sổ 5 từ thay vì 3, vì "không có gì
   **cần cải thiện** cả" có phủ định cách 4 từ. `predict(text, advice=False)` tái lập được bản cũ.
2. **Thuật ngữ bảng 2c** vào `aspect_lexicon.csv`: +50 dòng (career development, performance review
   criteria, company trip, nhà xe, thang máy, máy pha cafe, bàn nâng hạ, csvc, hỗ trợ gym, hybrid,
   flexiable, giờ giấc, cày cuốc, talkshow…), và **bỏ** `môi trường` / `môi trường làm việc` /
   `environment` khỏi `culture_fun` vì theo guideline mục 2c chúng là khen chung chung, không gán.
   153 → 200 dòng.

Chấm trên tập dev 53 câu, 59 cặp (`absa/eval_dev.py`):

| Hệ | Khía cạnh F1 | Theo ô, 3 lớp | Theo ô, chỉ pos/neg | Recall `negative` |
|---|---|---|---|---|
| từ điển cơ bản (số cũ, trên 57 câu) | 0,806 | 0,250 | 0,375 | 0,121 |
| từ điển mở rộng, tắt luật đề nghị | 0,933 | 0,263 | 0,395 | 0,161 |
| **từ điển mở rộng + luật đề nghị** | **0,933** | 0,404 | **0,607** | **0,645** |
| Nhãn yếu `aspect-dict+stars` | 0,933 | 0,437 | 0,655 | 0,581 |

Luật đề nghị là thay đổi có giá trị nhất: recall `negative` **0,161 → 0,645** (gấp 4), macro 2 lớp
0,395 → 0,607. *(Sửa sau phản biện 2026-11-17: đây là số **dev 53 câu**, chính là các câu đã dùng
để viết luật, nên lạc quan. Trên TEST đóng băng: 0,141 → 0,315 – vẫn gấp đôi, nhưng không phải gấp 4.)* Từ điển mở rộng giờ bắt câu tiêu cực **tốt hơn** nhãn yếu (0,645 so với 0,581), còn nhãn yếu
vẫn hơn ở tổng thể vì đọc được điểm sao.

**Phải ghi rõ trong báo cáo:** từ điển mở rộng được chỉnh *trên tập dev này*, nên 0,933 và 0,607 là số dev,
không phải số test. Số test chỉ được chấm một lần trên `absa_test1`, sau khi gán xong.

Lỗi đã biết của bản mở rộng: "nên" trong tiếng Việt vừa là "should" vừa là "vì thế" ("việc nhiều **nên** phải
OT"), nên luật đề nghị sẽ bắt sai một số câu mô tả. Giữ vì trên dev đúng nhiều hơn sai; ghi vào phần
phân tích lỗi.

### Chia dev/test theo review và rút `absa_test1` (2026-11-15)

Chia **theo review, không theo câu**. Hai câu cùng một review dùng chung điểm sao và cùng văn phong;
để một câu ở dev, câu kia ở test là rò rỉ, vì PhoBERT train trên nhãn yếu của review đó rồi lại bị chấm
trên chính review đó.

| Phần | Review | Câu | Dùng làm gì |
|---|---|---|---|
| dev | 45 (lô thử đã chạm) | 455 | chỉnh guideline, chỉnh từ điển; 53 câu đã có nhãn vàng |
| test | 99 | 610 | chấm một lần, không được chỉnh gì trên đó |

`annotation/sample_absa_batch.py` thêm `--exclude-reviews-of` để loại mọi câu thuộc review đã dùng.

`absa_test1` (seed 20261116, 300 câu từ pool 610): tiếng Việt 228 / tiếng Anh 72; `liked` 169,
`improvement` 91, `title` 40. Theo nhóm nhãn yếu: **toàn bộ 45 câu nhóm `neg_*` có trong pool đều được
lấy**, cộng 185 → 70 câu `no_aspect` và 31 câu mỗi nhóm `pos_*`.

Hạn chế đã biết: nhãn yếu chỉ cho 45 câu tiêu cực trong 610 câu, và `neg_office_workspace` = 0 (ITviec
chấm sao văn phòng cao, câu chê văn phòng nằm ở ô `improvement` mà không có cột sao). Lô thử cho thấy
nhãn vàng sẽ nhiều tiêu cực hơn nhãn yếu (nhãn yếu 24 câu neg → nhãn vàng 33 cặp neg), nên 300 câu này
dự kiến có khoảng 90–110 cặp tiêu cực. Nếu gán xong thấy quá ít thì bổ sung từ 310 câu còn lại của pool
test, **trước khi** chấm mô hình lần nào.

Lệch so với kế hoạch trong HUONG-DAN (~1.000 câu cho WM3): cả corpus chỉ có 1065 câu, chia theo review
thì pool test tối đa 610 câu. Lấy 300 câu cho vừa sức gán và vẫn đủ cho Macro-F1; 310 câu còn lại để
dành.

### Gán xong 300 câu TEST (2026-11-17) – số sơ bộ, chưa chốt

Project Label Studio 7 "WM3 ABSA - TEST (300 câu)", gán 300/300. Bỏ 7 câu tick "không gán được",
còn **293 câu / 331 cặp (khía cạnh, cực)**.

| | |
|---|---|
| Số khía cạnh mỗi câu | 0: 29 câu, 1: 212, 2: 38, 3: 13, 4: 1 |
| Theo khía cạnh | `culture_fun` 69, `work_life_balance` 68, `training_learning` 66, `management_care` 53, `salary_benefits` 44, `office_workspace` 31 |
| Theo cực | positive 251, negative 68, neutral 12 |
| Theo phần review | liked 166 câu, improvement 88, title 39 |
| Theo ngôn ngữ | vi 222, en 71 |

29/293 câu (9,9%) không nói về khía cạnh nào – đúng mục đích của hạn mức `no_aspect` khi rút mẫu:
không có nhóm này thì không đo được từ điển gán thừa bao nhiêu.

#### Baseline trên TEST (từ điển bản 2026-11-15, guideline 0.2.1)

| Hệ | Khía cạnh F1 | Theo ô, 3 lớp | Theo ô, chỉ pos/neg | Recall negative |
|---|---|---|---|---|
| từ điển, không luật đề nghị | 0.731 | 0.338 | 0.444 | 0.191 |
| từ điển + luật đề nghị | 0.731 | 0.374 | 0.505 | 0.412 |
| nhãn yếu `aspect-dict+stars` | 0.731 | 0.357 | 0.536 | 0.353 |

Luật đề nghị vẫn đáng giữ: recall `negative` 0.191 → 0.412 (gấp hơn hai lần), macro pos/neg 0.444 → 0.505.
Nhưng mức tăng nhỏ hơn trên dev nhiều (dev: 0.161 → 0.645).

#### Dev cao hơn test 0.20 F1 – vì dev đã bị dùng để sửa từ điển

Khía cạnh F1: **dev 0.933, test 0.731**. Chênh lệch này không phải nhiễu. Từ điển mở rộng (2026-11-15)
thêm 50 cụm lấy từ chính 11 câu bị tick "khó" của lô thử 60 câu, nên dev đo lại từ điển trên đúng dữ
liệu đã dùng để viết nó. 0.731 là con số trên test **lúc đó**, 0.933 chỉ dùng để so trước/sau khi sửa từ điển. *(Sửa sau phản
biện 2026-11-17: cùng đại lượng sau đó còn đổi 0,764 → 0,770 → 0,743 → 0,753 vì sửa từ điển, sửa
guideline và mở rộng TEST. **Số báo cáo là 0,753**: từ điển `absa-dict` trên TEST đóng băng 348 câu.)*
Ghi vào phần hạn chế của báo cáo: dev 53 câu quá nhỏ để vừa chỉnh vừa đo.

#### Lỗi guideline phát hiện khi gán TEST: chữ "môi trường"

Guideline 0.2 mục 2c ghi *"môi trường chuyên nghiệp → vẫn không gán (quá chung)"*, nhưng ví dụ ở mục 5
của **chính bản đó** lại gán `culture_fun` cho câu *"phúc lợi ổn, môi trường làm việc chuyên nghiệp,
văn phòng ở trung tâm"*. Hai chỗ nói ngược nhau.

Đo trên TEST: 35 câu có chữ "môi trường" hoặc "environment", **29 câu được gán `culture_fun`**, 6 câu
còn lại đều là "môi trường + bổ ngữ về học hỏi" nên vào `training_learning`. Tức là cách gán đã nhất
quán, chỉ câu luật kia sai. Thêm nữa khía cạnh này tên là "Văn hóa & **môi trường**", nên nói môi
trường thế nào thì đúng là nói về nó.

→ Guideline **0.2.2**: bỏ câu luật sai, chốt "môi trường + từ đánh giá chung" → `culture_fun`; từ đi
liền nói về chuyện học ("learning environment") → chỉ `training_learning`; có cả hai → gán cả hai.
Từ điển thêm lại `môi trường`, `environment` (và các cụm dài `môi trường học hỏi`, `learning
environment` để cụm dài khớp trước).

Khía cạnh F1 trên TEST: **0.731 → 0.764** (chỉ do từ điển), rồi **0.770** sau khi sửa 7 câu nhãn
lệch luật mới. Đây là lần chấm thứ hai trên TEST, ghi ra để minh bạch: lý do sửa là guideline tự mâu
thuẫn (một quyết định định nghĩa), không phải chọn theo điểm.

7 câu đã sửa (4 ở dev project 6, 3 ở test project 7) bằng `annotation/relabel_absa.py` với đặc tả
`data/annotation/relabel_0.2.2.json`; bản gốc của từng annotation lưu ở file `.backup.2026-11-17.json`
cùng thư mục. Giải thích từng câu: `data/annotation/absa_relabel_0.2.2.md`.

Sau khi sửa – TEST 292 câu / 333 cặp, DEV 57 câu / 73 cặp:

| Hệ | TEST khía cạnh F1 | TEST pos/neg | TEST recall neg | DEV khía cạnh F1 | DEV pos/neg |
|---|---|---|---|---|---|
| từ điển, không luật đề nghị | 0.770 | 0.470 | 0.191 | 0.945 | 0.421 |
| từ điển + luật đề nghị | 0.770 | 0.532 | 0.412 | 0.945 | 0.616 |
| nhãn yếu `aspect-dict+stars` | 0.770 | 0.557 | 0.353 | 0.945 | 0.649 |

#### Từ điển bỏ sót ở đâu (phân tích lỗi, không dùng để sửa từ điển)

331 cặp vàng, đoán đúng 230, **bỏ sót 101**, **gán thừa 68**.

| Khía cạnh | P | R | F1 | vàng | đoán |
|---|---|---|---|---|---|
| `work_life_balance` | 0.939 | 0.912 | 0.925 | 68 | 66 |
| `salary_benefits` | 0.724 | 0.955 | 0.824 | 44 | 58 |
| `office_workspace` | 0.750 | 0.871 | 0.806 | 31 | 36 |
| `training_learning` | 0.854 | 0.621 | 0.719 | 66 | 48 |
| `management_care` | 0.614 | 0.509 | 0.557 | 53 | 44 |
| `culture_fun` | 0.674 | 0.449 | 0.539 | 69 | 46 |

(bảng đo trước khi thêm "môi trường"; sau khi thêm thì `culture_fun` recall tăng)

Hai khía cạnh kém nhất là hai khía cạnh **không có từ khóa riêng**: `work_life_balance` chỉ cần bắt
"OT", "hybrid", "deadline" là xong, còn `management_care` và `culture_fun` thì người viết diễn đạt
bằng câu kể – "sếp nice", "thứ 6 hàng tuần còn có tiệc nhẹ", "Cần có sự gắn kết giữa các team member".
Từ điển không có cách nào bắt hết, đây là lý do cần mô hình học.

Lỗi cực tính: 31/68 câu có cặp `negative` mà từ điển không gọi là `negative`. Phần lớn là chê nhẹ
bằng cách nói giảm, không có từ xấu nào: "lương mặt bằng chung không cao", "Chưa quá rõ ràng về lộ
trình phát triển nghề nghiệp", "Một số quy trình còn mất thời gian và có thể tối ưu hơn", "nhiều khi
phải OT nhưng ko được tính lương OT đầy đủ". Luật đề nghị bắt được loại dùng "nên/cần/mong", không bắt
được loại dùng "chưa/không + từ tốt" và "có thể ... hơn".

#### 68 cặp negative là ít – rút thêm 56 câu phần "Đề nghị cải thiện"

Mục tiêu đặt trước là 90–110 cặp `negative`. Thực tế được 68, và phân bố rất lệch:

| | `management_care` | `work_life_balance` | `salary_benefits` | `training_learning` | `office_workspace` | `culture_fun` |
|---|---|---|---|---|---|---|
| cặp negative | 28 | 19 | 9 | 6 | 5 | 1 |

Bốn khía cạnh có dưới 10 cặp `negative` → **không báo cáo macro-F1 theo từng khía cạnh**, chỉ báo
macro chung kèm số mẫu từng lớp.

Hết cách rút thêm theo nhãn yếu: 310 câu còn lại trong pool test có **0 câu nhãn yếu negative** (toàn
bộ 45 câu đó đã nằm trong lô 300). Nhưng chia theo phần review thì năng suất rất khác nhau:

| Phần | Số câu TEST | Cặp negative | Trên mỗi câu |
|---|---|---|---|
| improvement | 88 | 59 | 0,67 |
| liked | 166 | 7 | 0,04 |
| title | 39 | 2 | 0,05 |

Pool còn 56 câu phần "Đề nghị cải thiện" chưa gán. Gán hết 56 câu đó thì được thêm khoảng 37 cặp
`negative`, tổng lên khoảng 105 – đúng khoảng mục tiêu. Đây là **lấy hết cả tầng**, không phải chọn
câu nào, nên không làm lệch tập test. Lô `absa_test2` (56 câu) nhập vào chính project 7 để TEST vẫn
là một khối, một lần export.

Lô `absa_test2` đã gán xong cùng ngày; kết quả ở mục "TEST WM3 đóng băng: 356 câu" bên dưới.

#### Mở rộng dev lên 207 câu (`absa_dev2`, 150 câu)

Dev hiện có 57 câu và đã bị dùng để viết từ điển mở rộng, nên vừa nhỏ vừa không còn trung lập. Phân tích
lỗi ở trên chỉ ra mấy hướng sửa cụ thể (chê bằng "chưa/không + từ tốt", "có thể … hơn", câu kể về sếp
và đồng nghiệp), nhưng 57 câu thì sửa gì cũng không biết là thật hay trùng hợp, mà TEST thì không được
chạm. Nên rút thêm 150 câu **từ đúng 45 review đã ở dev** (`--only-reviews-of`), để không review nào
vừa có câu ở dev vừa có câu ở test.

| | `absa_dev2` |
|---|---|
| Số câu | 150 (vi 105, en 45) |
| Theo phần | liked 98, improvement 37, title 15 |
| Nhãn yếu negative | 21 câu |
| Review | 40 (đều thuộc 45 review dev, 0 review trùng với test) |

Dev thành 207 câu. Kiểm tra chồng lấn giữa ba lô: 0 câu trùng nhau; `absa_dev2` không chung review nào
với `absa_test1` hay `absa_test2`.

### TEST WM3 đóng băng: 356 câu (2026-11-17)

Gán nốt 56 câu `absa_test2` vào project 7. TEST chốt ở **356 câu, 348 câu tính điểm (8 câu "không gán
được"), 378 cặp (khía cạnh, cực)**. Bản ghi đóng băng kèm sha256 của file nhãn:
`data/annotation/absa_test1.frozen.json`. Từ đây không sửa nhãn TEST nữa.

| Khía cạnh | positive | negative | neutral | tổng |
|---|---|---|---|---|
| `culture_fun` | 76 | 2 | 1 | 79 |
| `training_learning` | 61 | 8 | 3 | 72 |
| `management_care` | 26 | 43 | 2 | 71 |
| `work_life_balance` | 44 | 21 | 5 | 70 |
| `salary_benefits` | 38 | 12 | 2 | 52 |
| `office_workspace` | 27 | 6 | 1 | 34 |
| **tổng** | **272** | **92** | **14** | **378** |

92 cặp `negative` – đúng khoảng mục tiêu 90–110, lên từ 68 nhờ 56 câu phần "Đề nghị cải thiện".
Phần này chiếm 143/348 câu nhưng cho 83/92 cặp `negative`.

**Việc rút thêm 56 câu ăn thua ở chỗ nào:** `management_care` từ 28 lên **43** cặp negative và thành
khía cạnh duy nhất có negative nhiều hơn positive (43 so với 26); `work_life_balance` 19 → 21;
`salary_benefits` 9 → 12. **Không ăn thua với `culture_fun`:** dự đoán lên 6–9 cặp, thực tế chỉ 1 → 2.
Lý do: người viết hầu như không chê văn hóa công ty ở phần "Đề nghị cải thiện" – họ chê quản lý và OT.
Đây là tính chất của nguồn dữ liệu (ITviec chỉ cho khách xem 1 review tích cực mỗi công ty), không
phải lỗi cách rút mẫu, và không còn câu nào để rút thêm.

→ **Báo cáo macro-F1 theo từng khía cạnh chỉ cho `management_care`, `work_life_balance`,
`salary_benefits`** (12–43 cặp negative). Ba khía cạnh còn lại báo kèm số mẫu và nói rõ là không đủ
để kết luận. `neutral` 14 cặp trên 6 khía cạnh – không báo riêng, chỉ báo macro 2 lớp pos/neg.

#### Baseline trên TEST đã đóng băng (chấm một lần)

| Hệ | Khía cạnh F1 | Theo ô, 3 lớp | Theo ô, chỉ pos/neg | Recall negative |
|---|---|---|---|---|
| từ điển, không luật đề nghị | 0.743 | 0.329 | 0.434 | 0.141 |
| **từ điển + luật đề nghị** | 0.743 | **0.366** | 0.496 | **0.315** |
| nhãn yếu `aspect-dict+stars` | 0.743 | 0.343 | **0.515** | 0.261 |

Đây là con số nền mà PhoBERT phải vượt.

So với lúc TEST còn 292 câu: khía cạnh F1 0.770 → 0.743, recall `negative` 0.412 → 0.315. Cách giải thích
hợp lý nhất là tập test khó lên – 56 câu thêm vào toàn là góp ý nói giảm ở phần "Đề nghị cải
thiện", đúng loại từ điển bắt kém nhất. *(Sửa sau phản biện 2026-11-17: đây là giải thích, chưa phải
phép đo tách hai nguyên nhân; và 56 câu đó được chọn **sau khi đã xem phân bố nhãn TEST**, nên prevalence
`negative` của TEST là do nhóm đặt. Mọi số WM3 là "trên tập đã cân bằng theo hạn mức", không phải trên
phân bố thật của corpus.)*

#### Từ điển yếu ở đâu (phân tích lỗi trên TEST đã đóng băng)

| Khía cạnh | P | R | F1 | vàng | đoán |
|---|---|---|---|---|---|
| `work_life_balance` | 0.954 | 0.886 | 0.919 | 70 | 65 |
| `office_workspace` | 0.769 | 0.882 | 0.822 | 34 | 39 |
| `salary_benefits` | 0.746 | 0.904 | 0.817 | 52 | 63 |
| `training_learning` | 0.865 | 0.625 | 0.726 | 72 | 52 |
| `culture_fun` | 0.718 | 0.709 | 0.713 | 79 | 78 |
| `management_care` | 0.609 | **0.394** | 0.479 | 71 | 46 |

Thứ tự này gần như không đổi so với lúc 292 câu, trừ `management_care` tụt thêm (recall 0.509 → 0.394)
vì 56 câu mới chủ yếu nói về quản lý. Ba khía cạnh đầu có từ khóa riêng ("OT", "hybrid", "laptop",
"lương") nên từ điển làm tốt. `management_care` thì người viết diễn đạt bằng câu kể, không có từ nào
cố định: "Cần có sự gắn kết giữa các team member", "Provide clearer requirements and priorities",
"Project planning could be more organized". Đây là lý do cần mô hình học, nói rõ trong báo cáo.

Cực tính: 42/348 câu có cặp `negative` mà từ điển không gọi là `negative`, hầu hết là chê bằng cách
nói giảm ("chưa quá rõ ràng", "có thể tối ưu hơn", "lương mặt bằng chung không cao"). Luật đề nghị bắt
được loại dùng "nên/cần/mong", không bắt được loại "chưa/không + từ tốt" và "có thể … hơn".
Thử sửa trên dev 207 câu, **không chạm TEST**.

### Dev 200 câu và từ điển đủ luật (2026-11-17)

Gán xong 150 câu `absa_dev2` (project 8). Dev giờ có **200 câu, 207 cặp (khía cạnh, cực)**, gộp từ hai
file nhãn `absa_trial.absa.jsonl` và `absa_dev2.absa.jsonl`.

Điều đáng chú ý nhất: riêng 150 câu mới, từ điển mở rộng được **0.738** F1 khía cạnh. TEST được 0.743. Hai
con số gần bằng nhau. Trong khi đó 57 câu dev cũ cho tới 0.945. Nghĩa là dev cũ không đo được gì nữa
vì từ điển mở rộng vốn viết ra từ chính nó, còn dev mới thì chưa bị dùng để chỉnh gì nên nó đo thật.

**Một nhãn sai đã sửa:** câu "Unfair performance review." gán `management_care`=`positive`. "Unfair"
là chê. Sửa thành `negative` bằng `annotation/relabel_absa.py`.

#### Từ điển thiếu gì

Xem các câu từ điển đoán sai trên dev thì thấy ba nhóm thiếu. Từ 211 lên **247 cụm khía cạnh**, 101
lên **124 cụm cảm xúc**.

| Thiếu | Thêm |
|---|---|
| `management_care` không có từ **"sếp"** – từ phổ biến nhất của khía cạnh này | sếp, sếp trực tiếp, tech lead, team lead, scrum master, project manager, ban giám đốc, đánh giá năng lực, KPI, code review, giao tiếp, phân công |
| `culture_fun` chỉ có "đồng nghiệp" | teamwork, đội ngũ, mọi người, tôn trọng, respect, bonding, đối xử, hỗ trợ nhau, team member, **văn hoá** (viết "hoá" thay vì "hóa", từ điển cũ không khớp) |
| Thiếu từ cảm xúc hay gặp | hấp dẫn, hiệu quả, công bằng, chu đáo, tận tình (khen); nặng, trễ, bất công, mất thời gian, weak point, brief (chê) |

Ba từ "hấp dẫn", "hiệu quả", "công bằng" còn giải quyết luôn kiểu chê nói giảm. Luật phủ định đã có
sẵn, nên khi "hấp dẫn" là từ khen thì "lương **chưa** hấp dẫn" tự động thành chê.

#### Hai luật mới cho cực tính

Trên dev có hai kiểu câu mà nhãn vàng là chê nhưng từ điển chấm `neutral`:

**Kiểu 1 – "không có / chưa có *cái gì đó*".** Ví dụ "Không có company trip", "Không có lương OT".
Cả câu không có một từ chê nào, nên từ điển cũ không thấy gì. Luật mới: câu có "không có / chưa có"
**và** nói tới ít nhất một khía cạnh thì là chê. Phải có điều kiện "nói tới khía cạnh" để câu
"Không có gì cần cải thiện cả" không bị hiểu nhầm; ngoài ra chặn riêng chữ "không có **gì**".

**Kiểu 2 – câu khen một ý chê một ý.** Ví dụ "Great environment, but unfair performance review".
Từ điển đếm được một từ khen và một từ chê, trừ nhau bằng 0, ra `neutral`. Luật mới: hòa nhau mà
trong câu *có* từ cảm xúc thì lấy chê. Lý do theo guideline mục 2d: `neutral` dành cho câu **không
đánh giá gì**, chứ không phải câu đánh giá cả hai chiều. Câu không có từ cảm xúc nào vẫn là `neutral`.

Đồng thời sửa luật đề nghị, vì nó đang bắt nhầm câu khen thành chê:

- "need to" đứng một mình khớp cả **"Rarely need to do OT"**, mà câu này là khen. Đổi thành
  "need to be" / "needs to be".
- "cải thiện" cũng có trong câu khen: "luôn **được** học hỏi và cải thiện kỹ năng", "công ty
  **cố gắng** cải thiện". Thêm danh sách từ đứng trước làm mất nghĩa đề nghị: được, giúp, đã, luôn,
  cố, đang, tự, muốn, để, và.
- Thêm vài cách đề nghị gián tiếp: "would help", "could be", "sẽ giúp", "tuyệt vời hơn".

#### Bật dần từng luật trên dev (200 câu, 207 cặp)

Hai cột cuối đọc như sau. **R** = trong các cặp nhãn vàng là chê, từ điển bắt được bao nhiêu phần.
**P** = trong các cặp từ điển gọi là chê, đúng được bao nhiêu phần.

| Luật bật | Khía cạnh F1 | Theo ô 3 lớp | Chỉ pos/neg | R chê | P chê |
|---|---|---|---|---|---|
| Cơ bản – chỉ đếm từ cảm xúc | 0.833 | 0.294 | 0.433 | 0.212 | 0.824 |
| + luật đề nghị | 0.833 | 0.400 | 0.588 | 0.621 | 0.695 |
| + luật "không có" | 0.833 | 0.408 | 0.600 | 0.682 | 0.672 |
| + luật hòa → chê | 0.833 | 0.404 | 0.594 | 0.652 | 0.683 |
| **Đủ luật – cả ba luật** | 0.833 | **0.411** | **0.605** | **0.712** | 0.662 |
| nhãn yếu `aspect-dict+stars` | 0.833 | 0.431 | 0.646 | 0.515 | 0.694 |

Cả ba luật đều đi theo một hướng: bắt được nhiều lời chê hơn, đổi lại báo nhầm nhiều hơn. R từ 0.212
lên 0.712, P từ 0.824 xuống 0.662. Vẫn nên đổi, vì chê là lớp hiếm, bỏ sót một lời chê tốn hơn báo
thừa một lời chê.

#### Chấm từ điển đủ luật trên TEST đã đóng băng (348 câu, 378 cặp)

Chọn cấu hình đủ luật **trên dev** trước, rồi mới đem sang TEST. Không chỉnh gì theo số TEST.

| Hệ | Khía cạnh F1 | Theo ô 3 lớp | Chỉ pos/neg | R chê | P chê |
|---|---|---|---|---|---|
| Cơ bản – chỉ đếm từ cảm xúc | 0.753 | 0.344 | 0.458 | 0.152 | 0.609 |
| + luật đề nghị | 0.753 | 0.380 | 0.518 | 0.337 | 0.413 |
| + luật "không có" | 0.753 | 0.381 | 0.510 | 0.391 | 0.350 |
| + luật hòa → chê | 0.753 | 0.383 | **0.527** | 0.370 | 0.415 |
| **Đủ luật – cả ba luật** | **0.753** | **0.383** | 0.518 | **0.424** | 0.355 |
| nhãn yếu `aspect-dict+stars` | 0.753 | 0.346 | 0.519 | 0.261 | 0.511 |

So với bản mở rộng trên đúng tập TEST này: khía cạnh F1 0.743 → 0.753, R chê 0.315 → 0.424, macro pos/neg
0.496 → 0.518. Từ điển giờ bằng nhãn yếu về macro (0.518 so với 0.519), nhưng bắt được nhiều lời chê
hơn hẳn (0.424 so với 0.261).

Hai điều phải ghi rõ:

- **Dev cao hơn TEST khá nhiều** (0.605 so với 0.518). Phần chênh là do bản đủ luật được chỉnh trên dev. Số
  đem đi báo cáo là số TEST.
- Trên TEST, cấu hình **chỉ bật luật hòa** được 0.527, cao hơn bản đủ luật (0.518). Nhưng chọn cấu hình theo
  điểm TEST là sai nguyên tắc, nên giữ bản đủ luật vì nó thắng trên dev. Chênh lệch này cũng cho thấy khoảng
  0.01 ở đây là nhiễu, không nên đọc thành hơn kém.

Từng khía cạnh trên TEST:

| Khía cạnh | P | R | F1 | vàng | đoán |
|---|---|---|---|---|---|
| `work_life_balance` | 0.954 | 0.886 | 0.919 | 70 | 65 |
| `office_workspace` | 0.769 | 0.882 | 0.822 | 34 | 39 |
| `salary_benefits` | 0.746 | 0.904 | 0.817 | 52 | 63 |
| `culture_fun` | 0.709 | 0.772 | 0.739 | 79 | 86 |
| `training_learning` | 0.868 | 0.639 | 0.736 | 72 | 53 |
| `management_care` | 0.579 | 0.465 | 0.516 | 71 | 57 |

`culture_fun` từ 0.713 lên 0.739 và `management_care` từ 0.479 lên 0.516 nhờ các cụm mới.
`management_care` vẫn kém nhất, mà lại là khía cạnh nhiều lời chê nhất (43 trong 92 cặp). Đây là chỗ
PhoBERT phải thắng từ điển thì mới có gì để nói trong báo cáo.

#### Một lỗi trong công cụ chấm đã sửa

`absa/eval_dev.py` khi gộp nhiều file nhãn lại (dev nằm ở hai project) đang gộp theo **văn bản câu**.
TEST vì thế tụt từ 348 xuống 344 câu: hai review khác nhau có thể viết câu giống hệt nhau ("Lương
thấp"), đó là hai mẫu thật chứ không phải một. Đổi sang gộp theo `sentence_id`.

### Đồng thuận hai người gán WM3: κ = 0,871 (2026-11-17)

Người thứ hai gán lại **35 câu rút từ TEST đã đóng băng** (10% của 348 câu tính điểm, seed 20261117,
rút ngẫu nhiên đều chứ không chia hạn mức theo nhãn). Gán trên project Label Studio **riêng**, không
thấy nhãn người thứ nhất; file task chỉ có `sentence_id, text, company_name, section, lang`.

Lệnh: `uv run python -m annotation.sample_absa_kappa --batch absa_kappa1` →
`uv run python -m annotation.make_ls_project --title "WM3 ABSA - κ (người 2, 35 câu)" --config annotation/label_studio_absa.xml --tasks data/annotation/absa_kappa1.labelstudio.json` →
`uv run python -m annotation.export_absa --project 9 --batch absa_kappa1_p2` →
`uv run python -m annotation.kappa_absa --a data/annotation/absa_test1.absa.jsonl --b data/annotation/absa_kappa1_p2.absa.jsonl`

Người thứ hai tick "không gán được" 1 câu nên đo trên **34 câu** (204 ô = 34 × 6 khía cạnh).
Người 1: 39 cặp (khía cạnh, cực). Người 2: 34 cặp.

| Cohen's κ trên | κ | Trên bao nhiêu |
|---|---|---|
| ô 4 lớp (`none` / `positive` / `neutral` / `negative`) | **0,871** | 204 ô |
| chỉ việc phát hiện khía cạnh (có nhắc / không nhắc) | 0,883 | 204 ô |
| chỉ cực cảm xúc, trên ô cả hai đều gán khía cạnh | 0,872 | 33 ô |

Đạt mục tiêu ≥ 0,7 ngay vòng đầu. *(Sửa sau phản biện 2026-11-17: bỏ nhãn "almost perfect" – mẫu chỉ
34 câu. Khoảng tin cậy 95% bootstrap theo câu: ô 4 lớp **[0,754; 0,964]**, phát hiện khía cạnh
[0,779; 0,966], cực cảm xúc [0,474; 1,000]. Và **κ riêng lớp `negative` chỉ 0,657, CI [0,187; 1,000]**:
người 1 có 7 cặp chê, người 2 có 5. Lớp quan trọng nhất của WM3 là lớp có đồng thuận bất định nhất;
con số 0,871 không nói được điều đó. Lệnh: `uv run python -m annotation.kappa_absa`.)* Khác hẳn WM2: ở đó κ vòng 1
chỉ 0,591 và phải sửa guideline rồi đo lại. Lý do khác nhau: WM2 phải khớp **ranh giới span** trong
câu, WM3 chỉ chọn nhãn cho cả câu nên ít chỗ lệch hơn.

Lấy người 1 làm mốc để đọc hướng lệch (không phải để nói ai đúng): khía cạnh P 0,971 R 0,846 F1 0,904.
Tức là người 2 gán **thiếu** chứ gần như không gán sai.

**6/34 câu lệch, 8 ô lệch.** Chia theo kiểu:

| Kiểu lệch | Số ô |
|---|---|
| người 2 bỏ sót một khía cạnh | 6 |
| người 2 gán thêm một khía cạnh | 1 |
| hai người gán khác cực (`negative` / `positive`) | 1 |

Xem từng câu thì ra ba nhóm nguyên nhân, và chỉ một nhóm là lỗi gán thật:

1. **Câu liệt kê nhiều thứ, người 2 dừng ở khía cạnh đầu (3 câu).** "Premium health insurance, free
   daily lunch and snacks, learning support (courses…)" – người 1 gán `salary_benefits` +
   `training_learning`, người 2 chỉ gán `salary_benefits`. Đã thêm luật vào guideline mục 2c (bản 0.2.3):
   gặp dấu phẩy hoặc chữ "và" nối các danh từ thì soát lại bảng khía cạnh một lượt nữa.
2. **Guideline chưa nói tới (3 câu).** "Anh T\*\* leader kiến thức giỏi" – người 1 gán `culture_fun`,
   người 2 để trống. "Uống bia ít lại vì em hông uống được bia" – người 1 `management_care`, người 2
   `culture_fun`. "Phát triển các clb trong công ty" – người 1 `management_care`, người 2 tick
   "không gán được". Cả ba đều là chỗ guideline không có dòng nào để tra, nên mỗi người tự quyết.
   Bản 0.2.3 chốt: năng lực của sếp/lead → `management_care`; CLB, uống bia, ăn uống cùng nhau →
   `culture_fun`. Theo bản mới thì **nhãn người 2 đúng hơn ở hai trong ba câu này.**
3. **Lỗi gán thật, một câu.** "Improve sprint planning and workload management to maintain a healthy
   work-life balance." – người 2 gán `work_life_balance` = `positive`. Chữ "healthy work-life balance"
   kéo người gán sang phía khen, nhưng cả câu là lời đề nghị sửa, nên là `negative` (luật 2 và luật 9).

**TEST không sửa theo bản 0.2.3.** TEST đã đóng băng và đã có mô hình chấm trên đó. Hệ quả phải ghi
trong phần hạn chế: trong 356 câu TEST còn khoảng 2–3 câu gán khác guideline hiện hành, đều ở nhóm
`management_care` ↔ `culture_fun`.

Điều này nối với một con số đã thấy trước đó: `management_care` là khía cạnh từ điển làm tệ nhất
(F1 0,516), và cũng là khía cạnh hai người gán lệch nhau nhiều nhất. Một phần của 0,516 là **nhiễu
nhãn**, không phải mô hình yếu. Khi chấm PhoBERT phải nhớ: F1 của `management_care` có một mức trần
thấp hơn các khía cạnh khác.

**Hạn chế của chính phép đo κ này:** mẫu 35 câu là nhỏ, khoảng tin cậy của κ rộng; và mẫu chỉ có
8 cặp `negative` của người 1 nên κ cảm xúc (0,872) chủ yếu nói về lớp `positive`.

### Mô hình học có giám sát cho WM3: macro pos/neg 0,518 → 0,590 trên TEST (2026-11-17)

> **Đọc kèm mục "Kiểm lại" ở cuối phần này.** Mức tăng 0,518 → 0,590 là thật so với baseline
> từ điển, nhưng một luật một dòng theo trường `section` cũng được 0,583, nên phần do *học* mà ra
> là không đáng kể. Tiêu đề này giữ nguyên để khớp nhật ký; kết luận thì xem mục kiểm lại.

#### Không train được trên nhãn yếu – phải nói rõ vì sao

Kế hoạch ban đầu giống WM2: train PhoBERT trên nhãn yếu, chấm trên tập gán tay. Đếm lại thì không
làm được. Nhãn yếu WM3 lấy cực tính từ **điểm sao của review**, mà review công khai ITviec toàn điểm
cao:

| Pool | Số câu | Cặp nhãn yếu | Trong đó `negative` |
|---|---|---|---|
| Ngoài review của TEST | 455 (45 review) | 418 | **50** |
| Ngoài review của TEST, bỏ câu đã là dev gold | 255 | 193 | **1** |

Bỏ câu dev gold là bắt buộc nếu muốn dev còn sạch để chọn mô hình. Còn 1 cặp chê trên 255 câu thì
không học được gì về lời chê. Tăng pool cũng không cứu được: 99/144 review đã đi vào TEST, phần còn
lại chỉ có 114 câu thuộc phần "Đề nghị cải thiện".

Nguồn duy nhất có lời chê là **tập gán tay**: dev 200 câu / 207 cặp, trong đó 66 cặp `negative`.
Nên đổi cách: học có giám sát trên dev, chọn mô hình bằng 5-fold CV **trong dev**, rồi chấm TEST một
lần. Dev và TEST không chung review nào (`absa/supervised.py` dừng chương trình nếu chung).

#### Ba mô hình học từ đầu đều thua từ điển

Mỗi khía cạnh là một bài 4 lớp `none/positive/neutral/negative`. Số dưới đây là **out-of-fold**: mỗi
câu được dự đoán bởi mô hình không thấy nó, nên đọc được như số trên tập giữ lại.

| Hệ (dev 200 câu) | Khía cạnh F1 | Chỉ pos/neg | R chê | P chê |
|---|---|---|---|---|
| từ điển `absa-dict` | **0,833** | 0,605 | 0,712 | 0,662 |
| nhãn yếu | 0,833 | 0,646 | 0,515 | 0,694 |
| TF-IDF + hồi quy logistic | 0,533 | 0,398 | 0,197 | 0,591 |
| PhoBERT đóng băng + hồi quy logistic | 0,617 | 0,432 | 0,273 | 0,419 |
| PhoBERT fine-tune (8 epoch) | 0,343 | 0,214 | 0,606 | 0,097 |

Kết luận rõ: **160 câu train không đủ để học nhận ra khía cạnh.** Từ điển có 247 cụm khía cạnh do
người soạn, tức là nhiều tri thức hơn hẳn những gì 160 câu chứa. PhoBERT fine-tune tệ nhất và tệ theo
kiểu dễ hiểu: cân lại lớp (`none` chiếm 81% ô) làm nó đoán 750 cặp khi nhãn vàng chỉ có 207.

#### Mô hình lai: khía cạnh của từ điển, cực tính thì học

Chỗ từ điển yếu không phải khía cạnh (0,833) mà là cực tính. Nên bỏ phần học khía cạnh, chỉ học cực:

- **Khía cạnh**: `match_aspects` của từ điển, không đổi gì.
- **Cực tính**: một bộ hồi quy logistic 3 lớp cho cả câu, đặc trưng gồm
  (a) 11 **tín hiệu của chính từ điển** – số từ khen, số từ chê, hiệu hai số, cờ "câu hai chiều",
  cờ "không có từ cảm xúc nào", cờ luật đề nghị, cờ luật "không có", phần của review, ngôn ngữ,
  độ dài; và (b) TF-IDF từ 1-2 gram.

Ý chính: đừng bắt mô hình học lại từ vựng cảm xúc từ 160 câu, mà **đưa các số của từ điển vào làm đặc
trưng** rồi để nó học cách kết hợp – đúng việc mà ba luật tay (`advice`, `missing`, `tie`) đang làm
bằng if/else. Mục tiêu học là cực của cả câu (cực hay gặp nhất trong nhãn vàng của câu), vì baseline
từ điển cũng chỉ cho một cực cho cả câu, có vậy mới so được.

Bật dần từng khối đặc trưng, out-of-fold trên dev:

| Đặc trưng | Khía cạnh F1 | Chỉ pos/neg | R chê | P chê |
|---|---|---|---|---|
| (từ điển `absa-dict`, luật tay) | 0,833 | 0,605 | 0,712 | 0,662 |
| 11 tín hiệu từ điển | 0,833 | 0,677 | 0,697 | 0,708 |
| + TF-IDF | 0,833 | **0,768** | 0,773 | 0,761 |
| + PhoBERT đóng băng (thay TF-IDF) | 0,833 | 0,762 | 0,773 | 0,739 |
| + cả TF-IDF và PhoBERT | 0,833 | 0,762 | 0,773 | 0,739 |

Hai điều đọc được: (1) chỉ thay if/else bằng hồi quy logistic trên đúng các tín hiệu đó đã được
+0,072; (2) TF-IDF thêm +0,091 nữa, còn **PhoBERT không thêm gì** so với TF-IDF. Với 160 câu train,
768 chiều ngữ nghĩa không giúp hơn đếm từ. Chốt cấu hình `hybrid` = tín hiệu từ điển + TF-IDF.

Đổi seed (đổi cách chia fold và seed của bộ giải): 0,768 / 0,774 / 0,768 / 0,768 / 0,779 trên 5 seed.
Ổn định, không phải trúng một lần.

#### Chấm trên TEST đã đóng băng, một lần

| Hệ (TEST 348 câu, 378 cặp) | Khía cạnh F1 | Theo ô 3 lớp | Chỉ pos/neg | R chê | P chê |
|---|---|---|---|---|---|
| từ điển `absa-dict` | 0,753 | 0,383 | 0,518 | 0,424 | 0,355 |
| nhãn yếu | 0,753 | 0,346 | 0,519 | 0,261 | 0,511 |
| **lai (từ điển + hồi quy logistic)** | 0,753 | **0,438** | **0,590** | **0,533** | 0,402 |

Khía cạnh F1 bằng nhau là **theo thiết kế**: mô hình lai dùng chính khía cạnh của từ điển.

Bootstrap ghép cặp theo câu, 1.000 lần (`experiments/paired_wm3.py`) – mỗi lần lấy lại 348 câu có hoàn
lại và tính cả hai hệ trên cùng các câu đó:

| Chỉ số | từ điển | lai | Δ | CI95 | p(Δ≤0) |
|---|---|---|---|---|---|
| macro pos/neg theo ô | 0,518 | 0,590 | **+0,072** | [+0,027; +0,120] | 0,000 |
| F1 `negative` theo ô | 0,386 | 0,458 | +0,072 | [+0,007; +0,142] | 0,011 |
| R `negative` theo ô | 0,424 | 0,533 | +0,109 | [+0,035; +0,186] | 0,002 |
| macro 3 lớp theo ô | 0,383 | 0,438 | +0,055 | [−0,025; +0,158] | 0,132 |

Ba chỉ số đầu: khoảng tin cậy không chứa 0. Chỉ số 3 lớp thì chứa 0, vì lớp `neutral` chỉ có 14 cặp
nên F1 của nó nhảy loạn giữa các lần lấy mẫu – một lý do nữa để báo cáo số 2 lớp là số chính.

Không có phương sai theo seed trên TEST: lần chấm cuối train trên cả 200 câu dev, bộ giải lbfgs
không ngẫu nhiên, nên ba seed cho đúng cùng một số.

**Độ đúng cực tính trên các ô cả hai bên đều nhận ra khía cạnh** (279 ô) – đây mới là chỗ mô hình lai
làm việc, nhìn số này thấy rõ hơn:

| Khía cạnh | cặp | từ điển đúng cực | lai đúng cực |
|---|---|---|---|
| `office_workspace` | 30 | 0,733 | **0,933** |
| `salary_benefits` | 47 | 0,681 | **0,915** |
| `management_care` | 33 | 0,818 | 0,909 |
| `culture_fun` | 61 | 0,852 | 0,885 |
| `training_learning` | 46 | 0,609 | **0,826** |
| `work_life_balance` | 62 | 0,468 | 0,677 |
| **tổng** | 279 | 0,681 | **0,842** |

Từ điển đoán đúng cực 68,1% số ô, mô hình lai 84,2%. `work_life_balance` vẫn kém nhất ở cả hai.

#### Phân tích lỗi trên TEST

**Bỏ sót lời chê: chỉ 5 ô** (vàng chê, mô hình gọi khen) – cả 5 đều nằm ở phần "Điều tôi thích", và
4/5 là về OT: "nhiều khi phải OT nhưng ko được tính lương OT đầy đủ", "Overtime is paid, but it
depends on the project and isn't quite commensurate with the effort put in". Người viết kẹp lời chê
vào giữa phần khen.

**Báo chê thừa: 27 ô** (vàng khen, mô hình gọi chê), 22/27 ở phần "Đề nghị cải thiện". Mô hình học
"phần improvement → chê" hơi mạnh tay, nên câu khen lọt vào phần đó bị gọi sai ("Đồng nghiệp thân
thiện" đặt ở phần đề nghị). Đây là nguồn lỗi chính và nó giải thích P chê thấp (0,402).

**Một chỗ sai có thể sửa được, nhưng chưa sửa:** luật "không có" cho ra `negative`, mà với
`work_life_balance` thì "không có OT" là **lời khen**: "Công ty không có OT đâu nhé", "Công ty nhìn
chung không có văn hóa OT thường xuyên" đều bị gọi là chê. Giải pháp là cho luật "không có" biết
khía cạnh. **Nhưng quan sát này đến từ việc xem lỗi trên TEST**, nên không được sửa rồi chấm lại TEST
và gọi đó là cải thiện – làm vậy là chọn mô hình theo tập test. Ghi vào việc còn lại, kiểm trên dev
trước, và chỉ chấm lại khi có tập test mới.

#### Kiểm lại: mức tăng chủ yếu đến từ trường `section`, không phải từ việc học

> **Đọc kèm mục "WM3 – đối chiếu với điểm sao ITviec" ở cuối file (2026-11-18).** Kết luận ở mục này
> chỉ đúng với phép đo mức câu trên nhãn người; dưới đích là điểm sao, mô hình lai hơn luật `section`
> có ý nghĩa ở mức review (Δρ = +0,090, p = 0,005).

Sau khi có số trên TEST, kiểm thêm một hệ tầm thường mà lẽ ra phải thử từ đầu: **khía cạnh lấy từ
từ điển, cực tính chỉ theo phần của review** – câu nằm trong "Đề nghị cải thiện" thì `negative`, nằm
trong "Điều tôi thích" thì `positive`. Một dòng lệnh, không train gì.

| Hệ | dev (out-of-fold) | TEST |
|---|---|---|
| từ điển `absa-dict` | 0,605 | 0,518 |
| **chỉ luật phần review** | **0,774** | **0,583** |
| mô hình lai (train 160 câu) | 0,768 | 0,590 |

Trên dev luật một dòng **ăn** mô hình lai; trên TEST hơn kém không đáng kể. Bootstrap ghép cặp 1.000
lần, lai so với luật phần review:

| Chỉ số | luật phần | lai | Δ | CI95 | p(Δ≤0) |
|---|---|---|---|---|---|
| macro pos/neg | 0,583 | 0,590 | +0,007 | [−0,013; +0,031] | 0,264 |
| F1 `negative` | 0,454 | 0,458 | +0,004 | [−0,024; +0,034] | 0,403 |
| macro 3 lớp | 0,389 | 0,438 | +0,049 | [−0,006; +0,133] | 0,105 |

Không chỉ số nào có ý nghĩa. Lý do dễ thấy: trên TEST, **83/127 ô ở phần "Đề nghị cải thiện" là chê
(65%), còn ở phần "Điều tôi thích" chỉ 7/201 (3,5%)**. Cấu trúc form của ITviec đã mang gần hết thông
tin cực tính; mô hình học lại đúng cái đó và không thêm được gì đo được.

Đường cong học trên dev (out-of-fold, cắt bớt tập train, trung bình 3 seed) xác nhận:

| câu train | macro pos/neg |
|---|---|
| 20 | 0,737 |
| 40 | 0,754 |
| 80 | 0,765 |
| 120 | 0,766 |
| 160 | 0,770 |
| *(luật một dòng, 0 câu train)* | *0,774* |

Phẳng từ 80 câu, và chưa bao giờ vượt mức 0 câu train. Nên **gán thêm vài trăm câu nữa sẽ không
nâng được số này**; phải đổi cách đặt bài thì mới có chỗ tăng (xem "Việc còn lại").

**Kết luận sửa lại.** Câu đúng là: *"so với baseline từ điển thì +0,072 có ý nghĩa, nhưng gần như
toàn bộ mức tăng đó đến từ việc dùng trường `section` của ITviec, chứ không phải từ bộ phân loại
học được."* Số báo cáo chính vẫn là 0,590, nhưng phải kèm cột "luật phần review" làm baseline, không
được chỉ so với từ điển. Việc còn lại đáng làm là tìm chỗ mà `section` **không** quyết định được:
lời chê nằm trong phần khen (5 ô trên TEST) và câu hai cực.

#### Hạn chế

- **Mô hình học gần như không đóng góp gì ngoài trường `section`** (mục ngay trên). Phần này là kết
  quả âm, phải viết đúng như vậy trong báo cáo.
- Train chỉ 200 câu. Số dev (0,768) cao hơn TEST (0,590) khá nhiều; phần chênh là do TEST khó hơn
  (từ điển cũng tụt 0,605 → 0,518 trên đúng hai tập này), không phải do chỉnh theo dev – số dev là
  out-of-fold.
- Mô hình lai chỉ cho **một cực cho cả câu**, giống baseline. Câu khen một khía cạnh chê khía cạnh
  khác ("Lương ổn nhưng OT nhiều") thì chắc chắn sai một nửa. May là rất hiếm: 5/200 câu dev và
  3/348 câu TEST. Đây là trần của cả hai hệ, không phải lỗi của mô hình.
- Lớp `neutral` (14/378 cặp TEST) thực tế không học được: mô hình đoán đúng 1 ô.
- Lần chấm này chạy khi repo chưa commit sạch (`absa/supervised.py` còn mới) → chạy lại sau khi commit
  để số gắn với một commit, như đã làm với WM2.

Lệnh: `uv run python -m absa.supervised cv --model all` → `uv run python -m absa.supervised test --model hybrid`
→ `uv run python -m experiments.paired_wm3`

## WM6 – đồ thị kỹ năng

### Dựng đồ thị và hai mốc bắt buộc (2026-11-17)

Đồ thị đồng xuất hiện kỹ năng trên **867 tin** (TopCV `topcv_20261115` 331 tin + ITviec `itviec_20261113` 536 tin).
Đỉnh là kỹ năng đã chuẩn hóa về `canonical` của `ie/resources/skill_alias.csv`, cạnh nối hai kỹ năng
cùng xuất hiện trong một tin. Đây là bài **tiêu thụ đầu ra của WM2**, nên dựng bằng cả hai bộ trích:

| Bộ trích | Tin có kỹ năng | Kỹ năng/tin | Đỉnh | Cạnh | Mật độ |
|---|---|---|---|---|---|
| từ điển alias | 828/867 | 8,8 | 163 | 3.607 | 0,27 |
| PhoBERT WM2 self-training, seed 1 | 799/867 | 7,2 | 151 | 2.649 | 0,23 |

Lọc `min_df = 5` (kỹ năng dưới 5 tin) và `min_weight = 3` (cạnh dưới 3 tin). Trọng số lưu hai dạng:
`weight` là số tin chứa cả hai, `npmi` là NPMI – đếm thô thiên về kỹ năng phổ biến nên cần dạng đã
chuẩn hóa.

#### Kết quả âm thứ nhất: PageRank không thêm gì so với bậc có trọng số

| Đồ thị | Spearman PageRank ~ strength | PageRank ~ số tin | Top-10 trùng nhau |
|---|---|---|---|
| từ điển | **0,986** | 0,958 | 10/10 |
| PhoBERT | **0,985** | 0,952 | 10/10 |

Trên đồ thị vô hướng, PageRank xấp xỉ tỷ lệ với strength – đây là tính chất đã biết của thuật toán,
và số đo xác nhận đúng như vậy. Top-10 "kỹ năng trung tâm" của hai cách **giống hệt nhau**: AI, API,
CI/CD, Docker, Python, SQL, AWS, Kubernetes, DevOps, PostgreSQL. Chỗ lệch hạng lớn nhất chỉ ở nhóm
đuôi (Photoshop 140 lên 97, Illustrator 146 lên 114) – kỹ năng ít tin nhưng nối với các kỹ năng đông.

**Kết luận phải viết đúng:** với đồ thị đồng xuất hiện một tầng như thế này, PageRank *không* cho tri
thức gì ngoài việc đếm. (Đọc kèm mục "PageRank: sửa trọng số" ở cuối phần WM6: bảng trên dùng
trọng số là **số tin**, đổi sang NPMI thì top-10 khác hẳn.) Muốn PageRank có ý nghĩa thì cần đồ thị có hướng hoặc nhiều loại đỉnh
(tin, kỹ năng, công ty), không phải đồ thị đồng xuất hiện đối xứng.

#### Kết quả âm thứ hai: modularity trên đồ thị thô không khác đồ thị ngẫu nhiên

Modularity **tự nó không nói gì**: đồ thị ngẫu nhiên cũng có Q dương. Mốc so sánh là Q của chính đồ
thị đó sau khi đảo cạnh giữ nguyên bậc (degree-preserving rewiring).

| Đồ thị từ điển | Cụm | Q thật | Q ngẫu nhiên (giữ bậc) | z | số lần ngẫu nhiên ≥ thật |
|---|---|---|---|---|---|
| thô (3.607 cạnh) | 4 | 0,158 | 0,148 ± 0,012 | 0,9 | **9/50** |
| NPMI ≥ 0,1 (2.190 cạnh) | 4 | 0,258 | 0,145 ± 0,020 | 5,6 | 0/30 |
| NPMI ≥ 0,2 (1.350 cạnh) | 5 | 0,372 | 0,182 ± 0,015 | 12,7 | 0/30 |
| **NPMI ≥ 0,3 (716 cạnh)** | **8** | **0,515** | **0,278 ± 0,011** | **22,1** | **0/100** |

Dòng đầu là điểm đáng nói: cụm nhìn bằng mắt thì hợp lý (Java/backend, BA/ERP, DevOps, ML) nhưng
**Q không phân biệt được với ngẫu nhiên** (9/50 đồ thị ngẫu nhiên còn cao hơn). Nguyên nhân là mật độ:
0,27 nghĩa là trung bình mỗi kỹ năng nối với hơn một phần tư số kỹ năng còn lại, đồ thị gần như một
khối. Phải bỏ các cạnh "gặp nhau chỉ vì cả hai đều phổ biến" thì cấu trúc mới hiện ra.

#### Chọn ngưỡng NPMI bằng độ ổn định, không bằng Q

Q tăng đơn điệu theo ngưỡng, nên **chọn ngưỡng theo Q là chọn theo chính số mình sắp báo cáo**. Tiêu
chí chọn dùng một đại lượng khác: cụm có lặp lại khi dựng trên một nửa dữ liệu khác hay không
(NMI giữa hai phân hoạch), đối chiếu với mốc gán cụm ngẫu nhiên.

| NPMI ≥ | Đỉnh chung | NMI (chia ngẫu nhiên) | mốc ngẫu nhiên | khoảng cách |
|---|---|---|---|---|
| 0,0 | 144 | 0,418 | 0,020 | 0,398 |
| 0,1 | 144 | 0,425 | 0,031 | 0,394 |
| 0,2 | 144 | 0,535 | 0,032 | 0,503 |
| **0,3** | 140 | 0,615 | 0,057 | **0,558** |
| 0,4 | 130 | 0,722 | 0,193 | 0,529 |
| 0,5 | 104 | 0,854 | 0,457 | 0,397 |

NMI thô vẫn tăng ở 0,4 và 0,5, nhưng **mốc ngẫu nhiên tăng theo** (0,46 ở ngưỡng 0,5): đồ thị vỡ
thành nhiều cụm nhỏ nên hai phân hoạch bất kỳ cũng tự giống nhau, và số đỉnh còn lại rơi từ 163 xuống
104. Lấy khoảng cách so với mốc thì đỉnh ở **0,3**. Chốt ngưỡng 0,3.

#### Kết quả dương: 8 cụm kỹ năng, ổn định và khác ngẫu nhiên rõ rệt

Đồ thị từ điển, NPMI ≥ 0,3: 160 đỉnh, 716 cạnh, Q = **0,515** (ngẫu nhiên 0,278 ± 0,011, z = 22,1,
0/100 lần ngẫu nhiên vượt). Ổn định giữa 5 seed Louvain: NMI 0,83–0,96.

| Cụm | Kỹ năng | Kỹ năng nhiều tin nhất | Đọc ra là gì |
|---|---|---|---|
| 1 | 35 | API, Agile, Jira, Agile/Scrum, Phân tích yêu cầu, Scrum, Figma, UI/UX | BA / quản lý sản phẩm |
| 2 | 28 | JavaScript, TypeScript, ReactJS, C#, Node.js, .NET, CSS, HTML | Frontend và .NET |
| 3 | 27 | Java, Git, PostgreSQL, Microservices, RESTful API, MySQL, Kafka, SQL Server | Backend Java |
| 4 | 22 | CI/CD, Docker, AWS, DevOps, Kubernetes, Azure, GCP, Golang | DevOps / cloud |
| 5 | 15 | Python, Machine Learning, C++, R, FastAPI, C/C++, PyTorch, Deep Learning | ML / khoa học dữ liệu |
| 6 | 14 | Linux, Bash, Windows, Firewall, TCP/IP, VPN, VMware, Mạng máy tính | Hệ thống / mạng |
| 7 | 11 | ERP, Phân tích nghiệp vụ, Phân tích dữ liệu, CRM, ETL, Power BI, Odoo, Spark | ERP / BI |
| 8 | 8 | GitHub, Kotlin, Swift, Flutter, MVVM, XCode, Objective-C, Dart | Mobile |

Tám cụm **đọc ra được** thành các nhóm nghề quen thuộc, và có được mà không cần gán nhãn. *(Sửa sau phản
biện 2026-11-17: bản trước viết "khớp với các vai trò nghề thật trong ngành IT Việt Nam" – phát biểu
đó chưa chứng minh được. Không có mốc ngoài để đối chiếu (cột "đọc ra là gì" là cách nhóm đọc), và
chia theo nguồn cho NMI 0,476 / ARI 0,399, thấp hơn mốc chia ngẫu nhiên 0,615 / 0,542: cấu trúc cụm
**phụ thuộc một phần vào trang web**. Phát biểu đúng là: trên 828 tin TopCV + ITviec này có 8 cụm khác
ngẫu nhiên rõ rệt; phần chung giữa hai nguồn là thật nhưng chưa đo được nó gồm những cụm nào.)*

#### Kết luận không phụ thuộc bộ trích kỹ năng

Dựng lại toàn bộ bằng PhoBERT WM2 thay vì từ điển:

| | từ điển | PhoBERT |
|---|---|---|
| Q (NPMI ≥ 0,3) | 0,515 | 0,517 |
| Q ngẫu nhiên | 0,278 ± 0,011 | 0,303 ± 0,007 |
| z | 22,1 | 29,3 |
| số cụm | 8 | 7 |
| ổn định theo seed (NMI) | 0,83–0,96 | 0,95–1,00 |

Hai phân hoạch trùng nhau nhiều trên 145 đỉnh chung: **NMI 0,742 / ARI 0,646**. Cụm lớn gần như giống
nhau; khác chủ yếu ở chỗ PhoBERT đặt `Python` cùng nhóm hệ thống/mạng (`Linux`, `Bash`) còn từ điển
đặt cùng nhóm ML, và PhoBERT gộp `Figma` và `UI/UX` vào nhóm ERP/thiết kế thay vì nhóm BA.

#### Cụm có phải nếp riêng của một trang web không

Dựng đồ thị riêng cho từng nguồn rồi so phân hoạch (NPMI ≥ 0,3, `min_df` 3, `min_weight` 2):

| Cách chia hai nửa | Đỉnh chung | NMI | ARI | mốc ngẫu nhiên (NMI) |
|---|---|---|---|---|
| ngẫu nhiên (trần thực tế của nửa dữ liệu) | 140 | 0,615 | 0,542 | 0,057 |
| **theo nguồn** (TopCV so với ITviec) | 134 | **0,476** | 0,399 | 0,056 |
| theo thời gian | 139 | 0,571 | 0,404 | 0,079 |

Chia theo nguồn cho NMI **thấp hơn** mốc chia ngẫu nhiên (0,476 so với 0,615), nên cấu trúc cụm
**có một phần phụ thuộc trang web**, chưa phải tính chất chung của thị trường. Vẫn cao hơn hẳn mức
ngẫu nhiên, nên phần chung là thật.

Số "theo thời gian" **không đọc được như độ ổn định theo thời gian**: hai snapshot lệch nhau về thời
gian (TopCV 08–10/2026, ITviec 09–11/2026) nên chia theo ngày đăng cũng gần như chia theo nguồn
(nửa 1: 305 TopCV / 128 ITviec; nửa 2: 26 TopCV / 408 ITviec). Muốn đo ổn định theo thời gian thật
thì phải crawl thêm một đợt cùng nguồn ở thời điểm khác.

#### Hạn chế

- **Tin trùng chưa được gộp** (WM1 đang gán nhãn): một vị trí đăng cả TopCV và ITviec bị đếm hai lần,
  làm cạnh giữa các kỹ năng của nó dày lên. Có `--collapse-dup` để thử độ bền khi có nhãn WM1.
- **Đỉnh `AI` đứng đầu mọi bảng xếp hạng là một phần lỗi của WM2**: phân tích lỗi WM2 đã ghi `AI` là
  span thừa nhiều nhất (19 lần), vì từ điển khớp cả `AI solutions`, "giải pháp AI". Không nên trích
  "AI là kỹ năng trung tâm nhất" như một phát hiện.
- 867 tin là nhỏ cho một đồ thị 163 đỉnh. Cụm nhỏ (mobile 8 kỹ năng) dựa trên ít tin.
- Không có mốc ngoài để đối chiếu cụm (ví dụ nhóm nghề ESCO), nên phần "đọc ra là gì" là đánh giá
  định tính của nhóm, không phải số đo.

Lệnh: `uv run python -m graph.build --extractor dict` rồi `uv run python -m graph.analyze rank` rồi
`uv run python -m graph.analyze cluster --min-npmi 0.3 --n-null 100` rồi
`uv run python -m graph.analyze stability --split source --min-npmi 0.3`

### PageRank: sửa trọng số, và chỗ PageRank thật sự thắng phép đếm (2026-11-17)

Kết quả âm ở mục trên (PageRank tương quan 0,986 với bậc có trọng số) đo trên trọng số là **số tin**.
Đó là một lựa chọn sai, không phải tính chất của PageRank. Chạy lại với trọng số NPMI:

| Trọng số dùng cho PageRank | Spearman với bậc có trọng số | Spearman với số tin | Top-10 trùng |
|---|---|---|---|
| `weight` (số tin) | 0,986 | 0,958 | 10/10 |
| **`npmi`** | 0,898 | **0,689** | 8/10 |

Top-10 đổi hẳn: `AI`, `API`, `SQL`, `Python` rơi ra, thay bằng **Docker, PostgreSQL, RESTful API,
CI/CD, MySQL, Kubernetes, Microservices, Git, ReactJS, Kafka**. Lệch hạng lớn nhất: `Jira` 103 → 22,
`Confluence` 84 → 19, `Figma` 111 → 31 – các công cụ gắn chặt trong cụm của mình nhưng không phổ biến
toàn thị trường.

Vậy PageRank **khác phép đếm số tin** (0,689), nhưng vẫn **gần bậc có trọng số** (0,898): phần cải
thiện nằm ở cách đặt trọng số cho đồ thị, không phải ở thuật toán. Kết luận âm ban đầu được giữ, chỉ
sửa lại cho đúng: *PageRank toàn cục không thêm gì so với bậc có trọng số trên cùng trọng số đó.*

#### Thử đồ thị có hướng: không cứu được

PageRank cần hướng mới có ý nghĩa. Quan hệ bất đối xứng có thật trong dữ liệu là xác suất điều kiện:
`P(Docker | Kubernetes)` = 112/144 = 0,78 nhưng `P(Kubernetes | Docker)` = 112/178 = 0,63. Dựng đồ thị
có hướng, mỗi cặp chỉ giữ chiều trội (kỹ năng chuyên biệt trỏ về kỹ năng nền tảng), trọng số
`P(v|u)`:

| | Spearman với bậc vô hướng | với số tin | với bậc vào có trọng số |
|---|---|---|---|
| PageRank trên đồ thị có hướng | 0,856 | 0,911 | **0,983** |

Top-10 **không đổi một vị trí nào**. PageRank trên đồ thị đó gần như bằng bậc vào (0,983). Chỗ nó đổi
là phần đuôi, và đổi theo kiểu đọc được: `Swift` 103 → 38, `Photoshop` 107 → 50, `Illustrator`
137 → 85 lên hạng (các kỹ năng nền tảng *trong một nhóm hẹp*, được nhiều kỹ năng chuyên biệt trỏ về),
còn `Odoo` 99 → 146, `JMeter` 89 → 135, `Viết Testcase` 114 → 159 tụt (các kỹ năng chuyên biệt trỏ ra
ngoài). Hướng này không đáng theo tiếp.

#### PageRank cá nhân hoá: hơn phép đếm ở Recall@10, không hơn ở MRR

> *Tiêu đề sửa sau phản biện 2026-11-17 (bản trước: "đây là chỗ nó thắng"). Kiểm định ghép cặp ở
> cuối mục này.*

PageRank toàn cục xếp hạng một lần cho cả thị trường nên luôn có thể thay bằng đếm. **PageRank cá nhân
hoá** thì không: khởi động lại ngẫu nhiên chỉ về các kỹ năng của một hồ sơ, nên đầu ra phụ thuộc hồ sơ.
Dùng được làm bộ gợi ý kỹ năng cho WM5 và cho hồ sơ kỹ năng của app (UC004).

**Cách đánh giá (`graph/recommend.py`).** Không có nhãn "kỹ năng nên học tiếp", nên dùng bài **đoán kỹ
năng bị che**: mỗi tin tuyển dụng là một hồ sơ thật; che một kỹ năng, đưa phần còn lại làm hồ sơ, xem
hệ xếp kỹ năng bị che lên hạng bao nhiêu. Đồ thị dựng **chỉ trên nửa train**, đánh giá trên các tin ở
nửa test, nên kỹ năng bị che không nằm trong đồ thị của chính tin đó. Khoảng 318 ca mỗi lần chia.

Bốn hệ, mỗi hệ phải hơn hệ trước mới đáng làm (trung bình 4 lần chia train/test):

| Hệ | Recall@10 | MRR |
|---|---|---|
| `popular` (theo số tin, không nhìn hồ sơ) | 0,358 ± 0,010 | 0,174 ± 0,012 |
| `count` (tổng số tin đồng xuất hiện với hồ sơ) | 0,461 ± 0,014 | 0,232 ± 0,006 |
| `count-npmi` (tổng NPMI) | 0,489 ± 0,035 | 0,247 ± 0,023 |
| **`ppr`** (PageRank cá nhân hoá, alpha 0,35, NPMI) | **0,529 ± 0,031** | 0,255 ± 0,028 |

Δ so với `count-npmi` từng lần chia:

| | lần 1 | lần 2 | lần 3 | lần 4 |
|---|---|---|---|---|
| Recall@10 | +0,051 | +0,044 | +0,010 | +0,056 |
| MRR | +0,021 | +0,005 | **−0,022** | +0,024 |

**Recall@10 hơn ở cả 4/4 lần chia; MRR chỉ 3/4.** Đọc đúng là: PPR đưa được nhiều kỹ năng đúng vào
top-10 hơn, nhưng khi cả hai đều tìm ra thì phép đếm xếp nó cao hơn một chút. Chênh lệch nhỏ (khoảng
+0,04 Recall@10), nên đây là một thắng lợi vừa phải, không phải bước nhảy.

**Kiểm định ghép cặp** (thêm sau phản biện 2026-11-17). Gộp mọi ca của 4 lần chia (1.251 ca, 591 tin),
bootstrap **theo tin** vì một tin có thể rơi vào nửa test của nhiều lần chia:

| | Δ (ppr − count-npmi) | CI95 | p(Δ≤0) |
|---|---|---|---|
| Recall@10 | **+0,040** | **[+0,021; +0,059]** | 0,000 |
| MRR | +0,007 | [−0,007; +0,020] | 0,162 |

Kiểm định dấu trên top-10: PPR trúng mà `count-npmi` trượt **89 ca**, ngược lại **39 ca**, p hai phía < 0,001.
Kết luận đúng phạm vi: PPR đưa **nhiều kỹ năng đúng vào top-10 hơn** (có ý nghĩa), nhưng **không xếp
chúng cao hơn** (MRR không có ý nghĩa). Lưu ý còn lại: `alpha` chọn trên seed 1, và nửa test của seed 2–5
có chung tin với dữ liệu seed 1 – chưa có tập giữ lại hoàn toàn sạch cho việc chọn `alpha`.

**Hai tham số, và cách chọn.** `alpha` (xác suất đi tiếp thay vì nhảy về hồ sơ) hạ từ 0,85 xuống 0,35,
vì 0,85 là giá trị cho người lướt web còn ở đây cần đi gần hồ sơ. Ảnh hưởng rất lớn:

| Cấu hình `ppr` (lần chia seed 1) | Recall@10 | MRR |
|---|---|---|
| alpha 0,85, trọng số số tin (mặc định của networkx) | 0,384 | 0,195 |
| alpha 0,85, NPMI | 0,421 | 0,208 |
| alpha 0,50, NPMI | 0,538 | 0,250 |
| **alpha 0,35, NPMI** | **0,557** | 0,259 |
| alpha 0,20, NPMI | 0,535 | 0,257 |

Dòng đầu là điểm đáng nhớ: để nguyên mặc định thì PPR **thua cả `count`** (0,384 so với 0,447 ở lần
chia đó). Hai tham số chọn trên **seed 1**, các số báo cáo ở bảng chính đo trên **seed 2–5** để không
báo cáo trên chính lần chia đã dùng để chọn.

**Ví dụ hồ sơ `Java, SQL`** – thấy rõ từng mốc thêm được gì:

| # | `popular` | `count` | `count-npmi` | `ppr` |
|---|---|---|---|---|
| 1 | AI | AI | Spring Boot | Spring Boot |
| 2 | Python | API | Hibernate | Spring |
| 3 | API | Docker | Spring | Hibernate |
| 4 | CI/CD | Python | Microservices | PostgreSQL |
| 5 | Docker | Microservices | Oracle | Oracle |

`popular` và `count` trả về các kỹ năng phổ biến nhất thị trường, vô dụng cho hồ sơ này. Đổi sang NPMI
thì ra đúng nhóm Java. `ppr` thêm được các kỹ năng cách hồ sơ hai bước (`PostgreSQL`, `Kafka`) mà phép
đếm một bước không với tới.

#### Hạn chế

- Kỹ năng trích bằng **từ điển**, không phải PhoBERT, nên hồ sơ và đáp án đều mang sai số của WM2.
- Một tin tuyển dụng không phải một người. Bài "đoán kỹ năng bị che" đo xem hệ có nắm được cách các kỹ
  năng đi cùng nhau trong tin hay không, **không** chứng minh gợi ý này hữu ích với người tìm việc thật.
- Chênh lệch nhỏ và MRR không nhất quán. Nếu chỉ cần một bộ gợi ý đủ dùng thì `count-npmi` rẻ hơn
  nhiều (không phải giải PageRank cho mỗi hồ sơ) mà chỉ kém khoảng 0,04 Recall@10.

Lệnh: `uv run python -m graph.analyze rank --weight npmi` rồi `uv run python -m graph.recommend` rồi
`uv run python -m graph.recommend --profile Java SQL`

## WM5 – gợi ý việc làm

### Baseline và content-based trên log synthetic (2026-11-12)

> **Đã thay bằng số của log đã sửa** (mục "Sửa log đã sửa" ngay sau mục này): log cũ dồn 74% lượt xem vào một ngày.

- Log synthetic `recsys/events.py`: 400 người dùng ảo, mỗi người thuộc một nhóm nghề (mức 2 của `category`),
  hồ sơ kỹ năng rút từ kỹ năng phổ biến của nhóm; 70% lượt xem trong nhóm, 30% ngoài nhóm;
  thời điểm xem = ngày đăng + 0..21 ngày. **3.541 lượt xem trên 304 tin** (8,9 lượt/người).
- Chia theo thời gian (mốc ở phân vị 70% của lượt xem): train 929 / test 2.612; 394 người dùng có nhãn test.

| Chiến lược | Recall@10 | nDCG@10 |
|---|---|---|
| `popularity` (baseline, không cá nhân hóa) | 0,046 | 0,030 |
| `content-skill` (trùng kỹ năng, trọng số IDF) | 0,143 | 0,159 |
| `content-tfidf` (TF-IDF hồ sơ ↔ văn bản tin) | **0,174** | **0,181** |
| `hybrid` (tfidf + 0,1 × độ phổ biến) | 0,168 | 0,177 |

- Content-based hơn baseline khoảng **6 lần nDCG** *(log cũ, sai cách chia – log đã sửa: 4,7 lần; và vì
  log sinh theo đúng giả định mà `content-*` dùng để xếp hạng, đây chỉ là kiểm tra cài đặt)*. Ghép thêm độ phổ biến không giúp gì (0,177 so với 0,181).
- **Hạn chế phải ghi trong báo cáo:** log do chính nhóm sinh ra theo giả định "người dùng xem tin cùng nhóm nghề",
  mà `content-*` lại xếp hạng theo đúng tín hiệu đó → số này chỉ so sánh các chiến lược với nhau,
  không chứng minh được gì về người dùng thật. Cần bổ sung chấm tay (~20 hồ sơ × top 10).
- Hai lỗi thiết kế đã sửa trong lúc làm, ghi lại để không lặp: (1) đặt thời điểm xem **đúng bằng** ngày đăng
  khiến mỗi tin chỉ nằm một phía của mốc chia, baseline độ phổ biến luôn = 0; (2) chia theo danh sách ngày
  thay vì theo phân vị lượt xem cho train chỉ 239 lượt (ngày đăng dồn về cuối kỳ).
- Lệnh: `uv run python -m recsys.events` → `uv run python -m recsys.baseline --eval-set reco_synthetic_clamped`

### Sửa log đã sửa: chia theo thời gian của bản cũ không phải chia theo thời gian (2026-11-17)

Phản biện hỏi vì sao mốc ở phân vị 70% mà train 929 / test 2.612. Kiểm lại thì có **hai lỗi chồng nhau**:

1. **Bộ sinh log** (`recsys/events.py`): thời điểm xem = ngày đăng + 0..21 ngày, rồi
   `min(..., last_day)`. Bộ sinh lại ưu tiên tin mới (rút 3 tin, lấy tin mới nhất), nên phần lớn lượt
   xem tràn quá ngày cuối và bị **dồn về đúng ngày cuối**: 2.612/3.541 lượt (74%) rơi vào 2026-10-12,
   trong khi ngày đông thứ hai chỉ có 143. Ngày đó chỉ có 30/304 tin được đăng.
2. **Hàm chia** (`recsys/baseline.py`): lấy phần tử ở vị trí phân vị làm mốc rồi đưa mọi lượt `>= mốc`
   sang test. Mốc rơi đúng ngày đông đó, cả khối sang test.

Hệ quả: test của log cũ là "toàn bộ ngày cuối", train là cái đuôi trước nó. Số 0,174 / 0,181 ở trên đo
trên cách chia đó.

**Sửa.** Bộ sinh **bỏ** lượt xem rơi sau ngày cuối (chưa quan sát được, như log thật cắt ở ngày crawl)
thay vì dồn, và rút tiếp tới khi người dùng đủ số lượt xem. Hàm chia chọn **ranh giới giữa hai ngày**
cho tỷ lệ train gần mục tiêu nhất. Đã thử một cách sửa trung gian (chỉ rút độ trễ trong số ngày còn
lại) và bỏ: vẫn dồn 36% lượt xem vào ngày cuối.

| Log | Lượt xem | Ngày đông nhất | Chia thực tế (mục tiêu 70/30) |
|---|---|---|---|
| log cũ | 3.541 | 74% | 26 / 74 |
| **log đã sửa** | 4.700 | 14% | **75 / 25** (test = 2 ngày cuối) |

Ở log đã sửa số lượt xem tăng dần về cuối kỳ (ngày cuối 658, áp chót 535, trước đó 488) – đúng hướng, vì càng
về cuối càng nhiều tin đã được đăng để xem.

| Chiến lược | log cũ Recall@10 | log cũ nDCG@10 | **log đã sửa Recall@10** | **log đã sửa nDCG@10** |
|---|---|---|---|---|
| `popularity` (baseline) | 0,046 | 0,030 | 0,027 | 0,015 |
| `content-skill` | 0,143 | 0,159 | 0,069 | 0,058 |
| `content-tfidf` | 0,174 | 0,181 | **0,102** | **0,071** |
| `hybrid` | 0,168 | 0,177 | 0,097 | 0,072 |

Thứ tự các chiến lược không đổi, nhưng mọi số giảm khoảng một nửa và câu "content-based hơn baseline
khoảng 6 lần nDCG" không còn đúng (log đã sửa: 4,7 lần). **Số WM5 chính thức từ nay là cột log đã sửa.**

Hạn chế lớn hơn vẫn nguyên: log do nhóm sinh theo giả định "người dùng xem tin cùng nhóm nghề", và
`content-*` xếp hạng theo đúng tín hiệu đó. Sửa lỗi chia không sửa được vòng tròn này; số này chỉ kiểm
tra cài đặt, không chứng minh gợi ý hữu ích với người thật. Vẫn cần chấm tay (hồ sơ × top-10, chấm mù).

Lệnh: `uv run python -m recsys.events` (ra `reco_events.jsonl`) →
`uv run python -m recsys.baseline --eval-set reco_synthetic`

### Crawl thử TopCV (2026-10-12)

- Lệnh: `uv run python -m crawler.topcv.run --max-jobs 20` (parser `topcv-parser:0.1.0`, bộ lọc slug bản đầu).
- 23 request (1 robots.txt, 2 sitemap, 20 trang tin), tất cả HTTP 200, không bị chặn, 30 giây.
- 4/20 trang là tin IT (danh mục chính "Công nghệ Thông tin"), 0 lỗi parse, 4/4 khớp `job_posting.v1`, 4/4 có `date_posted`, 2/4 có lương dạng số.
- Bộ lọc slug bản đầu khớp chuỗi con ("ai" khớp "tai") → sửa sang khớp từ nguyên vẹn: số URL lọt lọc trong một sitemap con giảm 29 → 8/200.
- Sitemap tin TopCV: 220 file con × ~200 URL ≈ 44.000 tin đang có. Ước tính crawl toàn bộ tin IT: ~2.000 request (~35–40 phút).
- Tag "Kỹ năng cần có" của nhà tuyển dụng lẫn kỹ năng mềm ("Giao tiếp", "Làm việc nhóm") và cụm dài → nhãn yếu WM2 phải lọc qua từ điển alias.

### Crawl TopCV đợt 1 và sự cố HTTP 429 (2026-10-12)

**Sự cố:** lần chạy `--max-jobs 2000 --max-sitemaps 220` (19:56–21:52) bị TopCV trả **HTTP 429 (Too Many Requests)** từ khoảng 20:40. Spider bản cũ không dừng mà thử lại (RETRY_TIMES = 2), AUTOTHROTTLE còn rút ngắn khoảng cách vì 429 trả về nhanh → **5.507 request, 4.673 bị 429**, 832 thành công. Khi theo dõi, agent chỉ nhìn số trang/phút nên báo nhầm là "máy chủ chậm".
**Đã sửa (`crawler/topcv/spider.py`):** gặp 429/403 là dừng cả lần chạy, không thử lại; tối thiểu 3 giây/request; tối đa 1 lần thử lại cho lỗi 5xx; dừng khi quá 20 lỗi. **Bài học:** theo dõi crawl phải xem mã HTTP (`response_status_count`), không chỉ số trang.
**Từ nay:** mỗi ngày tối đa vài trăm request, chia nhỏ; không chạy lại trong ngày đã bị 429.

**Dữ liệu thu được (đợt 1, gộp lần thử):** 304 tin IT khác nhau.

| Chỉ số | Giá trị |
|---|---|
| Lương dạng số / "Thỏa thuận" | 55% / 44% |
| Có tag "Kỹ năng cần có" | 51% (median 1 tag/tin; trung bình 5,1) |
| Tag phổ biến | Python 17, SQL 15, **Giao tiếp 14, Làm việc nhóm 11**, Java 10, Giải quyết vấn đề 9 – kỹ năng mềm lẫn nhiều |
| `date_posted` | 100% có; 17/08–12/10/2026 (09: 146 tin, 10: 157 tin) – sitemap chỉ chứa tin đang mở |
| Nhóm nghề | Software Engineering 60, IT Infrastructure 59, Software Testing 37, Thiết kế 31, Product Management 27, AI 18 |
| Địa điểm | Hà Nội 199, TP.HCM 70, Đà Nẵng 8 |
| Độ dài mô tả + yêu cầu | median 301 từ; 100% có phần yêu cầu |

### Tập test WM2 `skill_test1` (2026-10-12)

- Snapshot `topcv_20261012`: 304 tin IT TopCV, ngày đăng 17/08–12/10/2026, ids_sha256 `61bad0f9…d1377048`. Lệnh: `uv run python -m crawler.snapshot --source topcv --name topcv_20261012`.
- Rút mẫu: 1.000 câu từ 125 tin (tối đa 8 câu/tin, seed 20261012), 96 câu của 12 tin để đo κ. Nhóm nghề: hạ tầng IT 24, phát triển phần mềm 21, testing 17, thiết kế 15, product 14, AI 9.
- Có câu tiếng Anh (tin của công ty nước ngoài).
- Gán xong 1.000 câu (2026-11-12), 1 người, không gợi ý sẵn: 477 câu có kỹ năng (48%), 1.169 span.
- κ lần 1 (2026-11-12, guideline 0.3): 96 câu double, người thứ hai gán trên project riêng không thấy nhãn người thứ nhất.
  Cohen's κ BIO mức token = **0,591** (1.839 token); F1 span strict giữa hai người = 0,709; 36/96 câu lệch.
  Dưới mục tiêu 0,7 → bàn các câu lệch, chốt guideline 0.4 (tài liệu BA, wireframe, cloud/AI, bảo mật, "quản lý", nghiệp vụ ngành, thiết bị hạ tầng, động từ chung, ranh giới span).
- Sửa nhãn test theo 0.4 (2026-11-12): 57 câu. κ lần 2: 50 câu ngẫu nhiên khác (seed 20261112, task 1604–2507), người thứ hai gán theo 0.4 trên project riêng.
  Kết quả: Cohen's κ BIO mức token = **0,650** (953 token); F1 span strict giữa hai người = 0,781; 18/50 câu lệch.
  Lệnh: `uv run python -m annotation.kappa_skill` (trước là script tạm `kappa2.py`, cùng cách tính). Chạy lại bây giờ ra κ 0,675 / F1 0,800 / 16 câu lệch, vì 4 nhãn người 1 đã sửa sau khi đo và Label Studio không giữ bản cũ; số chính thức vẫn là 0,650.
  Lệch chủ yếu do người thứ hai gán sót tên cụ thể và một câu bôi nhầm cả câu; 4 câu nhãn người thứ nhất sai theo 0.4 đã sửa (1726, 1814, 1906, 2051). Dưới 0,7 nhưng ở mức "substantial" (Landis & Koch) → chốt, không đo vòng 3.
- **Đóng băng TEST (2026-11-12):** `data/annotation/skill_test1.bio.jsonl`, 1.000 câu, 463 câu có kỹ năng, 1.149 span, sha256 `9f7a2a0c…fbefba0362`.
  Lệnh: `uv run python -m annotation.export_bio --project 3 --batch skill_test1`. Từ đây không sửa nhãn test.

### Kết quả trên test `skill_test1` (2026-11-12)

> **Số WM2 chính thức từ 2026-11-18 là của nhãn yếu self-training** (F1 0,617), xem mục "WM2 – chốt nhãn yếu self-training"
> ở cuối file. Bảng dưới là của bản nhãn tag, giữ lại để đối chiếu.

| Phương pháp | P | R | F1 (seqeval strict) | ΔF1 so với từ điển, CI95 bootstrap ghép cặp |
|---|---|---|---|---|
| Từ điển `dict-alias` (baseline) | 0,742 | 0,315 | 0,442 [0,398; 0,488] | – |
| PhoBERT `weak-tag`, 3 seed | 0,705 ± 0,014 | 0,469 ± 0,026 | 0,562 ± 0,014 | +0,111 → +0,136 (seed tệ nhất: [+0,083; +0,141]) |
| PhoBERT + từ điển, 3 seed | 0,699 ± 0,014 | 0,474 ± 0,026 | 0,564 ± 0,014 | +0,114 → +0,138 |

- Cả 3 seed đều hơn baseline, khoảng tin cậy không chứa 0 (1.000 lần bootstrap theo câu). Ghép thêm từ điển chỉ +0,002, không đáng kể.
- So với dev, F1 giảm (0,515 → 0,442 với từ điển; 0,596 → 0,562 với PhoBERT): dev từng được gợi ý sẵn bằng từ điển và cùng nguồn VietJobs; test gán tay không gợi ý, nguồn TopCV.
- Run chạy khi repo chưa commit sạch (`217f81c-dirty`) → chạy lại sau khi commit để số gắn với một commit.
- Lệnh: `uv run python -m ie.baseline_dict --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --snapshot topcv_20261012`;
  `uv run python -m ie.phobert eval --model data/models/wm2-phobert-tag-s<N> --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --seed <N>`;
  `uv run python -m experiments.paired_wm2 --bio data/annotation/skill_test1.bio.jsonl` (ΔF1, CI ghép cặp).

### Phân tích lỗi PhoBERT trên test (seed 1, F1 0,555; xem tay ~80 câu lỗi)

Seed 1: 628 span bỏ sót, 207 span thừa, 413/1.000 câu có lỗi. Số theo nhóm của 3 seed gần như nhau.

| Nhóm lỗi | Số (seed 1) | Ví dụ | Nguyên nhân |
|---|---|---|---|
| Câu có kỹ năng bị đoán rỗng hoàn toàn | 149/463 câu | "phát triển ứng dụng Native iOS … SWIFT" → không có span | Nhãn yếu chỉ bắt ~40% kỹ năng; mô hình học thói bỏ sót |
| Bỏ sót tên Latin 1 token | 232 span | `UAT` (8), `Android`, `iOS`, `LLM`, `RAG`, `GoldenGate`, `HiStaff`, `Freshchat` | Tên hiếm, ngoài từ điển và ngoài tag nhà tuyển dụng |
| Bỏ sót cụm Latin nhiều token | 182 span | `functional testing`, `High Availability`, `Data Warehouse`, `liquidity pools`, `SAP CO` | Như trên; thêm khái niệm nghiệp vụ (DeFi, SAP) |
| Bỏ sót cụm tiếng Việt | 129 span | `kiểm thử tự động`, `cân bằng tải`, `trực quan hóa dữ liệu`, `tối ưu cơ sở dữ liệu`, `thiết kế kịch bản` | Tag nhà tuyển dụng gần như toàn tiếng Anh; từ điển ít cụm tiếng Việt |
| Lệch ranh giới | 85 vàng / 72 đoán | `Maven / Gradle`, `Ethereum / EVM` gộp một span; `UI / UX` thay vì `thiết kế UI / UX`; `Docker` thay vì `Docker Compose`; `AI` thay vì `AI Agent Testing` | Nhãn yếu gộp dấu "/" và lấy tag ngắn |
| Span thừa (không chồng vàng) | 135 | `AI` (19), `API` (11), `testing`, `mạng`, `Camera IP`, `tủ Rack`, `Fiber`, `Lập test plan` | Nhãn yếu theo tag nhà tuyển dụng, không theo guideline (từ chung, thiết bị, tài liệu) |

- Các khái niệm guideline 0.4 mới thêm (wireframe, prototype, `cân bằng game`, `core loop`, AI/cloud đứng riêng, `UAT`) gần như không có trong nhãn yếu → mô hình bỏ sót. Đây là độ lệch giữa định nghĩa nhãn yếu và định nghĩa nhãn vàng, không chỉ là nhiễu.
- Nhãn vàng còn vài span lệch guideline (`Xây dựng dashboard`, `Thiết kế luồng xử lý dữ liệu`, `Delivery Support`); test đã đóng băng nên giữ nguyên, ghi vào hạn chế.
- Hướng cải thiện (đánh giá trên dev, không chạm test): tách span theo dấu "/" trong nhãn yếu; bỏ các tag từ chung và thiết bị khỏi nhãn yếu theo guideline 0.4; thêm alias tiếng Việt và khái niệm 0.4 vào từ điển; self-training hoặc chỉ tính loss trên câu có span để giảm đoán rỗng.

## Việc ngày 2026-11-18 (sau bản rà soát `data/ra-soat-scale-2026-11-18.md`)

Ba việc đã hứa trong bản rà soát, cùng một sự cố crawl. Không chấm thêm hệ nào ngoài **một** lần
chấm WM2 self-training đã lên kế hoạch trước.

### WM2 – chốt nhãn yếu self-training trên TEST: F1 0,442 → 0,617 (2026-11-18)

Chọn **bản self-training** trước khi chấm, theo số dev đã có: bản self-training cho F1 dev 0,644 ± 0,006 so với bản nhãn luật 0,642 ± 0,030 –
cùng điểm nhưng lệch giữa seed nhỏ hơn 5 lần. Chấm **một lần** trên `skill_test1` (1.000 câu đã
đóng băng, sha256 `9f7a2a0c…`), không chỉnh gì sau khi xem số.

| Phương pháp | P | R | F1 (seqeval strict) | ΔF1 so với từ điển, CI95 ghép cặp theo tin |
|---|---|---|---|---|
| Từ điển `dict-alias` | 0,742 | 0,315 | 0,442 [0,398; 0,488] | – |
| PhoBERT `weak-tag`, 3 seed (số cũ) | 0,705 ± 0,014 | 0,469 ± 0,026 | 0,562 ± 0,014 | +0,111 → +0,136 |
| **PhoBERT `weak-selftrain`, 3 seed** | **0,715 ± 0,006** | **0,543 ± 0,003** | **0,617 ± 0,001** | **+0,174 → +0,176**, mọi CI trong [+0,128; +0,224], p(Δ≤0) = 0,000 |
| PhoBERT `weak-selftrain` + từ điển | 0,697 ± 0,005 | 0,551 ± 0,003 | 0,615 ± 0,001 | +0,172 → +0,174 |

- Từng seed: 0,616 / 0,618 / 0,617. **Lệch giữa seed 0,001** – ổn định hơn bản nhãn tag (± 0,014) rất nhiều.
  Self-training ba seed đồng thuận (self-training) làm nhãn yếu bớt phụ thuộc lần khởi tạo.
- Mức tăng so với bản nhãn tag **nằm gần hết ở recall**: 0,469 → 0,543 (+0,074), precision gần như không đổi
  (0,705 → 0,715). Đúng chiều của chẩn đoán cũ: lỗi chính của bản nhãn tag là bỏ sót, không phải báo thừa.
- Ghép thêm từ điển vào PhoBERT self-training **không còn giúp** (0,615 so với 0,617): từ điển đã nằm trong nhãn yếu.
- Lần chấm này vẫn chạy khi repo chưa commit sạch (`runlog` đã in cảnh báo) → nằm trong việc chạy lại
  trên tag `report-wm`.

Lệnh: `uv run python -m ie.phobert eval --weak selftrain --model data/models/wm2-phobert-selftrain-s<N> --bio data/annotation/skill_test1.bio.jsonl --eval-set skill_test1 --split test --seed <N>`;
`uv run python -m experiments.paired_wm2 --bio data/annotation/skill_test1.bio.jsonl --prefix wm2-phobert-selftrain --out data/eval/skill_test1_preds_selftrain.json`

### WM3 – đối chiếu với điểm sao ITviec: phép đo mà luật `section` không thắng (2026-11-18)

Phép đo mức câu trên nhãn người là phép đo mà `section` gần như luôn thắng (0,583 so với 0,590,
p = 0,264), lại thêm chuyện người gán **nhìn thấy** `section`. Điểm sao thì không do người gán tạo ra
và có **riêng cho từng khía cạnh**: 1.241 bản ghi (1.100 review bị che), 75% review có sao khác nhau
giữa các khía cạnh (sd trong review median 0,49), và 23–32% ô có sao ≤ 3 – lời chê mà phần văn bản
công khai không có (0 review 1–2 sao).

Hai mức đo, số chính trên **99 review ngoài dev** (dev là nguồn train duy nhất của mô hình lai).
Spearman tính sau khi trừ trung bình theo khía cạnh ở cả hai phía; CI95 bootstrap 2.000 lần theo
review (mức review) hoặc theo công ty (mức công ty).

**Mức review** – đích là sao của chính review đó cho khía cạnh đó (289 ô / 99 review):

| Hệ | ρ | CI95 | AUC phát hiện sao ≤ 3 | số giá trị dự đoán khác nhau |
|---|---|---|---|---|
| từ điển `absa-dict` | 0,272 | [0,150; 0,371] | 0,617 | 15 |
| luật phần review | 0,239 | [0,112; 0,356] | 0,585 | 9 |
| **lai (từ điển + hồi quy logistic)** | **0,329** | [0,203; 0,430] | **0,635** | 10 |

- **lai so với luật phần review: Δρ = +0,090, CI95 [+0,022; +0,161], p(Δ≤0) = 0,005.**
- lai so với từ điển: Δρ = +0,057, CI95 [−0,061; +0,166], p = 0,178 (chưa đủ).

**Mức công ty** – đích là sao trung bình của các review **BỊ CHE** của công ty đó, tức nằm hoàn toàn
ngoài văn bản mà hệ đọc (278 ô / 96 công ty):

| Hệ | ρ | CI95 | AUC sao ≤ 3 |
|---|---|---|---|
| từ điển `absa-dict` | **−0,052** | [−0,171; 0,076] | 0,546 |
| luật phần review | 0,154 | [0,033; 0,258] | 0,539 |
| **lai** | **0,196** | [0,076; 0,296] | 0,587 |

- **lai so với từ điển: Δρ = +0,247, CI95 [+0,117; +0,360], p(Δ≤0) = 0,000.**
- lai so với luật phần review: Δρ = +0,042, CI95 [−0,025; +0,109], p = 0,116 (chưa đủ).

**Đọc kết quả – sửa lại kết luận của mục "Kiểm lại" ở phần WM3.**

1. Câu *"phần do học mà ra là không đáng kể"* **chỉ đúng với phép đo mức câu trên nhãn người**. Dưới
   một đích không do người gán tạo ra, mô hình lai hơn luật `section` **có ý nghĩa** ở mức review
   (+0,090, p = 0,005). Lý do dễ thấy: luật `section` cho cùng một cực cho mọi khía cạnh của một câu
   nên không thể bắt được phần biến thiên giữa các khía cạnh trong cùng một review, mà 75% review có
   biến thiên đó.
2. **Từ điển không mang tín hiệu mức công ty** (ρ = −0,052, CI chứa 0), trong khi mô hình lai thì có.
   Nói cách khác: từ điển nói được review này khen hay chê, không nói được công ty nào bị chê hơn.
3. Ở mức công ty, mô hình lai **không** tách được khỏi luật `section` (CI chứa 0). Hai kết quả này
   không mâu thuẫn: phần hơn của mô hình nằm ở chỗ phân biệt các khía cạnh *trong* một review, còn
   việc xếp hạng công ty thì cả hai hệ đều dựa phần lớn vào cấu trúc form.

**Hạn chế của chính phép đo này, phải ghi kèm:**

- ITviec chỉ chấm sao **5 khía cạnh**; `work_life_balance` không có sao, mà đó lại là khía cạnh cả hai
  hệ làm tệ nhất (độ đúng cực 0,468 / 0,677). Phép đo này không nói gì về nó.
- Sao là của **cả review**, dùng làm đích cho dự đoán mức câu → nhiễu đích. Nhiễu này hạ ρ của cả ba hệ
  như nhau nên vẫn so sánh được, nhưng ρ ≈ 0,33 **không** đọc như độ chính xác.
- ρ trả lời "có xếp đúng thứ tự hài lòng không", không trả lời "có gán đúng nhãn không". Phép đo này
  **bổ sung** cho macro-F1 trên TEST, không thay nó.
- Mô hình lai train trên 160 câu dev; cột "ngoài dev" loại 45 review dev nên sạch, nhưng từ điển
  `absa-dict` thì đã được chỉnh trên chính dev đó – lợi thế này nghiêng về phía **từ điển**, không nghiêng
  về mô hình.

Lệnh: `uv run python -m absa.company_eval --b 2000` → `data/eval/wm3_stars.json`

### Nhu cầu kỹ năng – bảng thống kê đầu tiên (2026-11-18)

Đề tài đăng ký là *"Mining Vietnamese Job Postings for Skill Demand"* nhưng tới nay `results.md` chỉ
có số chất lượng mô hình. Bốn bảng dưới sinh từ đầu ra trích kỹ năng, **không cần gán nhãn, không cần
crawl thêm**. Nguồn để riêng, không trộn: TopCV 331 tin, ITviec 536 tin (dữ liệu chính của môn),
VietJobs IT 1.906 tin và VietJobs đủ bộ 48.092 tin (**chỉ để lấy bề rộng**, không bao giờ là tập test).

Độ phủ bộ trích từ điển: TopCV 93% tin có ít nhất một kỹ năng, ITviec 97%, VietJobs IT 83%.

**Kỹ năng phổ biến nhất (bảng 1) và thiên lệch nguồn (bảng 2).** Cùng một kỹ năng, tỷ lệ tin khác
nhau rất xa giữa ba nguồn:

| Kỹ năng | % TopCV (331) | % ITviec (536) | % VietJobs IT (1.906) | chênh |
|---|---|---|---|---|
| AI | 27,2% | 45,5% | 14,2% | 31,3 điểm |
| Python | 16,3% | 34,1% | 10,3% | 23,9 |
| CI/CD | 12,4% | 27,4% | 6,1% | 21,3 |
| AWS | 9,1% | 27,4% | 6,7% | 20,7 |
| Photoshop | 3,3% | 0,9% | **17,6%** | 16,6 |

→ **Không được báo một con số "nhu cầu kỹ năng ở Việt Nam" gộp ba nguồn.** ITviec là tin tiếng Anh của
công ty IT nước ngoài (nên AWS/CI/CD/DevOps cao gấp 2–4 lần), còn nhóm IT của VietJobs có cả vị trí
thiết kế đồ họa (nên Photoshop đứng đầu). Thiên lệch nguồn ở đây lớn hơn mọi khác biệt giữa các mô hình
đã đo trong báo cáo này.

**Kỹ năng đặc trưng theo nhóm nghề (bảng 3)** – log-odds-ratio có tiên nghiệm Dirichlet (Monroe et al.
2008), chuẩn hóa theo độ lệch chuẩn; lấy "kỹ năng phổ biến nhất trong nhóm" thì nhóm nào cũng ra
Python/SQL. Chỉ đọc được trên TopCV: ITviec gắn một giá trị `category` phẳng cho cả 536 tin, VietJobs
IT cũng vậy sau khi lọc.

| Nhóm (TopCV, cấp 2) | tin | Kỹ năng đặc trưng (z) |
|---|---|---|
| Software Engineering | 64 | RESTful API (+4,3), Java (+4,0), OOP (+3,8), Spring Boot (+3,5) |
| IT Infrastructure and Operations | 64 | Windows (+5,1), Linux (+4,9), Firewall (+4,8), VPN (+4,2) |
| Software Testing | 38 | Kiểm thử phần mềm (+6,8), Postman (+5,8), Viết Testcase (+5,0), Selenium (+4,5) |
| Thiết kế | 35 | Figma (+8,0), Unity (+6,1), UI/UX (+5,7), Photoshop (+5,0) |
| Product Management | 30 | Phân tích nghiệp vụ (+6,9), UML (+3,4), Scrum (+3,0), Odoo (+3,0) |
| Artificial Intelligence (AI) | 20 | Python (+4,7), AI (+4,7), Deep Learning (+3,4), PyTorch (+2,9) |

7/14 nhóm đạt ngưỡng 15 tin. Các nhóm đọc ra đúng nghề, nhưng **cỡ nhóm 20–64 tin là quá nhỏ** để báo
tỷ lệ; chỉ nên đọc thứ tự.

**Nhu cầu theo tháng (bảng 4) – một kết quả âm đáng ghi.** Tách theo nguồn thì **không có xu hướng
thời gian nào**: TopCV tháng 09 (147 tin) và 10 (183 tin) cho AI 27% / 27%, API 28% / 23%; ITviec
tháng 10 và 11 cho AI 46% / 45%. Bản gộp hai nguồn *trông như* AI tăng 27% → 45% theo tháng, nhưng đó
chỉ là **chuyển nguồn**: `topcv_20261115` dừng ở 24/10 còn tin tháng 11 toàn của ITviec. Với dữ liệu chỉ phủ
2–3 tháng tin đang mở, bài này **không đo được xu hướng nhu cầu** – phải viết đúng như vậy.

**Bề rộng theo ngành (bảng 5, VietJobs đủ bộ 48.092 tin / 16 ngành).** Chỉ ở cỡ này mới đọc được
chuyện ngoài IT:

| Ngành | tin | Kỹ năng đặc trưng (z) |
|---|---|---|
| xây_dựng_kiến_trúc_bất_động_sản | 2.811 | AutoCAD (+56,5), SketchUp (+29,0), Revit (+27,8), 3ds Max (+24,4) |
| tài_chính_kế_toán_ngân_hàng_bảo_hiểm | 5.530 | Excel (+51,4), Tin học văn phòng (+22,5), Word (+20,9), ERP (+13,6) |
| marketing_truyền_thông_quảng_cáo | 5.950 | Canva (+34,3), Capcut (+32,7), Photoshop (+27,5), Google Analytics (+25,2) |
| thiết_kế_nghệ_thuật_giải_trí | 3.465 | Photoshop (+38,2), Premiere (+35,4), After Effects (+28,9) |
| công_nghệ_thông_tin_kỹ_thuật_số | 1.906 | API (+19,7), Java (+17,7), Git (+17,1), Python (+16,2) |

**Một lỗi từ điển mà chỉ cỡ 48.092 tin mới lộ ra:** alias một chữ bắt nhầm hàng loạt – `R` lên hạng 1
của ngành sản xuất (+19,9) và `C` vào nhóm nhân sự (+16,3), `Express` vào logistics (+8,7). Ở cỡ 331
tin thì không thấy. Cách sửa (chưa làm, phải đo lại trên dev WM2): alias dài 1–2 ký tự chỉ khớp khi có
ngữ cảnh ("R programming", "ngôn ngữ R"), không khớp trần.

Hạn chế chung của mọi bảng trên: từ điển có **200 kỹ năng chuẩn**, phủ 54,9% số lần gắn tag
`technical_skills` của VietJobs; đuôi dài 3.771 tag không được đếm. Tin trùng giữa hai nguồn chưa gộp
(WM1 chưa xong) nên một vị trí đăng hai nơi đếm hai lần; `--collapse-dup` để kiểm.

Lệnh: `uv run python -m experiments.skill_demand --top 10 --min-jobs 15`;
`uv run python -m experiments.skill_demand --all-categories` (đọc `data/vietjobs/VietJobs.csv`, 103 MB)

### Sự cố crawl TopCV: HTTP 429 sau 58 request (2026-11-18)

Chạy tiếp để lấp đủ tin IT (`--max-sitemaps 60 --max-jobs 400`, có thêm cờ mới `--skip-sitemaps` để
chia việc theo ngày). Kết quả: **60 request, 58 × HTTP 200, 2 × HTTP 429**, spider tự dừng
(`finish_reason: blocked_http_429`) sau 221 giây, tức 3,7 giây/request. Thu được **21 tin IT mới**
(`skipped_not_it` 29, 0 lỗi parse); `seen_ids.txt` 665 → 715, corpus TopCV 331 → 352 tin.

So với sự cố 12/10 (429 đến sau khoảng 800 request thành công, ở tốc độ nhanh hơn): **ngưỡng chịu
đựng của TopCV hiện thấp hơn một bậc.** Hệ quả cho kế hoạch:

- Giả định "500 request/ngày" trong `data/ra-soat-scale-2026-11-18.md` **sai**. Theo quan sát hôm nay,
  ngân sách thật có thể chỉ khoảng **50–60 request/ngày/IP** ở mức 3,7 giây/request.
- Nếu đúng vậy thì mục tiêu "đủ ~1.800 tin IT TopCV" cần ~30 ngày crawl liên tục → **không khả thi**
  trước hạn báo cáo. Phải đo lại ngưỡng trước khi hứa: lần chạy tới đặt `DOWNLOAD_DELAY` 10 giây,
  `--max-jobs 60`, và ghi lại request thứ bao nhiêu thì 429.
- Đường bù cho phần "scale" của thống kê nhu cầu và đồ thị kỹ năng: **VietJobs** (1.906 tin IT,
  48.092 tin toàn ngành, đã có trên máy, giấy phép rõ, trích dẫn Pham Dinh et al., LREC 2026). Nó
  không thay được tập test (quy tắc repo) nhưng thay được phần cần *bề rộng*.
- Hôm nay không chạm TopCV nữa (quy tắc: gặp 429 là dừng, không chạy lại trong ngày).

Lệnh: `uv run python -m crawler.topcv.run --max-sitemaps 60 --max-jobs 400`; log `data/logs/topcv_2026-11-18.log`

## Việc ngày 2026-11-20

### WM2 – phân tích lỗi mô hình nhãn LLM trên TEST (đã chấm, không dùng để chỉnh)

Đếm trên dự đoán đã lưu khi chấm TEST một lần (1.149 span vàng). "Lệch ranh giới" = span đoán chồng lên span
vàng nhưng không khớp đúng hai đầu.

| Hệ | F1 strict | F1 partial | Đúng | Lệch ranh giới | Bỏ sót | Báo thừa |
|---|---|---|---|---|---|---|
| Từ điển alias | 0,442 | 0,525 | 362 | 68 | 719 | 58 |
| PhoBERT nhãn LLM, seed 1 | 0,729 | 0,811 | 852 | 97 | 200 | 241 |
| PhoBERT nhãn LLM, seed 2 | 0,727 | 0,806 | 837 | 92 | 220 | 226 |
| PhoBERT nhãn LLM, seed 3 | 0,734 | 0,814 | 842 | 92 | 215 | 211 |

- Khoảng 8 điểm F1 mất vì ranh giới. Phần lớn là cụm động từ + đối tượng mà guideline tính cả cụm ("Xây dựng
  kịch bản kiểm thử" → đoán "Xây dựng"; "thiết kế UI / UX" → "UI / UX"), hoặc cụm tiếng Anh bị cắt/thừa một từ
  ("prototypes" → "prototypes and").
- Báo thừa nhiều nhất là các từ chung chung mà guideline không coi là kỹ năng khi đứng một mình: "AI" (12),
  "trải nghiệm người dùng" (6), "DevOps" (5), "cloud" (4). Bỏ sót nhiều nhất là từ viết tắt và thuật ngữ mới:
  "UAT" (5), "monitoring" (3), "RAG", "agent", "Codex".
- Báo thừa nay nhiều hơn bỏ sót (241 so với 200, seed 1); với từ điển thì ngược hẳn (58 so với 719).

### WM2 – độ ổn định của nhãn LLM giữa hai lần gán

Gán lại 300 câu dev bằng đúng cấu hình cũ (`gpt-6-luna`, cùng prompt, cùng guideline), chi phí ~$0,007.

| | P | R | F1 so với nhãn tay |
|---|---|---|---|
| Lần 1 (dùng để chọn mô hình LLM) | 0,864 | 0,834 | 0,849 |
| Lần 2 | 0,797 | 0,828 | 0,812 |

- Hai lần gán đồng thuận F1 0,878; 258/300 câu ra nhãn giống hệt. Chất lượng dao động ~0,04 F1 giữa hai lần
  gán, chủ yếu ở precision. Con số 0,849 đã báo nên đọc là "khoảng 0,81–0,85".
- Bộ nhãn train dùng lần gán duy nhất của nó; chưa đo ảnh hưởng của dao động này lên mô hình.

Lệnh: `uv run python -m ie.llm_label --model gpt-6-luna --bio data/annotation/skill_batch1.bio.jsonl --name dev_luna_rerun --eval`

### WM2 – tốc độ trên CPU

Bản full (PhoBERT) trên 352 tin TopCV, chạy trực tiếp trên máy dev (i7-11800H), tắt GPU, giới hạn 2 luồng
torch: **157 giây, tức ~0,45 giây/tin**, ra 10.110 dòng kỹ năng. Ước cho 50.000 tin: ~6,2 giờ với 2 CPU, chia
được theo lô để chạy song song. Lúc đo máy đang train mô hình khác trên GPU nên số này hơi bi quan. Chưa đo
được trong container (Docker Desktop không phản hồi giữa chừng).

### WM1 – tỷ lệ tin đăng lặp trên dữ liệu hiện có

Chạy hệ MinHash cắt khung (hệ đã chấm, không chỉnh gì) trên toàn bộ 888 tin: TopCV `topcv_20261118` (352) +
ITviec `itviec_20261113` (536).

- 17 nhóm trùng (34 tin), tức **17 tin thừa = 1,9%** số tin. Trong đó 5 nhóm là trùng **giữa hai trang**,
  12 nhóm trùng trong cùng một trang (TopCV 3, ITviec 9).
- Trên 300 cặp gán tay, precision của hệ là 5/5 với cặp khác trang và 0,385 với cặp cùng trang, recall 0,769.
  Hiệu chỉnh thô theo các số đó: số tin trùng thật khoảng **1–2,5%** số tin. Ước lượng thô vì tập cặp gán tay
  chỉ có 13 cặp trùng.
- Trùng giữa hai trang ít vì hai nguồn ít chung công ty và chung thời gian, không hẳn vì nhà tuyển dụng ít đăng
  lại. Muốn trả lời chắc RQ2 cần crawl nhắm vào các công ty có mặt trên cả hai trang, nhưng ngân sách crawl
  TopCV hiện chỉ ~50–60 request/ngày (mục sự cố 2026-11-18).

### WM3 – lô câu gán thêm

Toàn bộ câu review còn chưa gán và không thuộc review của TEST: **247 câu** (vi 186, en 61; phần "thích" 179,
"cần cải thiện" 47, tiêu đề 21) → lô `absa_dev3` để gán theo guideline WM3 hiện hành. Đây là tối đa có thể
có mà không crawl thêm review. Gán xong thì dev tăng từ 200 lên ~450 câu; chạy lại CV các mô hình đã thử
(TF-IDF, PhoBERT đóng băng, PhoBERT fine-tune, mô hình lai) trước khi chấm TEST lần mới.

Lệnh: `uv run python -m annotation.sample_absa_batch --all --batch absa_dev3 --exclude-reviews-of data/annotation/absa_test1.absa.jsonl --exclude-texts-of <absa_trial + absa_dev2>`

### WM5 – bộ chấm tay gợi ý việc làm

Thêm `recsys/judge_kit.py`: 30 hồ sơ kỹ năng × 4 phương pháp (độ phổ biến, trùng kỹ năng, TF-IDF, lai), gộp
top-10, xáo thứ tự, người chấm không biết phương pháp; nDCG@10 với điểm 0/1/2, so ghép cặp theo hồ sơ. Hồ sơ
nháp ở `data/eval/wm5_profiles_draft.csv` cần nhóm duyệt **trước** khi tạo phiếu. Chạy thử: ~790 dòng cần chấm
(~26 tin/hồ sơ). Chưa có kết quả.

### mining-service – chế độ PhoBERT

Đặt `JOBLENS_MINING_SKILL_MODEL` thì `/v1/skills:extract` dùng PhoBERT (cùng model với image) thay cho từ
điển; hợp đồng không đổi, `model_version` = `skill-extractor:<tag>`. Test hợp đồng có thêm hai ca cho chế độ
này (dùng model giả). Độ trễ đo trên CPU (tắt GPU, 2 luồng torch), 100 văn bản mô tả + yêu cầu của tin TopCV
(trung bình 1.646 ký tự), không tính lần nạp model: **p50 0,07 giây, p95 0,21 giây, max 0,35 giây**; 18,6 kỹ
năng/văn bản. Đạt yêu cầu ADR 0002 (p95 ≤ 3 giây). Lệnh: `uv run python -m service.bench --n 100 --threads 2`.

### WM2 – gắn mã ESCO cho từ điển kỹ năng (dở dang)

Contract `silver.job_skills` ghi `skill_id` là URI ESCO nếu có, nhưng cột `esco_uri` của từ điển vẫn rỗng.
`ie/esco_map.py` tra API tìm kiếm công khai của ESCO bằng **tên kỹ năng** (không gửi văn bản tin), tự nhận khi
nhãn ESCO (bỏ chú thích trong ngoặc) trùng đúng tên hoặc alias, còn lại đưa ra file duyệt.

- 2026-11-20: tra được **86/200 kỹ năng** (159 request, 1,1 giây/request) thì ESCO trả **HTTP 403** → dừng,
  không thử lại trong ngày. Script đã sửa: 2 giây/request, tối đa 2 truy vấn/kỹ năng, gặp lỗi HTTP thì dừng, chạy
  lại chỉ tra phần thiếu (cache).
- Trong 86 kỹ năng: **tự nhận 10** (ASP.NET, Ajax, Ansible, C#, C++, CSS, DevOps, Illustrator, Java,
  JavaScript); **duyệt nhận 11** (AI, Adobe Creative Suite, Agile, Agile/Scrum, AutoCAD, Automation Testing,
  CRM, Cloud, ETL, Firewall, Java Core – agent đề xuất, **cần người kiểm**); 65 không có trong ESCO.
- Quy tắc duyệt: chỉ nhận khi cùng khái niệm. **Không** đưa công cụ cụ thể về nhóm rộng hơn (Excel ↛ "use
  spreadsheets software", Git ↛ "tools for software configuration management", After Effects ↛ "motion
  graphics"), vì như vậy nhiều kỹ năng khác nhau sẽ chung một `skill_id` và làm sai số đếm.
- Tính theo số lần xuất hiện trong 888 tin crawl: 86 kỹ năng đã tra chiếm 56% số lần xuất hiện; trong đó
  **44%** có mã ESCO. Hụt lớn nhất là các công cụ hạ tầng và đám mây mà ESCO (bản hiện hành) không có: API
  (680 lần), AWS (522), Azure (492), Docker (360), CI/CD (356), Git (252), GCP (232).
- Chưa ghi vào từ điển: đợi tra xong 200 kỹ năng. Khi ghi, `skill_id` của các kỹ năng có ESCO đổi từ
  `joblens:<slug>` sang URI ESCO (đúng contract) – cần build image mới và báo nhóm dùng `silver.job_skills`.

### Chạy lại các bài dùng đầu ra WM2 bằng mô hình nhãn LLM (image 0.2.0)

**WM6 – đồ thị kỹ năng.** Dựng lại bằng PhoBERT nhãn LLM (867 tin; 799 tin có kỹ năng, 7,1 kỹ năng/tin; 150
đỉnh, 2.590 cạnh). NPMI ≥ 0,3 → 145 đỉnh/558 cạnh; Louvain **8 cụm, Q 0,517**; đồ thị ngẫu nhiên giữ bậc
0,305 ± 0,008, **z 27,2**, 0/100 lần ngẫu nhiên bằng hoặc hơn; ổn định theo seed NMI 0,86–1,00. So phân hoạch:
với đồ thị từ điển NMI 0,727 / ARI 0,621 (143 đỉnh chung); với đồ thị PhoBERT self-training cũ NMI 0,810 / ARI
0,716, top-20 kỹ năng theo số tin trùng 20/20. Kết luận WM6 giữ nguyên. Đồ thị gần như không đổi vì nó chỉ
tính kỹ năng có trong từ điển 200 kỹ năng: span mới mà mô hình bắt thêm phần lớn nằm ngoài từ điển và bị bỏ
khi quy về tên chuẩn. Đồ thị cũ lưu ở `data/graph/skill_graph_phobert_selftrain.json`.

**Bảng nhu cầu kỹ năng.** Chạy lại với `--extractor phobert` (mô hình nhãn LLM). Độ phủ tin có ít nhất một
kỹ năng: TopCV 90%, ITviec 94%, VietJobs IT 77% (từ điển: 93% / 97% / 83% – từ điển còn dùng tag nhà tuyển
dụng). Thiên lệch nguồn vẫn là kết quả chính: AI 24,2% (TopCV) / 42,2% (ITviec) / 12,5% (VietJobs IT);
Photoshop đứng đầu VietJobs IT (14,9%). Lệnh: `uv run python -m experiments.skill_demand --extractor phobert
--top 10 --min-jobs 15 --out data/eval/skill_demand_phobert.json`.

**WM5 – gợi ý trên log synthetic, dùng kỹ năng WM2 thay tag.** Trích kỹ năng 304 tin `topcv_20261012` bằng
image bản full (21,7 kỹ năng/tin sau khi quy về tên chuẩn), đưa vào `recsys.baseline --skills`.

| Chiến lược | tag nhà tuyển dụng (số chính thức) | kỹ năng WM2 |
|---|---|---|
| popularity | 0,027 / 0,015 | 0,027 / 0,015 |
| content-skill | 0,069 / 0,058 | **0,090 / 0,070** |
| content-tfidf | 0,102 / 0,071 | 0,102 / 0,071 |
| hybrid | 0,097 / 0,072 | 0,097 / 0,072 |

(Recall@10 / nDCG@10.) Trùng kỹ năng tốt hơn khi dùng kỹ năng WM2, đuổi kịp TF-IDF; chưa có khoảng tin cậy và
vẫn là log synthetic (người dùng ảo sinh từ tag), nên chỉ là số phụ. Số WM5 chính thức không đổi.

## Việc ngày 2026-11-21

### WM5 – trùng kỹ năng so qua từ điển alias

- **Lỗi:** `content-skill` so kỹ năng theo đúng mặt chữ (chỉ hạ chữ thường). Hồ sơ ghi "React" không khớp tin ghi
  "ReactJS"/"React.js"; trong 304 tin `topcv_20261012`, WM2 trả "reactjs" ở 18 tin, "nextjs" ở 7 tin. Với hồ sơ
  người viết, phương pháp này bị đánh giá thấp oan.
- **Sửa:** cả kỹ năng hồ sơ lẫn kỹ năng tin được đưa về tên chuẩn qua từ điển alias (cùng danh mục với
  mining-service) trước khi so; tên không có trong từ điển giữ chữ thường. Sửa trước khi tạo phiếu chấm tay, chưa
  có điểm chấm nào.
- **Log synthetic, chạy lại:** `content-skill` nDCG@10 0,058 → **0,057** (Recall@10 0,069 giữ nguyên); dùng kỹ
  năng WM2: 0,070 → 0,068. Gần như không đổi vì người dùng ảo sinh từ chính tag của tin, nên vốn không lệch tên.
  Các chiến lược khác không đổi. Lệnh: `uv run python -m recsys.baseline --eval-set reco_synthetic`.

### WM5 – chọn hồ sơ chấm tay

- Từ 30 hồ sơ nháp giữ **20**, bỏ 10 hồ sơ snapshot gần như không có tin phù hợp hoặc trùng nhóm: an ninh ứng dụng
  (0–3 tin có kỹ năng trùng), game designer, Flutter, blockchain, helpdesk, iOS, SAP/ERP ("Tư vấn triển khai"
  không phải kỹ năng), kiểm thử hiệu năng (đã có hai hồ sơ tester), game Unity, quản trị mạng.
- Chọn **trước khi xem gợi ý**, chỉ dựa trên số tin có ít nhất một kỹ năng trùng (không dựa trên thứ hạng).
- Ước khối lượng chấm: 20 hồ sơ × 4 phương pháp × top-10, gộp tin trùng: **~500 dòng** (kỹ năng tin từ WM2).
- **Đã tạo phiếu chấm (2026-11-21):** 20 hồ sơ (sha256 `8be17e871c62fbb0…`), kỹ năng tin lấy từ WM2, snapshot
  `topcv_20261012`, seed 20261120 → **503 dòng**, phiếu dạng Excel (.xlsx; bản CSV đầu bị Excel hiểu mô tả bắt đầu bằng "-" là công thức, cùng nội dung và thứ tự). Từ đây không sửa hồ sơ. Lệnh:
  `uv run python -m recsys.judge_kit make --profiles data/eval/wm5_profiles.csv --skills data/eval/wm5_skills_wm2.jsonl`.

### WM5 – kết quả chấm tay (2026-11-22)

- 20 hồ sơ, 503 cặp (hồ sơ, tin) chấm mù, 1 người chấm (Hoang Le), chưa đo κ. Điểm: 0 = 266, 1 = 42, 2 = 195.
  Kiểm phiếu: đủ mọi cặp trong khóa, không thiếu, không thừa. Kỹ năng tin lấy từ WM2, snapshot `topcv_20261012`.
- nDCG@10 gain 2^g − 1; tin tốt nhất "lý tưởng" lấy trong các tin đã chấm của hồ sơ đó (gộp 4 phương pháp).
  P@10 = tỷ lệ tin trong top-10 có điểm ≥ 1. Bootstrap ghép cặp theo hồ sơ, 1.000 lần.

| Phương pháp | nDCG@10 | P@10 | Δ nDCG so với độ phổ biến [CI95] |
|---|---|---|---|
| `popularity` (baseline) | 0,061 | 0,065 | – |
| `content-skill` | 0,775 | 0,740 | +0,714 [+0,615; +0,799] |
| **`content-tfidf`** | **0,837** | **0,810** | +0,776 [+0,665; +0,862] |
| `hybrid` | 0,812 | 0,780 | +0,752 [+0,659; +0,821] |

- So với `content-tfidf`: `content-skill` −0,062 [−0,172; +0,047], `hybrid` −0,025 [−0,065; +0,017] → **không
  phân biệt được** ba phương pháp content-based; cả ba hơn baseline rõ.
- Theo hồ sơ: `content-skill` thua rõ ở Data analyst (0,37 so với 0,85), Project Manager (0,39 so với 0,77),
  Fullstack Java/Angular (0,53 so với 0,96); thắng ở Lập trình nhúng (0,92 so với 0,50), Thu thập dữ liệu web
  (0,75 so với 0,33), AI thị giác máy tính (0,97 so với 0,73). Hai cách bổ sung nhau, chưa phân tích nguyên nhân.
- **Hạn chế:** nDCG tính trên tập tin đã chấm (pooling), nên tin tốt nằm ngoài top-10 của cả 4 phương pháp không
  được tính → số nghiêng cao. Một người chấm, chưa có κ. Hồ sơ do nhóm soạn, 304 tin của một snapshot.
- Kết luận khớp hướng với log synthetic (content-based ≫ độ phổ biến; ghép độ phổ biến không giúp), nhưng đây là
  số đầu tiên có người đánh giá. **Số WM5 chính thức chuyển sang bảng này**; log synthetic giữ làm kiểm tra cài đặt.
- Lệnh: `uv run python -m recsys.judge_kit score` (thêm `--baseline content-tfidf` để so với TF-IDF).
- **κ (chuẩn bị, 2026-11-22):** phiếu người chấm thứ hai 50 dòng rút ngẫu nhiên từ 503 dòng (seed 20261122; điểm
  người 1 trong mẫu: 0 = 20, 1 = 7, 2 = 23; đủ 20 hồ sơ), không kèm điểm người 1. Chưa có kết quả.
  Lệnh: `uv run python -m recsys.judge_kit kappa-make --n 50` → chấm → `uv run python -m recsys.judge_kit kappa`.
- **κ (kết quả, 2026-11-22):** người chấm thứ hai chấm độc lập 50 dòng. Trùng điểm 42/50 (84%).
  κ 3 mức **0,732** [0,58; 0,89]; κ trọng số tuyến tính **0,837** [0,72; 0,94]; κ hợp/không (điểm ≥ 1) **0,833**
  [0,64; 0,96] (bootstrap 2.000 lần theo dòng). Không có cặp lệch 0 ↔ 2; 8 dòng lệch đều nằm quanh mức 1
  (người 1 → người 2: 0→1 ×2, 1→0 ×2, 1→2 ×3, 2→1 ×1). Đạt mục tiêu κ ≥ 0,7; nhãn chính thức vẫn là của người 1.
