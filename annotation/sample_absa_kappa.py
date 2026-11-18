"""Rút mẫu đo Cohen's κ cho WM3: lấy một phần tập đã gán để người thứ hai gán lại.

    uv run python -m annotation.sample_absa_kappa --gold data/annotation/absa_test1.absa.jsonl --batch absa_kappa1

Sinh trong data/annotation/ (không commit):
    <batch>.labelstudio.json   nhập vào project riêng của người thứ hai
    <batch>.manifest.json      seed, danh sách sentence_id, thống kê nhãn người thứ nhất

**Người thứ hai không được thấy nhãn người thứ nhất.** File task chỉ chứa các trường người gán được
phép thấy, giống lô gốc; nhãn người thứ nhất chỉ ghi vào manifest để biết mẫu này gồm những gì.
Vì vậy phải tạo **project Label Studio riêng**, không thêm annotation thứ hai vào project cũ.

Rút ngẫu nhiên đều, không chia hạn mức theo nhãn: κ phải ước lượng cho cả tập, chọn lệch về câu khó
thì κ thấp giả tạo. Tập gốc đã cân bằng khi rút nên mẫu ngẫu nhiên vẫn có đủ câu tiêu cực.

Câu đã tick "không gán được" bị loại: nó không vào điểm nên cũng không cần đo đồng thuận.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

from absa.lexicon import ASPECTS

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "annotation"
UNUSABLE = "không gán được"
DEFAULT_SHARE = 0.10


def load_gold(path: Path) -> list[dict]:
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if not (r.get("flag") or "").startswith(UNUSABLE)]


def to_label_studio(rows: list[dict]) -> list[dict]:
    """Chỉ các trường như lô gốc – KHÔNG có `gold`, `flag`, `comment` của người thứ nhất."""
    return [
        {
            "data": {
                "sentence_id": r["sentence_id"],
                "index": i,
                "text": r["text"],
                "company_name": r.get("company_name"),
                "section": r["section"],
                "lang": r["lang"],
            }
        }
        for i, r in enumerate(rows)
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", type=Path, default=OUT_DIR / "absa_test1.absa.jsonl")
    ap.add_argument("--batch", default="absa_kappa1")
    ap.add_argument("--n", type=int, help="số câu; để trống thì lấy ~10% số câu tính điểm")
    ap.add_argument("--seed", type=int, default=20261117)
    args = ap.parse_args()

    pool = load_gold(args.gold)
    n = args.n or max(1, round(len(pool) * DEFAULT_SHARE))
    if n > len(pool):
        raise SystemExit(f"--n {n} lớn hơn {len(pool)} câu tính điểm trong {args.gold.name}")
    chosen = random.Random(args.seed).sample(pool, n)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{args.batch}.labelstudio.json").write_text(
        json.dumps(to_label_studio(chosen), ensure_ascii=False, indent=1), "utf-8"
    )
    pairs = [(a, p) for r in chosen for a, p in r["gold"].items()]
    manifest = {
        "batch": args.batch,
        "muc_dich": "đo Cohen's κ giữa hai người gán",
        "gold_file": args.gold.name,
        "seed": args.seed,
        "n_cau": n,
        "n_cau_trong_pool": len(pool),
        "ti_le": round(n / len(pool), 3),
        "n_cap_nguoi_1": len(pairs),
        "theo_cuc_nguoi_1": dict(collections.Counter(p for _, p in pairs)),
        "theo_khia_canh_nguoi_1": {a: sum(1 for x, _ in pairs if x == a) for a in ASPECTS},
        "so_cau_khong_khia_canh_nguoi_1": sum(1 for r in chosen if not r["gold"]),
        "by_lang": dict(collections.Counter(r["lang"] for r in chosen)),
        "by_section": dict(collections.Counter(r["section"] for r in chosen)),
        "sentence_ids": [r["sentence_id"] for r in chosen],
    }
    (OUT_DIR / f"{args.batch}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    print({k: v for k, v in manifest.items() if k != "sentence_ids"})


if __name__ == "__main__":
    main()
