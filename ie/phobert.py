"""WM2 – PhoBERT-base-v2 token classification (nhãn SKILL, BIO), train trên nhãn yếu, chọn tham số trên dev.

    uv sync --group ml
    uv run python -m ie.phobert train --seed 1                       # train + chấm dev, ghi experiments/runs/*.json
    uv run python -m ie.phobert eval --model data/models/wm2-phobert-tag-s1 --bio data/annotation/skill_test1.bio.jsonl \
        --eval-set skill_test1 --split test

- PhoBERT cần đầu vào đã tách từ (âm tiết nối bằng "_"): tách bằng underthesea trên token gốc (TOKEN_RE), mỗi "đơn vị"
  là một từ của underthesea, gồm một hoặc nhiều token gốc. Nhãn của đơn vị = nhãn token đầu; khi chấm thì trải ngược về
  token gốc (B → B I I…, I → I…, O → O…) để vẫn chấm seqeval trên token gốc như baseline.
- Chỉ subword đầu của mỗi đơn vị được tính loss (-100 cho phần còn lại).
- Mất mát do tách từ (ranh giới span nằm giữa một từ) được đo bằng `oracle`: đổi nhãn vàng dev sang đơn vị rồi trải
  ngược, chấm với nhãn vàng.
- File model ghi vào data/models/ (đã gitignore), không commit.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from seqeval.metrics import f1_score, precision_score, recall_score
from seqeval.scheme import IOB2

from annotation.preannotate_dict import load_aliases
from ie.baseline_dict import build_index, tag

ROOT = Path(__file__).resolve().parents[1]
WEAK_DIR = ROOT / "data" / "weak"
DEV = ROOT / "data" / "annotation" / "skill_batch1.bio.jsonl"
MODELS = ROOT / "data" / "models"
BASE = "vinai/phobert-base-v2"
LABELS = ["O", "B-SKILL", "I-SKILL"]
L2I = {lab: i for i, lab in enumerate(LABELS)}
SEQ = {"mode": "strict", "scheme": IOB2}


# ---------- tách từ và ánh xạ nhãn ----------


def segment(tokens: list[str], word_tokenize=None) -> list[tuple[str, list[int]]]:
    """Gom token gốc thành đơn vị theo từ của underthesea. Trả [(chuỗi cho PhoBERT, [chỉ số token gốc])].

    Ghép theo ký tự (bỏ khoảng trắng): token và từ được lấy dần cho tới khi hai chuỗi bằng nhau, nên chịu được
    trường hợp underthesea tách khác TOKEN_RE (ví dụ "C++").
    """
    if word_tokenize is None:
        from underthesea import word_tokenize
    if not tokens:
        return []
    words = [w.replace(" ", "") for w in word_tokenize(" ".join(tokens))]
    units, ti, wi = [], 0, 0
    while ti < len(tokens):
        idx, t_str, w_str = [ti], tokens[ti], words[wi] if wi < len(words) else ""
        ti += 1
        wi += 1
        while len(t_str) != len(w_str) or t_str != w_str:
            if len(t_str) < len(w_str) and ti < len(tokens):
                idx.append(ti)
                t_str += tokens[ti]
                ti += 1
            elif wi < len(words) and len(w_str) < len(t_str):
                w_str += words[wi]
                wi += 1
            else:  # lệch không ghép được (hiếm): lấy mỗi token một đơn vị cho phần còn lại
                break
        units.append(("_".join(tokens[i] for i in idx), idx))
    return units


def to_units(tags: list[str], units: list[tuple[str, list[int]]]) -> list[str]:
    return [tags[idx[0]] for _, idx in units]


def from_units(unit_tags: list[str], units: list[tuple[str, list[int]]], n_tokens: int) -> list[str]:
    out = ["O"] * n_tokens
    for t, (_, idx) in zip(unit_tags, units, strict=True):
        if t == "O":
            continue
        out[idx[0]] = t
        for i in idx[1:]:
            out[i] = "I-SKILL"
    return out


# ---------- dữ liệu ----------


def read_bio(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def prepare(rows: list[dict], cache: Path | None = None) -> list[dict]:
    """Thêm trường units (cache theo id vì tách từ 24k câu mất ~1 phút)."""
    seg = {}
    if cache and cache.exists():
        seg = {r["id"]: r["units"] for r in read_bio(cache)}
    out, new = [], []
    for r in rows:
        units = seg.get(r["id"])
        if units is None:
            units = [[u, idx] for u, idx in segment(r["tokens"])]
            new.append({"id": r["id"], "units": units})
        out.append({**r, "units": [(u, idx) for u, idx in units]})
    if cache and new:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("a", encoding="utf-8") as f:
            for n in new:
                f.write(json.dumps(n, ensure_ascii=False) + "\n")
    return out


def encode(tokenizer, units: list[tuple[str, list[int]]], unit_tags: list[str] | None, max_len: int):
    ids, labels, first = [tokenizer.cls_token_id], [-100], []
    for k, (u, _) in enumerate(units):
        sub = tokenizer.convert_tokens_to_ids(tokenizer.tokenize(u)) or [tokenizer.unk_token_id]
        if len(ids) + len(sub) >= max_len - 1:
            break
        first.append(len(ids))
        labels += [L2I[unit_tags[k]] if unit_tags else -100] + [-100] * (len(sub) - 1)
        ids += sub
    ids.append(tokenizer.sep_token_id)
    labels.append(-100)
    return ids, labels, first


# ---------- train / predict ----------


def predict(model, tokenizer, rows: list[dict], max_len: int, device, bs: int = 32) -> list[list[str]]:
    import torch

    model.eval()
    preds = []
    for s in range(0, len(rows), bs):
        batch = rows[s : s + bs]
        enc = [encode(tokenizer, r["units"], None, max_len) for r in batch]
        width = max(len(e[0]) for e in enc)
        ids = torch.full((len(enc), width), tokenizer.pad_token_id)
        mask = torch.zeros((len(enc), width), dtype=torch.long)
        for i, (x, _, _) in enumerate(enc):
            ids[i, : len(x)] = torch.tensor(x)
            mask[i, : len(x)] = 1
        with torch.no_grad():
            logits = model(input_ids=ids.to(device), attention_mask=mask.to(device)).logits.argmax(-1).cpu()
        for i, r in enumerate(batch):
            first = enc[i][2]
            ut = [LABELS[int(logits[i, p])] for p in first] + ["O"] * (len(r["units"]) - len(first))
            ut = [("B-SKILL" if t == "I-SKILL" and (k == 0 or ut[k - 1] == "O") else t) for k, t in enumerate(ut)]
            preds.append(from_units(ut, r["units"], len(r["tokens"])))
    return preds


def hybrid(model_tags: list[str], dict_tags: list[str]) -> list[str]:
    """Thêm span của từ điển vào chỗ mô hình để trống (không đè span của mô hình)."""
    out = list(model_tags)
    i = 0
    while i < len(dict_tags):
        if dict_tags[i] == "B-SKILL":
            j = i + 1
            while j < len(dict_tags) and dict_tags[j] == "I-SKILL":
                j += 1
            if all(t == "O" for t in model_tags[i:j]) and (j >= len(out) or out[j] != "I-SKILL"):
                out[i:j] = dict_tags[i:j]
            i = j
        else:
            i += 1
    return out


def scores(gold, pred) -> dict[str, float]:
    return {
        "precision": precision_score(gold, pred, **SEQ),
        "recall": recall_score(gold, pred, **SEQ),
        "f1": f1_score(gold, pred, **SEQ),
    }


def evaluate(model, tokenizer, rows, max_len, device) -> dict[str, dict[str, float]]:
    index, max_n = build_index(load_aliases())
    gold = [r["tags"] for r in rows]
    pred = predict(model, tokenizer, rows, max_len, device)
    dct = [tag(r["tokens"], index, max_n) for r in rows]
    return {
        "phobert": scores(gold, pred),
        "phobert+dict": scores(gold, [hybrid(p, d) for p, d in zip(pred, dct, strict=True)]),
    }, pred


def token_loss(logits, labels, o_weight: float = 1.0):
    """Cross-entropy theo token; token nhãn O nhân `o_weight` (< 1: bớt phạt vì nhãn yếu bỏ sót). Chia cho số token
    có nhãn, nên o_weight = 1 trùng với loss mặc định của transformers."""
    import torch.nn.functional as F

    flat = labels.view(-1)
    ce = F.cross_entropy(logits.view(-1, logits.size(-1)).float(), flat, ignore_index=-100, reduction="none")
    valid = flat != -100
    w = valid.float()
    if o_weight != 1.0:
        w = w * ((flat == L2I["O"]).float() * (o_weight - 1.0) + 1.0)
    return (ce * w).sum() / valid.sum().clamp(min=1)


def train(args) -> None:
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer, get_linear_schedule_with_warmup

    from experiments.runlog import save_run

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    t0 = time.time()
    weak = prepare(read_bio(args.train or WEAK_DIR / f"wm2_weak_{args.weak}.bio.jsonl"), MODELS / "seg_cache.jsonl")
    dev = prepare(read_bio(args.dev), MODELS / "seg_cache.jsonl")
    pos = [r for r in weak if "B-SKILL" in r["tags"]]
    neg = [r for r in weak if "B-SKILL" not in r["tags"]]
    rng = random.Random(args.seed)
    train_rows = pos + rng.sample(neg, min(len(neg), int(len(pos) * args.neg_ratio)))
    print(f"train {len(train_rows)} câu ({len(pos)} có span, neg_ratio {args.neg_ratio}); dev {len(dev)}")

    gold_dev = [r["tags"] for r in dev]
    oracle = [from_units(to_units(r["tags"], r["units"]), r["units"], len(r["tokens"])) for r in dev]
    print(f"oracle tách từ trên dev (trần do ranh giới từ): F1={f1_score(gold_dev, oracle, **SEQ):.3f}")

    tok = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForTokenClassification.from_pretrained(
        args.base, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)), label2id=L2I
    ).to(device)
    enc = [encode(tok, r["units"], to_units(r["tags"], r["units"]), args.max_len) for r in train_rows]
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = args.epochs * ((len(enc) + args.bs - 1) // args.bs)
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")

    name = f"wm2-phobert-{args.weak}" + (f"-{args.tag}" if args.tag else "")
    out_dir = MODELS / f"{name}-s{args.seed}"
    best, best_res = -1.0, None
    for ep in range(args.epochs):
        model.train()
        order = list(range(len(enc)))
        rng.shuffle(order)
        total = 0.0
        for s in range(0, len(order), args.bs):
            b = [enc[i] for i in order[s : s + args.bs]]
            width = max(len(x[0]) for x in b)
            ids = torch.full((len(b), width), tok.pad_token_id)
            lab = torch.full((len(b), width), -100)
            mask = torch.zeros((len(b), width), dtype=torch.long)
            for i, (x, y, _) in enumerate(b):
                ids[i, : len(x)] = torch.tensor(x)
                lab[i, : len(y)] = torch.tensor(y)
                mask[i, : len(x)] = 1
            with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                logits = model(input_ids=ids.to(device), attention_mask=mask.to(device)).logits
                loss = token_loss(logits, lab.to(device), args.o_weight)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            total += loss.item()
        res, _ = evaluate(model, tok, dev, args.max_len, device)
        line = " | ".join(f"{k} P={v['precision']:.3f} R={v['recall']:.3f} F1={v['f1']:.3f}" for k, v in res.items())
        print(f"epoch {ep + 1}: loss {total / max(1, len(order) // args.bs):.4f} | {line}")
        if res["phobert"]["f1"] > best:
            best, best_res = res["phobert"]["f1"], res
            model.save_pretrained(out_dir)
            tok.save_pretrained(out_dir)

    minutes = round((time.time() - t0) / 60, 1)
    print(f"tốt nhất dev F1={best:.3f} → {out_dir} ({minutes} phút)")
    params = {
        "lr": args.lr,
        "epochs": args.epochs,
        "bs": args.bs,
        "neg_ratio": args.neg_ratio,
        "max_len": args.max_len,
        "o_weight": args.o_weight,
    }
    for method, m in best_res.items():
        save_run(
            task="WM2",
            rq="RQ3",
            method=method_name(method, args),
            baseline_of="dict-alias",
            eval_set="skill_batch1",
            split="dev",
            metrics=m,
            ids=[r["id"] for r in dev],
            seed=args.seed,
            train={
                "data": f"wm2_weak_{args.weak}",
                "base": str(args.base),
                "n_items": len(train_rows),
                "params": params,
            },
            runtime={"minutes": minutes, "hardware": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu"},
        )


def method_name(method: str, args) -> str:
    return f"{method}-weak-{args.weak}" + (f"-{args.tag}" if args.tag else "")


def eval_cmd(args) -> None:
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForTokenClassification.from_pretrained(args.model).to(device)
    rows = prepare(read_bio(args.bio), MODELS / "seg_cache.jsonl")
    res, _ = evaluate(model, tok, rows, args.max_len, device)
    for k, v in res.items():
        print(f"{k:14s} P={v['precision']:.3f} R={v['recall']:.3f} F1={v['f1']:.3f}")
    if args.eval_set:
        from experiments.runlog import save_run

        for method, m in res.items():
            save_run(
                task="WM2",
                rq="RQ3",
                method=method_name(method, args),
                baseline_of="dict-alias",
                eval_set=args.eval_set,
                split=args.split,
                metrics=m,
                ids=[r["id"] for r in rows],
                seed=args.seed,
                train={"data": f"wm2_weak_{args.weak}", "model": str(args.model)},
            )


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--weak", default="tag", help="bộ nhãn yếu: tag, rules, selftrain, globaltag, llm")
    t.add_argument("--train", type=Path, help="mặc định data/weak/wm2_weak_<weak>.bio.jsonl")
    t.add_argument("--dev", type=Path, default=DEV)
    t.add_argument("--seed", type=int, default=1)
    t.add_argument("--epochs", type=int, default=3)
    t.add_argument("--lr", type=float, default=3e-5)
    t.add_argument("--bs", type=int, default=16)
    t.add_argument("--neg-ratio", type=float, default=0.3)
    t.add_argument("--max-len", type=int, default=256)
    t.add_argument("--o-weight", type=float, default=1.0, help="hệ số loss cho token nhãn O (mặc định 1 = như cũ)")
    t.add_argument("--base", default=BASE, help="mô hình gốc: tên Hugging Face hoặc thư mục (vd bản DAPT)")
    t.add_argument("--tag", help="hậu tố tên model và tên phương pháp, vd dapt → wm2-phobert-selftrain-dapt-s1")
    e = sub.add_parser("eval")
    e.add_argument("--weak", default="tag", help="bộ nhãn yếu model đã train, để ghi vào run")
    e.add_argument("--model", type=Path, required=True)
    e.add_argument("--bio", type=Path, default=DEV)
    e.add_argument("--max-len", type=int, default=256)
    e.add_argument("--eval-set", help="có thì ghi experiments/runs/<run_id>.json, ví dụ skill_batch1")
    e.add_argument("--split", default="dev")
    e.add_argument("--seed", type=int, default=0, help="seed lúc train model, để ghi vào run")
    e.add_argument("--tag", help="như train --tag, để ghi tên phương pháp")
    args = ap.parse_args()
    train(args) if args.cmd == "train" else eval_cmd(args)


if __name__ == "__main__":
    main()
