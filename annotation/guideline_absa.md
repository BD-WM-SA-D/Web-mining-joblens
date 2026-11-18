# Guideline gán nhãn ABSA review công ty (bản 0.2.3 – đã gán 60 câu thử + 356 câu TEST + 200 câu dev)

Gán cho WM3: mỗi **câu** trong review công ty được gán các cặp **(khía cạnh, cực cảm xúc)**.
Một câu có thể có nhiều khía cạnh, mỗi khía cạnh một cực riêng. Câu không nói về khía cạnh nào → không gán gì.

Tập đánh giá: 356 câu TEST + 200 câu dev từ review ITviec. Người thứ hai gán lại 35 câu TEST
(10%) để đo Cohen's κ: **κ = 0,871** trên ô câu × khía cạnh, đạt mục tiêu ≥ 0,7.
Nhãn yếu (điểm sao theo khía cạnh của chính review) **không bao giờ** dùng làm tập test.

## 1. Khía cạnh (6 nhãn)

Mã khía cạnh lấy đúng theo contract `silver.review_aspects` (repo joblens): 5 mục chấm sao của ITviec + cân bằng công việc.

| Mã (ghi vào dữ liệu) | Tên | Nói về |
|---|---|---|
| `salary_benefits` | Lương & phúc lợi | lương, thưởng, review lương, bảo hiểm, phụ cấp, ESOP, ăn trưa, hỗ trợ gym/sức khỏe (sự kiện du lịch, team building: xem mục 2c) |
| `training_learning` | Đào tạo & cơ hội học hỏi | onboarding, mentor, khóa học, công nghệ mới, cơ hội thăng tiến, được làm dự án hay |
| `management_care` | Quản lý | sếp, lead, PM, cách quản lý, lắng nghe nhân viên, minh bạch, chính trị nội bộ, quy trình quản lý |
| `culture_fun` | Văn hóa & môi trường | đồng nghiệp, không khí làm việc, team building, cách đối xử, drama, tuổi trung bình đội ngũ |
| `office_workspace` | Văn phòng & thiết bị | vị trí, chỗ ngồi, máy móc cấp phát, pantry, chỗ gửi xe, điều hòa |
| `work_life_balance` | Cân bằng công việc / OT | OT, deadline, áp lực, làm cuối tuần, remote/hybrid, giờ giấc linh hoạt, nghỉ phép dễ/khó |

Phân xử nhanh các ca giáp ranh:

- "OT có trả lương / OT không lương": nói về chế độ **trả tiền** cho OT → `salary_benefits`; nói về **tần suất phải OT** → `work_life_balance`. Câu nói cả hai ("OT nhiều mà không được trả") → gán cả hai.
- "Sếp giỏi, học được nhiều từ sếp" → cả `management_care` (khen sếp) và `training_learning` (học được nhiều).
- Thăng tiến, lộ trình career → `training_learning`. Tăng lương chậm → `salary_benefits`.
- Đồng nghiệp giỏi giúp mình tiến bộ → `culture_fun` + `training_learning`; "đồng nghiệp vui vẻ" → chỉ `culture_fun`.
- Quy trình làm việc lộn xộn, giao việc không rõ → `management_care`.
- Máy yếu, không cấp màn hình → `office_workspace` (không phải phúc lợi).
- Khen/chê **chung chung không thuộc khía cạnh nào** ("công ty tốt", "không recommend") → **không gán** (ghi nhận là hạn chế của phạm vi 6 khía cạnh; không thêm nhãn `general`).
- Nói về **sản phẩm/kinh doanh** của công ty ("app nhiều người dùng", "công ty đang lỗ") → không gán, trừ khi gắn với trải nghiệm nhân viên ("công ty lỗ nên cắt thưởng" → `salary_benefits`).

## 2. Cực cảm xúc (3 giá trị cho từng khía cạnh)

| Cực | Khi nào | Ví dụ |
|---|---|---|
| `positive` | khen, hài lòng | "Lương review đều mỗi năm." |
| `negative` | chê, than phiền, cảnh báo | "Sếp micro-manage kinh khủng." |
| `neutral` | có nhắc khía cạnh nhưng không rõ khen chê: mô tả sự kiện, trung lập, nửa nọ nửa kia không tách được | "Lương trả vào ngày 5 hằng tháng." |

