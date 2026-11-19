# Luồng xử lý WM2 – trích kỹ năng từ tin tuyển dụng

*Cập nhật 19/11/2026, ứng với image `skill-extractor` 0.2.0. Số liệu lấy từ `experiments/results.md`; chỗ chưa đo để `<...>`.*

Tài liệu này mô tả WM2 từ đầu đến cuối: dữ liệu vào, cách làm nhãn, train, chấm điểm, đóng image, rồi chạy trong
hệ thống chung. Phần hạ tầng (Kafka, Iceberg, Airflow, K8s) thuộc môn Big Data, chỉ được nhắc để chỉ rõ chỗ nối.

## 1. Vị trí trong hệ thống

```
 Web Mining (repo này)                         Big Data                                   PTTKHT
 ┌──────────────┐  jobs.raw.topcv.v1   ┌──────────────────────────────────────┐  Trino  ┌──────────┐
 │ crawler      │ ───────────────────► │ bronze → silver.job_postings         │ ──────► │ app      │
 └──────────────┘       Kafka          │              │                       │         └──────────┘
                                       │              ▼  Airflow chạy image     │              │
 ┌──────────────┐  image có tag        │   ┌──────────────────────────┐        │              │ HTTP
 │ skill-       │ ───────────────────► │   │ skill-extractor 0.2.0    │        │              ▼
 │ extractor    │  x.y.z-gitsha        │   └──────────────────────────┘        │       ┌──────────────┐
 └──────────────┘                      │              ▼                        │       │ mining-      │
                                       │   silver.job_skills → gold (dbt)      │       │ service      │
                                       └──────────────────────────────────────┘       │ (bản stub)   │
                                                                                       └──────────────┘
```

- **Đường batch** (chính): Airflow của Big Data gọi image `skill-extractor` theo hợp đồng chạy ADR 0001 D3. Image
  đọc `silver.job_postings`, ghi `silver.job_skills` (contract trong repo `joblens`). Bảng này là đầu vào của
  gợi ý việc làm (WM5), đồ thị kỹ năng (WM6), bảng nhu cầu kỹ năng và các mart bên Big Data.
- **Đường trực tuyến**: `mining-service` (ADR 0002) trả kỹ năng cho văn bản người dùng dán vào app. Hiện vẫn là
  **bản stub dùng từ điển**, chưa dùng PhoBERT. Muốn đổi phải đo độ trễ trên CPU (yêu cầu p95 ≤ 3 giây): `<chưa đo>`.
- **LLM không có mặt trong hệ thống.** Nó chỉ dùng một lần lúc làm nhãn train, trên máy của người làm WM (mục 3.2).
  Pod không gọi API ngoài và không cần key.

## 2. Dữ liệu vào

| Nguồn | Dùng cho | Rời máy? |
|---|---|---|
| Tin TopCV tự crawl (snapshot `topcv_<ngày>`) | Tập test `skill_test1` (1.000 câu, 125 tin); một phần nhãn yếu train (tag "Kỹ năng cần có") | Không |
| Tin ITviec tự crawl | Chạy batch, đồ thị, nhu cầu kỹ năng; không dùng để train WM2 | Không |
| VietJobs, tập tin IT `vietjobs_it` (Pham Dinh et al., LREC 2026; CC BY 4.0 / MIT) | Phần lớn câu train; dev `skill_batch1` (300 câu); từ điển alias | **Có**: câu train gửi tới API LLM để gán nhãn |
| Từ điển `ie/resources/skill_alias.csv` (200 kỹ năng, alias Việt/Anh) | Baseline, nhãn yếu, chuẩn hóa `skill_id` | Không |

Tách tập theo **tin**: tin nào có câu trong dev hoặc test thì không có câu nào trong train.

## 3. Luồng xây dựng mô hình (offline, trên máy WM)

```
 Guideline gán nhãn kỹ năng 0.4 (annotation/guideline_skill.md)
        │                                   │
        ▼                                   ▼
 ┌─────────────────────┐          ┌────────────────────────────┐
 │ Tập vàng (gán tay)  │          │ Nhãn yếu cho train          │
 │ Label Studio cục bộ │          │ ① tag + từ điển             │
 │ dev  skill_batch1   │          │ ② + luật theo guideline     │
 │ test skill_test1    │          │ ③ + self-training           │
 │ κ trên ~10% câu     │          │ ④ câu VietJobs: LLM gán lại │
 └─────────┬───────────┘          │    theo guideline           │
           │                      └─────────────┬──────────────┘
           │                                    ▼
           │                      ┌────────────────────────────┐
           │  chọn epoch trên dev │ Fine-tune PhoBERT-base-v2   │
           ├────────────────────► │ token classification BIO    │
           │                      │ 3 seed                      │
           │                      └─────────────┬──────────────┘
           │   chấm TEST một lần                ▼
           └────────────────────► seqeval strict, bootstrap ghép cặp theo tin
                                                │
                                                ▼
                       models.yaml + image skill-extractor x.y.z-gitsha
```

