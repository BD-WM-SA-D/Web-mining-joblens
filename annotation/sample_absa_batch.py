"""Rút câu review để gán nhãn khía cạnh + cảm xúc (WM3).

    uv run python -m annotation.sample_absa_batch --n 300 --batch absa_trial    # 50–300 câu thử guideline
    uv run python -m annotation.sample_absa_batch --all --batch absa_batch1     # gán toàn bộ

Sinh trong data/annotation/ (không commit):
    <batch>.labelstudio.json   nhập vào Label Studio (cấu hình: annotation/label_studio_absa.xml)
    <batch>.manifest.json      seed, danh sách sentence_id, thống kê

**Vấn đề phải xử lý: dữ liệu lệch mạnh về tích cực.** ITviec chỉ cho khách xem một review đã được chọn
cho mỗi công ty, và review đó thiên về tích cực (đo 2026-11-13: review công khai cao hơn review bị mờ
0,27 sao; 0/141 review công khai nói "Không khuyến khích"). Cộng thêm phần `liked` dài hơn phần
`improvement`, nhãn yếu ra 835 tích cực / 91 tiêu cực. Rút ngẫu nhiên thì tập nhãn gần như không có
câu tiêu cực và Macro-F1 mất ý nghĩa.

Cách rút: **chia hạn mức theo nhãn yếu** để mọi khía cạnh và cả hai cực đều có mặt.
Ưu tiên theo thứ tự hạn mức giảm dần:

| Nhóm | Vì sao |
|---|---|
| `neg_<aspect>` | câu nhãn yếu tiêu cực – lớp thiếu nhất, lấy **tất cả** nếu còn chỗ |
| `pos_<aspect>` | câu nhãn yếu tích cực – lấy đều các khía cạnh, không để `culture_fun` chiếm hết |
| `no_aspect` | câu từ điển không nhận ra khía cạnh nào (31,6%) – **cần cho recall**: không gán thì không biết từ điển bỏ sót bao nhiêu |

Nhãn yếu chỉ dùng để *rút mẫu*, không đưa vào file gán nhãn và không hiện cho người gán.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

from absa.lexicon import ASPECTS
from absa.weak_labels import weak_label

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "annotation"
NO_ASPECT_SHARE = 0.20  # tỉ lệ dành cho câu từ điển không nhận ra khía cạnh


def group_of(sent: dict) -> str:
    """Nhóm rút mẫu của một câu, theo nhãn yếu (chỉ dùng để rút, không phải nhãn)."""
    labels = weak_label(sent)
    if not labels:
        return "no_aspect"
    neg = [lb for lb in labels if lb["polarity"] == "negative"]
    lb = neg[0] if neg else labels[0]
    return f"{'neg' if neg else 'pos'}_{lb['aspect']}"


def quotas(n: int) -> dict[str, int]:
    """Hạn mức mỗi nhóm: câu không nhận ra khía cạnh một phần, phần còn lại chia đều cho
    6 khía cạnh × 2 cực (ưu tiên lấy hết nhóm tiêu cực vì nhóm đó ít nhất)."""
    n_no = round(n * NO_ASPECT_SHARE)
    per = (n - n_no) // (len(ASPECTS) * 2)
    q = {"no_aspect": n_no}
    for a in ASPECTS:
        q[f"neg_{a}"] = per
        q[f"pos_{a}"] = per
    return q


def pick(sents: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Rút n câu theo hạn mức; nhóm nào thiếu thì phần dư chia lại cho nhóm còn hàng."""
    pools: dict[str, list[dict]] = collections.defaultdict(list)
    for s in sents:
        pools[group_of(s)].append(s)
    for pool in pools.values():
        rng.shuffle(pool)

    q = quotas(n)
    chosen: list[dict] = []
    # vòng 1: theo hạn mức, nhóm tiêu cực trước (ít hàng nhất, dễ bị bỏ sót)
    for g in sorted(q, key=lambda g: (not g.startswith("neg_"), g)):
        take = pools[g][: q[g]]
        pools[g] = pools[g][len(take) :]
        chosen += take
    # vòng 2: còn thiếu thì lấy thêm từ các nhóm còn hàng, luân phiên để khỏi lệch về một nhóm
    rest = [g for g in sorted(pools) if pools[g]]
    i = 0
    while len(chosen) < n and rest:
        g = rest[i % len(rest)]
        if pools[g]:
            chosen.append(pools[g].pop())
            i += 1
        else:
            rest.remove(g)
    rng.shuffle(chosen)  # trộn để người gán không gán theo cụm
    return chosen[:n]


