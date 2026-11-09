# Format kết quả thực nghiệm

Mục đích: mọi kết quả ghi theo **cùng một khuôn**, để người viết báo cáo chép thẳng bảng và nhận xét, và mọi con số truy được về lệnh chạy.

Mỗi thí nghiệm có **hai phần**:

| Phần | Ai tạo | Nằm ở đâu | Dùng để |
|---|---|---|---|
| **A. File kết quả máy đọc** (JSON) | Script đánh giá **tự ghi** sau mỗi lần chạy | `experiments/runs/<run_id>.json` (commit được, chỉ chứa số) | Gộp tự động thành bảng cho `results.md` và báo cáo |
| **B. Phiếu kết quả** (Markdown) | Người phụ trách bài viết, **một phiếu cho mỗi thí nghiệm đã chốt** | `experiments/cards/<mã>.md` | Nhận xét, phân tích lỗi, insight, chép vào báo cáo |

`experiments/results.md` vẫn là bảng tổng: mỗi thí nghiệm một dòng, trỏ tới phiếu.

## A. File kết quả JSON

Tên file: `<ngày>-<bài>-<phương pháp>-<tập>-s<seed>.json`, ví dụ `2026-11-20-wm2-phobert-test-s1.json`.

```json
{
  "run_id": "2026-11-20-wm2-phobert-test-s1",
  "task": "WM2",
  "rq": "RQ3",
  "method": "phobert-base-v2+weak",
  "baseline_of": "dict-alias-v0",
  "data": {
    "eval_set": "skill_test1",
    "split": "test",
    "snapshot": "topcv_v1",
    "ids_sha256": "61bad0f9…",
    "n_items": 1000,
    "n_gold": 0
  },
  "train": {"data": "weak_vietjobs_topcv_v1", "n_items": 0, "params": {"lr": 3e-5, "epochs": 5}},
  "seed": 1,
  "metrics": {"precision": 0.0, "recall": 0.0, "f1": 0.0, "f1_partial": 0.0},
  "ci95": {"f1": [0.0, 0.0]},
  "vs_baseline": {"metric": "f1", "delta": 0.0, "ci95": [0.0, 0.0]},
  "runtime": {"seconds": 0, "hardware": "RTX …", "p95_latency_ms": null},
  "repro": {"command": "uv run python -m ie.eval …", "git_commit": "abc1234", "models_yaml": "wm2-phobert@0.1.0"},
  "created_at": "2026-11-20T10:00:00+07:00"
}
```

Quy định:
- **Không ghi dữ liệu gốc hay câu văn** vào JSON, chỉ ghi số.
- `metrics` dùng tên cố định theo bài (bảng dưới), để script gộp không phải đoán.
- Chạy nhiều seed thì mỗi seed một file. Script gộp tự tính trung bình ± độ lệch chuẩn.
- Lần chạy **trên test** phải có `repro.git_commit`. Chạy test lại với commit khác thì phải ghi lý do trong phiếu.

| Bài | Tên metric cố định |
|---|---|
| Thu thập | `field_acc_<trường>`, `pii_recall`, `http_429`, `http_403`, `schema_valid_rate` |
| WM1 | `precision`, `recall`, `f1`, `blocking_recall`, `dup_rate` |
| WM2 | `precision`, `recall`, `f1`, `f1_partial`, `novel_skill_rate`, `norm_acc` |
| WM3 | `aspect_f1_micro`, `aspect_f1_macro`, `sentiment_f1_macro`, `spearman_stars` |
| WM5 | `ndcg@10`, `recall@10`, `coverage`, `explained_rate` |
| WM6 | `modularity`, `modularity_random_mean`, `kendall_tau_pr_freq`, `n_communities` |
| WM4 | `ndcg@10`, `mrr` |
| κ | `kappa` (thêm `task`, `n_items`, `annotators`) |
| Service | `p95_latency_ms`, `contract_pass_rate` |

## B. Phiếu kết quả (chép mẫu dưới cho mỗi thí nghiệm)

```markdown
# <Mã> – <Tên thí nghiệm>          ví dụ: WM2-E2 – PhoBERT với nhãn yếu

**Câu hỏi (RQ):** RQ3 – …
**Người làm / ngày chốt:** … / …
**Dùng ở mục báo cáo:** Chương 3.4 (Thực nghiệm WM2)

## Thiết lập
- Dữ liệu đánh giá: <tập>, <split>, snapshot <tên> (ids_sha256 …), <n> mẫu
- Dữ liệu train: …
- Phương pháp và tham số chính: …
- Baseline so sánh: …
- File kết quả: `experiments/runs/…json` (seed 1–3)
- Lệnh tái lập: `…`

## Kết quả
| Phương pháp | P | R | F1 | Khoảng tin cậy 95% |
|---|---|---|---|---|
| Baseline | | | | |
| Mô hình (3 seed, TB ± ĐLC) | | | | |
| Chênh lệch | | | | [ , ] |

## Phân tích lỗi (≥ 30 ví dụ)
| Loại lỗi | Số lượng | % | Ví dụ ngắn (đã bỏ thông tin cá nhân) |
|---|---|---|---|
| Bỏ sót | | | |
| Gán thừa | | | |
| Lệch ranh giới | | | |
| … | | | |

## Insight (1–3 câu, mỗi câu kèm số)
- …

## Ý nghĩa cho sản phẩm
- …

## Hạn chế của thí nghiệm này
- …
```

## Quy trình

1. Script đánh giá gọi hàm ghi JSON ở cuối mỗi lần chạy.
2. Khi chốt một thí nghiệm, người phụ trách viết phiếu B. Insight và hạn chế phải có số đi kèm.
3. Người kia (review chéo) chạy lại lệnh trong phiếu, ra cùng số thì ghi "đã kiểm" vào phiếu.
4. Script gộp đọc `experiments/runs/*.json` và sinh bảng tổng (Markdown cho `results.md`, có thể thêm LaTeX cho báo cáo).
5. Người viết báo cáo chỉ lấy số từ bảng gộp và phiếu, không chép tay từ log.