### 3.1 Tập vàng (không bao giờ là nhãn yếu)

1. Rút câu: `annotation/sample_skill_batch.py` (tách câu theo dòng mô tả, giới hạn số câu mỗi tin, seed cố định).
2. Gán trong Label Studio chạy cục bộ (`annotation/make_ls_project.py`, `label_studio_skill.xml`). Dev có gợi ý từ
   điển; **test gán không có gợi ý** để không thiên về baseline.
3. Export sang BIO: `annotation/export_bio.py`. Đo κ: `annotation/kappa_skill.py`.
4. Test đóng băng bằng sha256 (ghi trong `models.yaml`); không sửa sau khi chấm.

### 3.2 Nhãn yếu cho train

| Bước | Code | Làm gì | Độ nhiễu so với nhãn tay (dev) |
|---|---|---|---|
| ① Tag + từ điển | `ie/weak_labels.py --version tag` | Dò lại tag nhà tuyển dụng và alias từ điển trong câu | F1 0,542 |
| ② Luật theo guideline | `ie/weak_labels.py --version rules`, `ie/weak_rules.py` | Thêm cụm guideline coi là kỹ năng, bỏ span guideline loại | F1 0,600 |
| ③ Self-training | `ie/self_train.py` | Thêm span mà cả 3 model PhoBERT (train trên ②) cùng đoán | (đo qua mô hình) |
| ④ LLM theo guideline | `ie/llm_label.py`, `ie/weak_llm.py` | Câu VietJobs: LLM đọc guideline, trả danh sách span; dò lại trên token thành BIO. Câu TopCV giữ nhãn ③ | F1 0,849 |

Ràng buộc của bước ④ (đều nằm trong code, không chỉ là quy ước):
- Chỉ câu có `job_uid` thuộc `vietjobs_it` được gửi đi. Câu crawl TopCV/ITviec và câu test bị chặn trước khi gọi API.
- Ví dụ trong guideline gửi kèm mà trùng một câu test thì bị bỏ khỏi prompt.
- Key đọc từ `.env` (không commit). Ghi số token và chi phí sau mỗi lần gọi, dừng khi vượt ngân sách.
- Kết quả lưu ở `data/llm/` (không commit) để tái lập, vì dịch vụ ngoài có thể đổi mô hình.
- Mô hình dùng: `gpt-6-luna`, `reasoning_effort` low, 20 câu mỗi lần gọi. Gán ~20.700 câu, chi phí ước ~0,54 USD.

### 3.3 Train và chọn mô hình

- `ie/phobert.py train --weak llm --seed <N>`: tách từ bằng underthesea, chỉ subword đầu của mỗi từ tính loss,
  lr 3e-5, 3 epoch, batch 16, chọn epoch theo F1 trên dev. Ba seed 1–3. Model ở `data/models/wm2-phobert-<nhãn>-s<N>`.
- Hai hướng sửa phía mô hình đã thử và **không** cải thiện (ghi trong `results.md`): học tiếp PhoBERT trên văn bản
  tin tuyển dụng (`ie/dapt.py`) và giảm trọng số token O (`--o-weight`).

### 3.4 Chấm điểm

- `ie/phobert.py eval … --bio data/annotation/skill_test1.bio.jsonl --split test`: seqeval strict, IOB2.
- `experiments/paired_wm2.py`: bootstrap ghép cặp theo tin (1.000 lần) so với mô hình trước, cùng seed.
- Quy tắc ghi trước khi chạy: chỉ gọi là "tốt hơn" khi CI95 của ΔF1 > 0 ở cả 3 seed; chỉ khi đó mới đổi image.
- Mỗi lần chạy ghi một file vào `experiments/runs/` (commit, metric, lệnh, snapshot).

| Hệ (TEST 1.000 câu) | P | R | F1 |
|---|---|---|---|
| Từ điển alias (baseline, cũng là bản stub) | 0,742 | 0,315 | 0,442 |
| PhoBERT, nhãn yếu self-training (image 0.1.0) | 0,715 | 0,543 | 0,617 |
| **PhoBERT, nhãn yếu LLM (image 0.2.0)** | **0,725** | **0,734** | **0,730** |

### 3.5 Đóng gói