> **Để trống ≠ `neutral`.** Đây là chỗ sai nhiều nhất.
>
> | Chọn gì | Nghĩa |
> |---|---|
> | **để trống** | câu **không nói gì** về khía cạnh này |
> | `neutral` | câu **có nói** tới, nhưng không khen không chê |
>
> Câu "Lương thấp hơn thị trường" chỉ gán `salary_benefits` = `negative`, **năm khía cạnh còn lại để trống**.
> Gán `neutral` cho chúng là nói "câu này có bàn về đào tạo, văn phòng, OT…" – sai, và mô hình sẽ học
> rằng câu nào cũng nhắc đủ 6 khía cạnh.
>
> Một câu thường chỉ nhắc 1–2 khía cạnh. Nếu bạn đang gán 4 khía cạnh trở lên cho một câu, đọc lại câu đó.

Quy ước:

1. **Gán theo ý người viết trong ngữ cảnh**, kể cả mỉa mai: "Lương cao lắm, cao đến mức 3 năm không đổi :)" → `salary_benefits` = `negative`.
2. **Lời khuyên cho công ty ngầm chứa chê**: "Mong công ty xem lại chế độ OT" → `work_life_balance` = `negative`.
3. Câu có **cả khen và chê về cùng một khía cạnh** ("lương cứng thấp nhưng thưởng cao"): nếu nghiêng rõ về một phía thì gán phía đó; cân bằng thật sự → `neutral`.
4. **So sánh thời kỳ** ("hồi trước OT nhiều, giờ đỡ rồi"): gán theo hiện tại người viết mô tả (`work_life_balance` = `positive`).
5. Phủ định phải đọc kỹ: "không phải OT bao giờ" → `positive`; "không được đào tạo gì" → `negative`.
6. "Bình thường", "tạm ổn", "ổn" cho một khía cạnh → `neutral` nếu chỉ có vậy; "khá ổn", "ổn áp" → `positive`.
7. Câu tiếng Anh gán như thường.
8. **Chê nhẹ vẫn là `negative`.** "Nhà xe hơi chật", "văn phòng hơi cũ", "lương hơi thấp" → `negative`.
   `neutral` chỉ dành cho câu nêu **sự việc kiểm chứng được, không kèm đánh giá nào**: "Lương trả ngày 5
   hằng tháng", "Văn phòng ở quận 1". Thấy từ chỉ mức độ ("hơi", "khá", "quá", "chưa") kèm tính từ xấu
   thì đó là chê.
9. **Lời đề nghị lịch sự vẫn là `negative`** (nói rõ thêm luật 2). "Rất mong công ty tăng lương",
   "Công ty nên mua thêm máy", "Cần chú ý thêm chế độ OT" → `negative`. Người ta chỉ đề nghị sửa thứ
   đang không ổn; dấu "!!" hay "mong" không làm câu thành trung lập.
10. **Gán theo điều người viết muốn nói, đừng nghĩ "chỗ nào chẳng thế".** Câu "OT được tính theo quy
   định" không phải `neutral` chỉ vì luật đã bắt trả tiền OT. Ba lý do:
   - Bài này đo người viết **nghĩ gì về công ty của họ**, không phải so công ty đó với thị trường.
   - Mô hình **chỉ đọc được câu**. Nhãn dựa vào thứ không nằm trong câu (lương thị trường, luật lao
     động) thì mô hình không học được, mà hai người gán cũng khó khớp nhau.
   - Dữ liệu của mình có 12 câu chê "OT không lương". Vậy trả tiền OT **không** phải chuyện đương
     nhiên. Người viết nhắc nó ra là đang khen.

   **Chốt 2026-11-15:** công ty làm đúng nghĩa vụ mà người viết nhắc ra thì gán `positive`. Áp cho cả
   ba kiểu câu: "trả lương đúng hạn", "đóng bảo hiểm full lương", "OT tính theo quy định".

## 2b. Quy trình gán một câu (làm theo đúng thứ tự)

Gán theo cảm tính thì κ thấp và không giải thích được cho giảng viên. Mỗi câu đi qua 4 bước:

| Bước | Câu hỏi | Nếu KHÔNG |
|---|---|---|
| 1 | Câu có nói gì về **trải nghiệm làm việc** không? | để trống cả 6, Submit |
| 2 | Thuộc khía cạnh nào? **Tra bảng mục 1**, không đoán | khen chê chung chung ("công ty tốt") → để trống cả 6 |
| 3 | Có **đánh giá** không, hay chỉ mô tả sự việc? | chỉ mô tả → `neutral` |
| 4 | Khen hay chê? **Lời khuyên = chê** (luật 2) | – |