def to_label_studio(sents: list[dict]) -> list[dict]:
    """Chỉ đưa những trường người gán được phép thấy: KHÔNG có điểm sao (đó là nhãn yếu)."""
    return [
        {
            "data": {
                "sentence_id": s["sentence_id"],
                "index": i,
                "text": s["text"],
                "company_name": s.get("company_name"),
                "section": s["section"],
                "lang": s["lang"],
            }
        }
        for i, s in enumerate(sents)
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sentences", type=Path, default=ROOT / "data" / "absa" / "sentences.jsonl")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--all", action="store_true", help="lấy toàn bộ câu, bỏ qua --n")
    ap.add_argument("--seed", type=int, default=20261115)
    ap.add_argument("--batch", default="absa_batch1")
    ap.add_argument(
        "--exclude-reviews-of",
        type=Path,
        help="file nhãn (.absa.jsonl): loại MỌI câu thuộc cùng review với các câu trong file đó",
    )
    ap.add_argument(
        "--only-reviews-of",
        type=Path,
        help="ngược với --exclude-reviews-of: chỉ lấy câu thuộc cùng review với các câu trong file đó (mở rộng tập dev)",
    )
    ap.add_argument(
        "--exclude-ids",
        type=Path,
        action="append",
        default=[],
        help="manifest của lô trước: loại đúng những câu đã ở trong lô đó (giữ nguyên các câu khác của cùng review)",
    )
    ap.add_argument(
        "--exclude-texts-of",
        type=Path,
        help="file nhãn (.absa.jsonl): loại đúng những câu đã gán trong file đó, khớp theo văn bản "
        "(dùng khi `sentence_id` đã đổi vì sửa bộ tách câu, lúc đó manifest cũ không khớp nữa)",
    )
    ap.add_argument(
        "--only-section",
        choices=("title", "liked", "improvement"),
        help="chỉ lấy câu từ một phần của review",
    )
    args = ap.parse_args()

    sents = [json.loads(ln) for ln in args.sentences.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if args.exclude_reviews_of:
        # Chia dev/test theo REVIEW, không theo câu. Hai câu cùng một review dùng chung điểm sao và
        # cùng văn phong; để một câu ở dev, câu kia ở test là rò rỉ – mô hình train trên nhãn yếu của
        # review đó rồi lại bị chấm trên chính review đó.
        labeled = {
            json.loads(ln)["text"]
            for ln in args.exclude_reviews_of.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        }
        drop = {s["source_review_id"] for s in sents if s["text"] in labeled}
        before = len(sents)
        sents = [s for s in sents if s["source_review_id"] not in drop]
        print(f"loại {before - len(sents)} câu thuộc {len(drop)} review đã dùng ở lô trước")
    if args.only_reviews_of:
        # Mở rộng tập dev: lấy thêm câu từ đúng những review đã ở dev, để không review nào
        # vừa có câu ở dev vừa có câu ở test.
        labeled = {
            json.loads(ln)["text"] for ln in args.only_reviews_of.read_text(encoding="utf-8").splitlines() if ln.strip()
        }
        keep = {s["source_review_id"] for s in sents if s["text"] in labeled}
        before = len(sents)
        sents = [s for s in sents if s["source_review_id"] in keep]
        print(f"chỉ giữ {len(sents)}/{before} câu thuộc {len(keep)} review của {args.only_reviews_of.name}")

    for man in args.exclude_ids:
        # Lô bổ sung lấy thêm câu từ **chính các review đã có trong TEST**, nên không dùng
        # `--exclude-reviews-of` ở đây: chỉ bỏ đúng câu đã gán, không bỏ cả review.
        done = set(json.loads(man.read_text(encoding="utf-8"))["sentence_ids"])
        before = len(sents)
        sents = [s for s in sents if s["sentence_id"] not in done]
        print(f"loại {before - len(sents)} câu đã có trong {man.name}")
    if args.exclude_texts_of:
        done = {
            json.loads(ln)["text"]
            for ln in args.exclude_texts_of.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        }
        before = len(sents)
        sents = [s for s in sents if s["text"] not in done]
        print(f"loại {before - len(sents)} câu đã gán trong {args.exclude_texts_of.name}")

    if args.only_section:
        before = len(sents)
        sents = [s for s in sents if s["section"] == args.only_section]
        print(f"chỉ giữ phần '{args.only_section}': {len(sents)}/{before} câu")

    rng = random.Random(args.seed)
    if args.all:
        chosen = list(sents)
        rng.shuffle(chosen)
    else:
        chosen = pick(sents, args.n, rng)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{args.batch}.labelstudio.json").write_text(
        json.dumps(to_label_studio(chosen), ensure_ascii=False, indent=1), "utf-8"
    )
    by_group = collections.Counter(group_of(s) for s in chosen)
    manifest = {
        "batch": args.batch,
        "seed": args.seed,
        "sentences_file": str(args.sentences.name),
        "n": len(chosen),
        "by_lang": dict(collections.Counter(s["lang"] for s in chosen)),
        "by_section": dict(collections.Counter(s["section"] for s in chosen)),
        "by_weak_group": dict(sorted(by_group.items())),
        "sentence_ids": [s["sentence_id"] for s in chosen],
    }
    (OUT_DIR / f"{args.batch}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    print({k: v for k, v in manifest.items() if k != "sentence_ids"})


if __name__ == "__main__":
    main()
