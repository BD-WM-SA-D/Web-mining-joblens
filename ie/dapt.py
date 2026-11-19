"""WM2 – tiền huấn luyện thích nghi miền (DAPT): PhoBERT-base-v2 học tiếp masked LM trên văn bản tin VietJobs.

    uv run python -m ie.dapt corpus          # tách câu + tách từ 48k tin → data/dapt/vietjobs_seg.jsonl (~30 phút)
    uv run python -m ie.dapt train           # MLM 1 epoch → data/models/phobert-dapt-vietjobs/
    uv run python -m ie.phobert train --weak v3 --base data/models/phobert-dapt-vietjobs --tag dapt --seed 1

Cấu hình theo mục đăng ký trước "VietJobs cho WM6 và WM2" trong `experiments/results.md` – không đổi sau khi xem số.

- Corpus chỉ là VietJobs (Pham Dinh et al., LREC 2026): tiêu đề + mô tả + yêu cầu, không dùng nhãn. Không dùng văn
  bản crawl TopCV/ITviec vì `skill_test1` lấy câu từ đó.
- Chống rò rỉ: câu nào trùng nguyên văn (chữ thường, gộp khoảng trắng) với một câu `skill_test1` thì bỏ; số câu bỏ
  ghi vào manifest.
- Tách câu (`split_sentences`), token (TOKEN_RE) và tách từ (underthesea) giống hệt lúc fine-tune, để mô hình học
  đúng dạng đầu vào nó sẽ gặp.
- Câu của cùng một tin được nối thành đoạn ≤ 256 subword (nhiều ngữ cảnh hơn và ít đệm hơn mỗi câu một mẫu).
- File corpus và model nằm trong data/ (gitignore), không commit.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "vietjobs" / "VietJobs.csv"
TEST = ROOT / "data" / "annotation" / "skill_test1.bio.jsonl"
CORPUS = ROOT / "data" / "dapt" / "vietjobs_seg.jsonl"
OUT = ROOT / "data" / "models" / "phobert-dapt-vietjobs"
BASE = "vinai/phobert-base-v2"
FIELDS = ("job_title", "description", "requirements_text")
TOKEN_RE = re.compile(r"\w+[+#]*|[^\w\s]")  # giống annotation/export_bio.py
SEED = 1


def norm(tokens: list[str]) -> str:
    return " ".join(tokens).lower()


def test_keys() -> set[str]:
    return {norm(json.loads(x)["tokens"]) for x in TEST.read_text("utf-8").splitlines() if x.strip()}


def job_sentences(row: dict) -> list[list[str]]:
    from annotation.sample_skill_batch import split_sentences

    out = []
    title = row.get("job_title")
    if isinstance(title, str) and title.strip():
        out.append(TOKEN_RE.findall(title))
    for f in FIELDS[1:]:
        out += [TOKEN_RE.findall(s) for s in split_sentences(row.get(f))]
    return [t for t in out if t]


def _segment_job(item: tuple[int, list[list[str]]]) -> dict:
    from ie.phobert import segment

    i, sents = item
    return {"i": i, "sents": [" ".join(u for u, _ in segment(t)) for t in sents]}


def cmd_corpus(args) -> None:
    from multiprocessing import Pool

    import pandas as pd

    df = pd.read_csv(args.csv)
    keys = test_keys()
    done = set()
    if CORPUS.exists():
        done = {json.loads(x)["i"] for x in CORPUS.read_text("utf-8").splitlines() if x.strip()}
    items, dropped, total = [], 0, 0
    for i, row in enumerate(df.to_dict("records")):
        sents = job_sentences(row)
        total += len(sents)
        keep = [t for t in sents if norm(t) not in keys]
        dropped += len(sents) - len(keep)
        if i not in done and keep:
            items.append((i, keep))
    print(
        f"{len(df)} tin, {total} câu; bỏ {dropped} câu trùng skill_test1; còn {len(items)} tin cần tách từ", flush=True
    )
    CORPUS.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with Pool(args.workers) as pool, CORPUS.open("a", encoding="utf-8") as f:
        for n, rec in enumerate(pool.imap(_segment_job, items, chunksize=32), 1):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if n % 2000 == 0:
                rate = n / (time.time() - t0)
                print(
                    f"  {n}/{len(items)} tin ({rate:.0f} tin/giây, còn ~{(len(items) - n) / rate / 60:.0f} phút)",
                    flush=True,
                )
    meta = {"csv": str(args.csv), "jobs": len(df), "sentences": total, "dropped_test_overlap": dropped}
    CORPUS.with_suffix(".manifest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    print(f"xong → {CORPUS}", flush=True)


def chunks(tok, max_len: int) -> list[list[int]]:
    """Nối câu của cùng một tin thành đoạn ≤ max_len subword (kể cả <s> </s>). Câu dài hơn thì cắt."""
    body = max_len - 2
    out = []
    for line in CORPUS.read_text("utf-8").splitlines():
        cur: list[int] = []
        for sent in json.loads(line)["sents"]:
            ids = tok(sent, add_special_tokens=False)["input_ids"][:body]
            if cur and len(cur) + len(ids) > body:
                out.append(cur)
                cur = []
            cur = cur + ids
        if cur:
            out.append(cur)
    return [[tok.cls_token_id, *c, tok.sep_token_id] for c in out]


def mlm_loss(model, collate, data, bs, device) -> float:
    import torch

    model.eval()
    total, n = 0.0, 0
    with torch.no_grad():
        for s in range(0, len(data), bs):
            batch = collate([{"input_ids": x} for x in data[s : s + bs]])
            with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                loss = model(**{k: v.to(device) for k, v in batch.items()}).loss
            total += loss.item() * len(batch["input_ids"])
            n += len(batch["input_ids"])
    model.train()
    return total / max(1, n)


def cmd_train(args) -> None:
    import torch
    from transformers import (
        AutoModelForMaskedLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        get_linear_schedule_with_warmup,
    )

    random.seed(SEED)
    torch.manual_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(BASE)
    t0 = time.time()
    data = chunks(tok, args.max_len)
    rng = random.Random(SEED)
    rng.shuffle(data)
    held, data = data[: args.held_out], data[args.held_out :]
    if args.max_chunks and len(data) > args.max_chunks:
        data = data[: args.max_chunks]
    n_tok = sum(len(x) for x in data)
    print(
        f"{len(data)} đoạn train ({n_tok / 1e6:.1f}M subword), {len(held)} đoạn giữ lại; tokenize {time.time() - t0:.0f}s"
    )

    model = AutoModelForMaskedLM.from_pretrained(BASE).to(device)
    collate = DataCollatorForLanguageModeling(tok, mlm_probability=args.mlm_prob)
    torch.manual_seed(SEED)
    before = mlm_loss(model, collate, held, args.micro_bs, device)
    print(f"loss MLM giữ lại trước DAPT: {before:.3f} (perplexity {math.exp(before):.1f})", flush=True)

    accum = args.bs // args.micro_bs
    steps = math.ceil(len(data) / args.bs) * args.epochs
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, int(args.warmup * steps), steps)
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")
    data.sort(key=len)  # gom đoạn cùng độ dài vào một micro-batch để ít đệm, rồi xáo thứ tự các batch
    model.train()
    t1, step, run = time.time(), 0, 0.0
    for _ in range(args.epochs):
        batches = [data[s : s + args.bs] for s in range(0, len(data), args.bs)]
        rng.shuffle(batches)
        for big in batches:
            for m in range(0, len(big), args.micro_bs):
                batch = collate([{"input_ids": x} for x in big[m : m + args.micro_bs]])
                with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                    loss = model(**{k: v.to(device) for k, v in batch.items()}).loss / accum
                scaler.scale(loss).backward()
                run += loss.item()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            opt.zero_grad()
            sched.step()
            step += 1
            if step % 100 == 0 or step == 20:
                el = time.time() - t1
                eta = el / step * (steps - step) / 60
                print(f"  bước {step}/{steps}: loss {run / min(step, 100):.3f}, còn ~{eta:.0f} phút", flush=True)
                if step % 100 == 0:
                    run = 0.0
    torch.manual_seed(SEED)
    after = mlm_loss(model, collate, held, args.micro_bs, device)
    minutes = round((time.time() - t0) / 60, 1)
    print(f"loss MLM giữ lại sau DAPT: {after:.3f} (perplexity {math.exp(after):.1f}); {minutes} phút", flush=True)
    model.save_pretrained(OUT)
    tok.save_pretrained(OUT)
    meta = {
        "base": BASE,
        "corpus": json.loads(CORPUS.with_suffix(".manifest.json").read_text("utf-8")),
        "train_chunks": len(data),
        "train_subwords": n_tok,
        "held_out_chunks": len(held),
        "params": {k: getattr(args, k) for k in ("max_len", "mlm_prob", "lr", "warmup", "bs", "micro_bs", "epochs")},
        "seed": SEED,
        "held_out_loss": {"before": round(before, 4), "after": round(after, 4)},
        "minutes": minutes,
        "hardware": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
    }
    (OUT / "dapt_manifest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    print(f"→ {OUT}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("corpus")
    c.add_argument("--csv", type=Path, default=CSV)
    c.add_argument("--workers", type=int, default=4)
    t = sub.add_parser("train")
    t.add_argument("--max-len", type=int, default=256)
    t.add_argument("--mlm-prob", type=float, default=0.15)
    t.add_argument("--lr", type=float, default=5e-5)
    t.add_argument("--warmup", type=float, default=0.06)
    t.add_argument("--bs", type=int, default=32, help="batch hiệu dụng")
    t.add_argument("--micro-bs", type=int, default=8, help="batch mỗi lần chạy GPU (tích lũy tới --bs)")
    t.add_argument("--epochs", type=int, default=1)
    t.add_argument("--held-out", type=int, default=500)
    t.add_argument("--max-chunks", type=int, default=None, help="lấy mẫu bớt nếu ước lượng > 4 giờ (ghi lại)")
    args = ap.parse_args()
    cmd_corpus(args) if args.cmd == "corpus" else cmd_train(args)


if __name__ == "__main__":
    main()