Bước 2 cho ra *một hoặc vài* khía cạnh; bước 3–4 làm riêng cho **từng** khía cạnh đó
("Lương ổn nhưng OT nhiều" → `salary_benefits` = `positive`, `work_life_balance` = `negative`).

Ví dụ chạy đủ 4 bước – *"Công việc cần có quy trình hơn."*

1. Có nói về trải nghiệm làm việc → đi tiếp.
2. "quy trình" → `management_care` (mục 1, dòng phân xử "quy trình làm việc lộn xộn").
3. "cần ... hơn" là đánh giá, không phải mô tả → đi tiếp.
4. Lời khuyên cho công ty → `negative`.

Kết quả: `management_care` = `negative`, 5 khía cạnh còn lại **để trống**.

Câu này không chứa từ chê nào nên baseline từ điển sẽ trả `neutral`. Đó là loại lỗi phải nêu trong phần
phân tích lỗi của báo cáo, nên gán cho đúng chứ đừng gán theo cách baseline nghĩ.

## 2c. Bảng tra thuật ngữ hay gặp (chốt sau lô thử 60 câu, 2026-11-15)

Lô thử có 11/57 câu phải tick "khó / cần bàn", và phần lớn rơi vào cùng mấy thuật ngữ. Bảng này chốt
sẵn để lần sau không phải nghĩ lại – **tra bảng trước khi tự quyết**.

| Thấy trong câu | Khía cạnh | Ghi chú |
|---|---|---|
| career path, career development, lộ trình, thăng tiến, cơ hội phát triển | `training_learning` | kể cả khi câu không nhắc tới học hay khóa học |
| performance review, đánh giá hiệu suất, tiêu chí đánh giá, KPI không rõ | `management_care` | là chuyện minh bạch của quản lý. Nếu câu nối sang lương ("review không rõ nên không được tăng") thì gán **thêm** `salary_benefits` |
| company trip, du lịch công ty, team building, year-end party, tiệc | `culture_fun` | gán `salary_benefits` **chỉ khi** câu nói về tiền hay quyền lợi bị cắt ("hợp đồng ghi có du lịch mà không có") |
| máy pha cafe, pantry, nhà xe, bàn ghế, thang máy, điều hòa, chỗ ngủ trưa | `office_workspace` | tiện nghi **tại văn phòng**, không phải phúc lợi |
| laptop, màn hình, MacBook/MacOS, thiết bị, cơ sở vật chất, CSVC | `office_workspace` | đã có ở mục 1, nhắc lại vì hay gán thành `salary_benefits` |
| hỗ trợ gym, hỗ trợ sức khỏe, bảo hiểm, phụ cấp, ăn trưa | `salary_benefits` | tiền hoặc quyền lợi mang ra khỏi công ty được |
| flexible / flexiable, hybrid, work from home, giờ giấc, cày cuốc, sấp mặt | `work_life_balance` | |
| talkshow, buổi chia sẻ, mentor, được làm dự án mới, mở rộng domain | `training_learning` | |
| lắng nghe nhân viên, quy trình làm việc, giao việc, minh bạch | `management_care` | |
| khen hoặc chê **năng lực của sếp, lead, PM** ("leader kiến thức giỏi") | `management_care` | thêm `training_learning` nếu câu nói mình học được từ người đó; đây là chuyện người quản lý, không phải không khí đồng nghiệp |
| CLB, hội nhóm trong công ty, uống bia, ăn uống cùng nhau | `culture_fun` | hoạt động chung của nhân viên, cùng nhóm với team building |

(Hai dòng cuối chốt sau khi đo κ ngày 2026-11-17 – xem mục lịch sử.)

**Câu liệt kê nhiều thứ phải tra từng thứ.** "Premium health insurance, free daily lunch and snacks,
learning support (courses…)" có ba món, hai khía cạnh: `salary_benefits` **và** `training_learning`.
Lệch nhiều nhất giữa hai người gán là kiểu này: đọc thấy khía cạnh đầu rồi dừng. Gặp dấu phẩy hoặc
chữ "và" nối các danh từ thì soát lại bảng mục 1 một lượt nữa.

