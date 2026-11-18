"""Đo Cohen's κ giữa hai người gán nhãn WM3 và in các câu lệch để ngồi soát.

    uv run python -m annotation.kappa_absa \
        --a data/annotation/absa_test1.absa.jsonl \
        --b data/annotation/absa_kappa1_p2.absa.jsonl

Ghép hai file theo `sentence_id`, chỉ lấy phần giao (người thứ hai thường chỉ gán ~10%).

Ba con số κ, vì một con số không nói được hai người lệch ở đâu:

| κ | Trên gì | Trả lời |
|---|---|---|
| ô 4 lớp | câu × 6 khía cạnh, nhãn `none/positive/neutral/negative` | đồng thuận tổng hợp |
| phát hiện khía cạnh | cùng các ô đó, nhãn nhị phân có/không nhắc tới | hai người có thấy cùng một khía cạnh không |
| cảm xúc | chỉ các ô **cả hai** đều gán khía cạnh | thấy rồi thì khen/chê có khớp không |
| lớp `negative` | cùng các ô, nhị phân chê / không chê | hai người có bắt cùng một lời chê không |

Mỗi κ kèm khoảng tin cậy 95% bootstrap **theo câu** (2.000 lần): mẫu κ thường chỉ ~35 câu, một κ
không kèm khoảng tin cậy ở cỡ đó dễ bị đọc quá tay.

Câu nào một trong hai người tick "không gán được" thì bỏ khỏi cả ba phép đo và báo riêng số lượng:
câu đó không vào điểm của tập test nên cũng không cần đo đồng thuận.

κ phạt sự trùng khớp ngẫu nhiên, nên κ của ô 4 lớp luôn thấp hơn "tỉ lệ ô giống nhau" – phần lớn ô là
`none`, đoán bừa `none` cũng khớp cao. Vì vậy không báo cáo tỉ lệ giống nhau thay cho κ.
"""

from __future__ import annotations

import argparse
import collections
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score

from absa.lexicon import ASPECTS
from absa.score import NONE, fmt, report, slots

ROOT = Path(__file__).resolve().parents[1]
UNUSABLE = "không gán được"


LABELS4 = [NONE, "positive", "neutral", "negative"]


def kappas(a: list[dict], b: list[dict]) -> dict[str, tuple[float, int]]:
    """Bốn κ (giá trị, số ô dùng để đo) cho hai danh sách nhãn đã ghép theo câu."""
    ya, yb = slots(a, b)  # câu × 6 ô, ô không nhắc tới = "none"
    out = {
        "ô 4 lớp": (cohen_kappa_score(ya, yb, labels=LABELS4), len(ya)),
        "phát hiện khía cạnh": (cohen_kappa_score([x != NONE for x in ya], [x != NONE for x in yb]), len(ya)),
        "lớp negative": (
            cohen_kappa_score([x == "negative" for x in ya], [x == "negative" for x in yb]),
            len(ya),
        ),
    }
    pol = [(x, y) for x, y in zip(ya, yb, strict=True) if x != NONE and y != NONE]
    k_pol = cohen_kappa_score([x for x, _ in pol], [y for _, y in pol]) if pol else float("nan")
    out["cảm xúc (ô cả hai gán)"] = (k_pol, len(pol))
    return out


def kappa_ci(a: list[dict], b: list[dict], b_reps: int = 2000, seed: int = 0) -> dict[str, tuple[float, float]]:
    """Khoảng tin cậy 95% của từng κ, bootstrap lấy lại câu (giữ nguyên 6 ô của mỗi câu)."""
    rng = np.random.default_rng(seed)
    n = len(a)
    vals: dict[str, list[float]] = {}
    with warnings.catch_warnings():
        # mẫu bootstrap không có ô chê nào thì κ lớp negative không xác định – bỏ mẫu đó, không in cảnh báo
        warnings.simplefilter("ignore")
        for _ in range(b_reps):
            ix = rng.integers(0, n, size=n)
            for k, (v, _) in kappas([a[i] for i in ix], [b[i] for i in ix]).items():
                if not np.isnan(v):
                    vals.setdefault(k, []).append(v)
    return {k: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in vals.items()}


def load(path: Path) -> dict[str, dict]:
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return {r["sentence_id"]: r for r in rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=Path, required=True, help="file nhãn người thứ nhất")
    ap.add_argument("--b", type=Path, required=True, help="file nhãn người thứ hai")
    ap.add_argument("--show", type=int, default=50, help="số câu lệch in ra")
    args = ap.parse_args()

    a_all, b_all = load(args.a), load(args.b)
    both = [sid for sid in a_all if sid in b_all]
    if not both:
        raise SystemExit("hai file không có câu nào chung (sentence_id không khớp)")

    unusable = [sid for sid in both if UNUSABLE in ((a_all[sid]["flag"] or "") + (b_all[sid]["flag"] or ""))]
    ids = [sid for sid in both if sid not in unusable]
    a = [a_all[sid]["gold"] for sid in ids]
    b = [b_all[sid]["gold"] for sid in ids]

    print(f"{len(both)} câu chung, bỏ {len(unusable)} câu 'không gán được' -> đo trên {len(ids)} câu")
    print(f"  người 1: {sum(len(g) for g in a)} cặp   người 2: {sum(len(g) for g in b)} cặp")

    n_neg = (sum(v == "negative" for g in a for v in g.values()), sum(v == "negative" for g in b for v in g.values()))
    print(f"  cặp negative: người 1 {n_neg[0]}, người 2 {n_neg[1]}")
    ks, cis = kappas(a, b), kappa_ci(a, b)
    print("\n| κ | giá trị | CI95 (bootstrap theo câu) | số ô |")
    print("|---|---|---|---|")
    for k, (v, n_cells) in ks.items():
        lo, hi = cis.get(k, (float("nan"), float("nan")))
        print(f"| {k} | {v:.3f} | [{lo:.3f}; {hi:.3f}] | {n_cells} |")

    # Lấy người 1 làm mốc để đọc được "người 2 gán thiếu hay gán thừa", không phải để nói ai đúng.
    print("\n" + fmt("người 2 so với người 1", report(a, b)))

    diff = [sid for sid in ids if a_all[sid]["gold"] != b_all[sid]["gold"]]
    print(f"\n{len(diff)}/{len(ids)} câu lệch ít nhất một khía cạnh")
    kinds: collections.Counter[str] = collections.Counter()
    for sid in ids:
        ga, gb = a_all[sid]["gold"], b_all[sid]["gold"]
        for asp in ASPECTS:
            x, y = ga.get(asp, NONE), gb.get(asp, NONE)
            if x == y:
                continue
            if x == NONE:
                kinds["người 2 gán thêm khía cạnh"] += 1
            elif y == NONE:
                kinds["người 2 bỏ sót khía cạnh"] += 1
            else:
                kinds[f"lệch cực: {x} / {y}"] += 1
    print("Kiểu lệch (theo ô):")
    for k, v in kinds.most_common():
        print(f"  {v:>3}  {k}")

    print(f"\n{min(args.show, len(diff))} câu lệch đầu tiên:")
    for sid in diff[: args.show]:
        r = a_all[sid]
        print(f"\n  [{sid}] ({r['lang']}, {r['section']}) {r['text']}")
        print(f"    người 1: {r['gold'] or '(để trống)'}")
        print(f"    người 2: {b_all[sid]['gold'] or '(để trống)'}")
        if b_all[sid].get("comment"):
            print(f"    ghi chú người 2: {b_all[sid]['comment']}")


if __name__ == "__main__":
    main()