1. Chép model seed 1 vào `data/models/skill-extractor/` (tên chung, image không phụ thuộc tên thí nghiệm).
2. Build từ gốc repo (`images/batch/Dockerfile`, target `full`, torch bản CPU, đã lọc gói CUDA):
   `docker build -f images/batch/Dockerfile --target full --build-arg JOB=skill_extractor --build-arg VERSION=$V -t joblens/skill-extractor:$V .`
   với `V=0.2.0-<gitsha>`. Bản `stub` (từ điển, không torch) build cùng Dockerfile.
3. Cập nhật `models.yaml` (version, metric, dữ liệu train, tập test).
4. Báo nhóm Big Data tag mới để đổi trong DAG và ghi `deploy/compat.md`.

## 4. Luồng chạy trong image (`batch/skill_extractor.py`)

```
 silver.job_postings (snapshot)      hoặc file Parquet cục bộ (--input-file)
        │  cột: job_uid, description, requirements, skill_tags
        ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │ 1. skill_tags (tag nhà tuyển dụng) → tra từ điển → skill_id, conf 1,0 │
 │ 2. description, requirements:                                         │
 │      bản full: tách dòng → token → PhoBERT → span BIO, conf 0,8       │
 │      bản stub: khớp từ điển alias, conf 0,9                            │
 │ 3. span → skill_id: ESCO URI nếu từ điển có, không thì joblens:<slug> │
 │ 4. bỏ trùng theo (job_uid, field, span_start, span_end)               │
 │ 5. model_version = tag image (x.y.z-gitsha), run_id do Airflow truyền │
 └─────────────────────────────────────────────────────────────────────┘
        │  ghi đè có điều kiện theo job_uid của lô (một giao dịch Iceberg)
        ▼
 silver.job_skills          hoặc file Parquet cục bộ (--output-file)
```

- Tham số (ADR 0001 D3): `--input-table silver.job_postings --input-snapshot <id> --output-table silver.job_skills --run-id <id>`.
  Chạy một mình: `--input-file … --output-file …`, thêm `--stub` cho bản từ điển.
- Biến môi trường: `JOBLENS_CATALOG_URI` và các biến S3 do Secret của Big Data cấp; `JOBLENS_SKILL_MODEL` (mặc định
  thư mục model trong image).
- Confidence là mức cố định theo nguồn để app lọc được, **không** phải xác suất đã hiệu chỉnh.
- Thời gian chạy trên CPU cho 50.000 tin: `<chưa đo>`; Big Data cần đo trước khi đưa vào DAG hằng ngày.
- Đã chạy thử image 0.2.0 trên 30 tin cục bộ: 525 dòng kỹ năng.

## 5. Thay đổi ở 0.2.0 và ảnh hưởng tới nhóm khác

| Thay đổi | Ảnh hưởng | Ai làm |
|---|---|---|
| Model mới (nhãn yếu LLM), cùng kiến trúc PhoBERT-base | Hợp đồng chạy, schema bảng, tài nguyên pod không đổi | – |
| Tag image `0.2.0-<gitsha>` | Đổi tag trong DAG; thêm dòng `deploy/compat.md` | Big Data |
| Recall tăng 0,54 → 0,73 | Mỗi tin ra nhiều kỹ năng hơn; số đếm ở gold/mart tăng. Không phải lỗi pipeline | Big Data, PTTKHT nên biết |
| `mining-service` | Không đổi (vẫn stub); `model_version` trả về là `stub-dict-alias` | – |
| Bước làm nhãn gọi API LLM | Chỉ ở máy WM lúc train; ghi trong `joblens/docs/project-plan/02-du-lieu.md` | – |

## 6. File và chỗ lưu

| Thứ | Chỗ | Commit? |
|---|---|---|
| Code, guideline, Dockerfile, `models.yaml`, `experiments/runs/*.json` | repo này | Có |
| Snapshot crawl, VietJobs, file nhãn (vàng, yếu, LLM), model | `data/` (gitignore); bản chia sẻ ở `s3://joblens/…` `<chưa đẩy>` | Không |
| Key OpenAI, token Label Studio | `.env`, `data/.ls_token` | Không bao giờ |

## 7. Hạn chế đã biết

- Nhãn LLM vẫn là nhãn yếu (F1 0,849 so với nhãn tay); một mô hình, gán một lần, chưa đo độ ổn định.
- 30/1.000 câu test trùng nguyên văn câu train; bỏ đi kết luận không đổi (0,731 so với 0,620).
- Chuẩn hóa ESCO chưa làm: `esco_uri` trong từ điển còn rỗng, `skill_id` hiện là id từ điển tự soạn.
- Dev (VietJobs) cao hơn test (TopCV) 0,067 F1: nhãn LLM trên văn bản VietJobs khớp dev hơn.