**"môi trường làm việc" / "environment"** (sửa 2026-11-17, xem bên dưới):

| Câu | Gán | Vì sao |
|---|---|---|
| "Môi trường làm việc chuyên nghiệp", "môi trường tốt", "môi trường thân thiện", "good environment" | `culture_fun` | khía cạnh này tên là "Văn hóa & **môi trường**", nên nói môi trường thế nào là nói về nó |
| "môi trường học hỏi", "môi trường rèn luyện", "good learning environment", "môi trường phát triển" | `training_learning` | bổ ngữ chỉ sang chuyện học, không phải chuyện văn hóa |
| "Môi trường product", "Môi trường đa số là các bạn trẻ" | không gán | chỉ kể sự việc, không đánh giá |
| "Môi trường **tốt** để rèn luyện", "**Good** environment to growth" | `culture_fun` **và** `training_learning` | tính từ đánh giá chung ("tốt", "good") là một ý, mệnh đề chỉ mục đích ("để rèn luyện") là ý thứ hai |

Cách phân xử nhanh: tính từ đi ngay với "môi trường" mà nói về chuyện học ("learning", "học hỏi")
thì **chỉ** `training_learning`. Tính từ đánh giá chung ("tốt", "good", "chuyên nghiệp") thì `culture_fun`,
cộng thêm khía cạnh mà phần còn lại của câu nói tới.

Bản 0.2 ghi "môi trường chuyên nghiệp → vẫn không gán (quá chung)" nhưng ví dụ ở mục 5 của chính nó
lại gán `culture_fun` cho đúng câu kiểu đó. Lúc gán 300 câu TEST, 29/35 câu có chữ "môi trường" được
gán `culture_fun`; 6 câu còn lại đều là "môi trường + bổ ngữ về học hỏi" nên vào `training_learning`.
Tức là cách gán đã nhất quán, chỉ có câu luật kia là sai. Bỏ câu luật đó.

> **TEST không sửa theo hai dòng mới này.** 356 câu TEST được gán theo bản 0.2.2 và đã đóng băng,
> đã có mô hình chấm trên đó, nên sửa nhãn test lúc này là sai nguyên tắc. Hệ quả: trong TEST còn
> khoảng 2–3 câu gán khác bản 0.2.3 (một câu khen kiến thức của leader gán `culture_fun`, một câu về
> uống bia gán `management_care`). Số lượng nhỏ nhưng phải ghi trong phần hạn chế của báo cáo.

## 2d. Khi nào được điền `neutral`

`neutral` **không phải** ô "tôi chưa chắc". Chưa chắc thì tick "khó / cần bàn" rồi đi tiếp. Điền
`neutral` cho câu mình chưa đọc ra thì mô hình học sai mà không ai biết; tick "khó" thì câu đó còn được
bàn lại.

### Phép thử đổi chiều

Đổi sự việc trong câu sang chiều ngược lại, rồi đọc câu mới xem nghe ra sao.

| Câu gốc | Đổi chiều thành | Câu mới nghe ra | Vậy câu gốc là |
|---|---|---|---|
| Rất ít phải OT | Phải OT rất nhiều | tiếng chê | `positive` |
| OT được tính theo quy định | OT không được tính lương | tiếng chê (có 12 câu như vậy thật) | `positive` |
| Trả lương đúng hạn | Lương trả trễ | tiếng chê | `positive` |
| **Lương trả ngày 5 hằng tháng** | Lương trả ngày 20 | vẫn chỉ là một sự việc khác | **`neutral`** |
| **Văn phòng ở quận 1** | Văn phòng ở quận 12 | vẫn chỉ là một sự việc khác | **`neutral`** |
| **Team mình 8 người** | Team mình 20 người | vẫn chỉ là một sự việc khác | **`neutral`** |

Đổi sang **chiều ngược bình thường**, đừng đổi thành thảm họa. Ngược của "trả lương ngày 5" là "trả
ngày 20", không phải "nợ lương 3 tháng".

### Ba câu hỏi, phải "có" cả ba mới được `neutral`

1. Đổi chiều xong **vẫn chỉ là một sự việc khác** (không thành khen, không thành chê)?
2. Câu **không có** từ khen chê ("tốt", "chật", "ổn") **và không có** từ chỉ mức độ ("rất ít", "hơi",
   "quá", "chỉ", "tương đối", "may mắn")? Có từ chỉ mức độ nghĩa là người viết đang đánh giá, không
   phải chỉ kể.
3. Câu **không phải** lời đề nghị?

Một câu trả lời "không" là câu đó không phải `neutral`. Vẫn do dự thì tick "khó / cần bàn", và chỉ khi
buộc phải chọn mới dựa vào ô review – ô review là gợi ý yếu, `liked` vẫn có nhiều câu chê (mục 3).

### Vì sao `neutral` ít

Người ta viết review để nói cái hay cái dở, không để kể sự việc. Lô thử 60 câu, soi lại theo ba câu hỏi
trên thì chỉ còn 1–2 câu `neutral`. Dữ liệu nó vậy, không phải gán sai.

## 3. Đơn vị gán và ngữ cảnh

- Gán **mức câu** (câu đã tách sẵn khi tạo task). Không gán mức cụm từ.
- Được nhìn **câu trước/câu sau** (hiện mờ trong task) để hiểu câu đang gán; nhưng nhãn chỉ mô tả nội dung **câu đang gán**. Câu "Nhưng bù lại rất vui." đứng sau câu chê lương → chỉ gán `culture_fun` = `positive`, không gán lương.
- Đại từ thay thế ("ở đó", "chỗ này", "họ") vẫn tính: "Họ hứa tăng lương rồi quên" → `salary_benefits` = `negative`, `management_care` = `negative`.
- Câu chỉ có emoji/cụm cực ngắn ("OT :(( ") → vẫn gán được (`work_life_balance` = `negative`).
- Còn sót tên người thật trong câu → tick cờ `PII` để lọc lại, vẫn gán bình thường.
- Câu khó/mơ hồ → tick cờ `khó / cần bàn`, các câu này sẽ bàn khi chốt guideline 0.2.

### Câu đến từ phần nào của review (đọc kỹ, dễ gán sai)

Mỗi review ITviec có hai phần: **"Điều tôi thích"** và **"Đề nghị cải thiện"**. Task hiện phần nguồn của câu.

**Gán theo nội dung câu, KHÔNG theo phần nó nằm.** Phần nguồn chỉ là gợi ý, không phải nhãn.
Dữ liệu thật (108 review crawl 2026-11-12) có đủ hai kiểu ngược:

| Câu | Nằm ở phần | Nhãn đúng |
|---|---|---|
| "Lương tăng khá chán, có cảm giác như tăng auto chứ không có sếp review lương." | Đề nghị cải thiện | `salary_benefits`=neg |
| "Hiện tại tôi không thấy quá nhiều vấn đề để có thể yêu cầu cải thiện" | Đề nghị cải thiện | (không gán – không nói về khía cạnh nào) |
| "Không có gì cần cải thiện cả. Phúc lợi khá tốt." | Đề nghị cải thiện | `salary_benefits`=**pos** |
| "phúc lợi ổn, môi trường làm việc chuyên nghiệp, văn phòng ở trung tâm" | Đề nghị cải thiện | `salary_benefits`=pos; `culture_fun`=pos; `office_workspace`=pos |
| "Lương hơi thấp so với thị trường." | Điều tôi thích | `salary_benefits`=**neg** |

Câu trong "Đề nghị cải thiện" thường viết dưới dạng **đề xuất** chứ không chê thẳng – vẫn gán `negative` (quy ước 2 ở mục 2):
"Salary and bonuses should be adjusted to keep competitive" → `salary_benefits`=neg.

## 4. Ví dụ gán đủ

| Câu | Nhãn |
|---|---|
| "Lương ổn nhưng sếp hay la mắng trước mặt team." | `salary_benefits`=pos; `management_care`=neg |
| "OT triền miên, được cái trả OT đầy đủ." | `work_life_balance`=neg; `salary_benefits`=pos |
| "Văn phòng ở quận 1, có chỗ gửi xe." | `office_workspace`=neu (mô tả, không khen chê rõ) |
| "Văn phòng đẹp, view sông." | `office_workspace`=pos |
| "Mình làm ở đây 2 năm." | (không gán) |
| "Công ty không dành cho người muốn phát triển." | `training_learning`=neg |
| "Should improve the review salary process." | `salary_benefits`=neg |
| "Đồng nghiệp ok, sếp ok, lương hơi bèo." | `culture_fun`=pos; `management_care`=pos; `salary_benefits`=neg |

## 5. Quy trình

1. Mỗi task Label Studio = 1 câu + ngữ cảnh mờ + tên công ty đã ẩn danh (`cty_<id>`).
2. Chọn các cặp (khía cạnh, cực) bằng checkbox (18 lựa chọn + cờ). Không chọn gì = câu không có khía cạnh.
3. Gán thử 50 câu → bàn các câu lệch/khó → chốt guideline 0.2 → gán chính thức ~1.000 câu.
4. Người thứ hai gán ~100 câu trên project riêng (không thấy nhãn người thứ nhất, task giữ `src_task`), đo κ:
   - κ tính trên từng khía cạnh (nhãn 4 lớp: pos/neg/neu/không nhắc) rồi báo trung bình và từng khía cạnh.
5. Export → `data/annotation/absa_batch1.jsonl`; thống kê ghi `experiments/results.md`.

## 6. Những điều chưa chốt (chờ Hoang Le duyệt)

- [ ] Có thêm nhãn `general` cho khen/chê chung chung không? (bản nháp: **không**)
- [ ] `neutral` có giữ không hay gộp vào "không nhắc"? (bản nháp: **giữ**, vì đề tài đăng ký ghi positive/negative/neutral)
- [ ] Review tiếng Anh chiếm bao nhiêu % – nếu quá nhiều có lọc bớt không?
- [ ] Ngưỡng tách câu: câu ghép dài có bị tách đôi làm mất vế không – xem sau khi crawl thử.

## 7. Hạn chế của dữ liệu (phải ghi vào báo cáo)

Đo trên 912 review của 200 công ty, crawl 2026-11-12 (chi tiết: `experiments/results.md`):

- ITviec chỉ cho khách chưa đăng nhập xem **1 review mỗi công ty**, và **chọn review tích cực**:
  0/104 review công khai ghi "Không khuyến khích", trong khi 147/808 review bị che (18%) có ghi.
  Không review công khai nào dưới 3 sao, trong khi review bị che có 14 cái 1 sao và 40 cái 2 sao.
- Review công khai cao hơn review bị che **+0,27 sao** (so trong cùng công ty, n=104).
- Hệ quả khi gán nhãn: **thiếu câu phê phán nặng**. Nguồn câu `negative` chủ yếu là phần
  "Đề nghị cải thiện" của các review 4–5 sao, nên thường là góp ý nhẹ chứ không phải bức xúc.
- Khi báo macro-F1 phải kèm **số lượng từng lớp**; lớp `negative` ít mẫu thì nói rõ là kém tin cậy.

## Lịch sử

| Bản | Ngày | Thay đổi |
|---|---|---|
| 0.1 | 2026-11-12 | Nháp đầu, chờ duyệt và gán thử 50 câu |
| 0.1.1 | 2026-11-13 | Thêm mục "câu đến từ phần nào" và mục 7 hạn chế, sau khi crawl 200 công ty |
| 0.1.2 | 2026-11-15 | Nói rõ **để trống ≠ `neutral`** (câu hỏi lúc gán lô thử); sửa cấu hình Label Studio bị trắng trên trắng ở chế độ Dark |
| 0.1.3 | 2026-11-15 | Thêm mục 2b: quy trình 4 bước gán một câu, kèm ví dụ chạy đủ các bước |
| 0.2 | 2026-11-15 | Sau lô thử 60 câu: mục 2c bảng tra thuật ngữ, luật 8–9 siết `neutral`, gỡ nhập nhằng "du lịch công ty" |
| 0.2.1 | 2026-11-15 | Thêm luật 10 (gán theo điều người viết muốn nói) và mục 2d: phép thử đổi chiều + ba câu hỏi cho `neutral` |
| 0.2.2 | 2026-11-17 | Bỏ câu luật tự mâu thuẫn về "môi trường" ở mục 2c; chốt "môi trường + từ đánh giá chung" → `culture_fun` |
| 0.2.3 | 2026-11-17 | Sau khi đo κ (0,871 trên 35 câu): mục 2c thêm "năng lực của sếp/lead" → `management_care`, "CLB, uống bia" → `culture_fun`, và luật "câu liệt kê nhiều thứ phải tra từng thứ" (chỗ hai người lệch nhiều nhất) |
