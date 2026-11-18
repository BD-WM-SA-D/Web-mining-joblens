"""WM3 – học có giám sát trên tập dev đã gán, chọn mô hình bằng K-fold CV, chấm TEST một lần.

    uv run python -m absa.supervised cv --model tfidf          # chọn mô hình trên dev (out-of-fold)
    uv run python -m absa.supervised cv --model all            # so cả ba trên cùng các fold
    uv run python -m absa.supervised test --model tfidf        # chấm TEST, ghi experiments/runs/

**Vì sao không train trên nhãn yếu như WM2.** Nhãn yếu WM3 lấy cực tính từ điểm sao của review. Các
review nằm ngoài review của TEST (455 câu, 45 review) đều là review điểm cao, nên nhãn yếu trên đó
cho 367 cặp `positive` và **50 cặp `negative`**; nếu bỏ thêm các câu đã là dev gold (để dev còn sạch
cho việc chọn mô hình) thì còn **1 cặp `negative` trên 255 câu**. Không thể học nhận ra lời chê từ đó.
Tập gán tay (dev 200 câu, 207 cặp, 66 cặp `negative`) tuy nhỏ nhưng là nguồn duy nhất có lời chê.

**Cách chia.** Dev và TEST không chung review nào (kiểm tra lại trong `splits`). Chọn mô hình và tham
số **chỉ** bằng CV trên dev, sau đó mới chấm TEST một lần. Mỗi khía cạnh là một bài 4 lớp
`none/positive/neutral/negative`; `none` nghĩa là câu không nhắc khía cạnh đó (guideline mục 2).

Ba mô hình, cùng một tập train, cùng các fold:

| `--model` | Biểu diễn | Bộ phân loại |
|---|---|---|
| `tfidf` | TF-IDF từ (1-2 gram) + ký tự (3-5 gram) | hồi quy logistic, 6 bộ |
| `frozen` | PhoBERT-base-v2 **đóng băng**, lấy trung bình tầng cuối | hồi quy logistic, 6 bộ |
| `finetune` | PhoBERT-base-v2 fine-tune | 1 đầu ra 6×4, loss là tổng 6 cross-entropy |

Với 200 câu train, PhoBERT đóng băng + hồi quy logistic thường ăn fine-tune; có cả ba để nói được
điều đó bằng số chứ không phải phỏng đoán.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import time
from pathlib import Path

from absa.eval_dev import GOLD, SENTS, dev_set
from absa.lexicon import ASPECTS
from absa.lexicon import VERSION as DICT_VERSION
from absa.lexicon import is_advice, is_missing, match_aspects
from absa.lexicon import predict as dict_predict
from absa.lexicon import sentiment_counts
from absa.score import NONE, as_dict, fmt, report
from absa.weak_labels import VERSION as WEAK_VERSION
from absa.weak_labels import weak_label

ROOT = Path(__file__).resolve().parents[1]
TEST_GOLD = ROOT / "data" / "annotation" / "absa_test1.absa.jsonl"
MODELS = ROOT / "data" / "models"
SEG_CACHE = MODELS / "absa_seg_cache.json"
BASE = "vinai/phobert-base-v2"
LABELS = (NONE, "positive", "neutral", "negative")
L2I = {lab: i for i, lab in enumerate(LABELS)}
N_FOLDS = 5
MAX_LEN = 128


# ---------- dữ liệu ----------


def splits(gold_dev: list[Path], gold_test: Path, sents: Path) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """(dev rows, dev sents, test rows, test sents). Dừng nếu dev và test chung review."""
    drows, dsents, _ = dev_set(gold_dev, sents)
    trows, tsents, _ = dev_set([gold_test], sents)
    r_dev = {s["source_review_id"] for s in dsents}
    r_test = {s["source_review_id"] for s in tsents}
    if r_dev & r_test:
        raise SystemExit(f"dev và test chung {len(r_dev & r_test)} review – rò rỉ, dừng")
    ids_dev = {r["sentence_id"] for r in drows}
    if ids_dev & {r["sentence_id"] for r in trows}:
        raise SystemExit("dev và test chung câu – dừng")
    # gắn review vào từng câu để CV chia fold theo review (xem `folds`)
    for rows, sents_ in ((drows, dsents), (trows, tsents)):
        for r, s in zip(rows, sents_, strict=True):
            r["review_id"] = s["source_review_id"]
    return drows, dsents, trows, tsents


def targets(rows: list[dict]) -> list[list[int]]:
    """Mỗi câu → 6 số, một số một khía cạnh (0 = không nhắc tới)."""
    return [[L2I[r["gold"].get(a, NONE)] for a in ASPECTS] for r in rows]


def to_pred(y: list[int]) -> dict[str, str]:
    return {a: LABELS[v] for a, v in zip(ASPECTS, y, strict=True) if LABELS[v] != NONE}


def segment(texts: list[str]) -> list[str]:
    """Tách từ cho PhoBERT ("môi trường" → "môi_trường"), có cache vì underthesea khá chậm."""
    cache = json.loads(SEG_CACHE.read_text(encoding="utf-8")) if SEG_CACHE.exists() else {}
    missing = [t for t in texts if t not in cache]
    if missing:
        from underthesea import word_tokenize

        for t in missing:
            cache[t] = word_tokenize(t, format="text")
        MODELS.mkdir(parents=True, exist_ok=True)
        SEG_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return [cache[t] for t in texts]


# ---------- ba mô hình: fit trên (texts, Y) rồi dự đoán Y cho texts khác ----------


def fit_predict_tfidf(tr_texts, tr_y, te_texts, seed: int, **_) -> list[list[int]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_union

    vec = make_union(
        TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True),
        TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True),
    )
    xtr = vec.fit_transform(tr_texts)
    xte = vec.transform(te_texts)
    return _lr_per_aspect(xtr, tr_y, xte, seed, LogisticRegression)


def fit_predict_frozen(tr_texts, tr_y, te_texts, seed: int, **_) -> list[list[int]]:
    from sklearn.linear_model import LogisticRegression

    xtr = _embed(tr_texts)
    xte = _embed(te_texts)
    return _lr_per_aspect(xtr, tr_y, xte, seed, LogisticRegression)


def _lr_per_aspect(xtr, tr_y, xte, seed: int, LogisticRegression) -> list[list[int]]:
    """Một bộ phân loại 4 lớp cho mỗi khía cạnh. `class_weight='balanced'` vì ~80% ô là `none`."""
    out = [[0] * len(ASPECTS) for _ in range(xte.shape[0])]
    for j in range(len(ASPECTS)):
        y = [row[j] for row in tr_y]
        if len(set(y)) < 2:  # khía cạnh này trong fold chỉ có một lớp
            for i in range(xte.shape[0]):
                out[i][j] = y[0]
            continue
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
        clf.fit(xtr, y)
        for i, v in enumerate(clf.predict(xte)):
            out[i][j] = int(v)
    return out


def _embed(texts: list[str]):
    """Trung bình tầng cuối của PhoBERT đóng băng, có cache theo văn bản."""
    import numpy as np
    import torch
    from transformers import AutoModel, AutoTokenizer

    global _EMB_CACHE, _EMB_MODEL
    try:
        _EMB_CACHE
    except NameError:
        _EMB_CACHE = {}
        _EMB_MODEL = None
    missing = [t for t in dict.fromkeys(texts) if t not in _EMB_CACHE]
    if missing:
        if _EMB_MODEL is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            _EMB_MODEL = (
                AutoTokenizer.from_pretrained(BASE),
                AutoModel.from_pretrained(BASE).to(device).eval(),
                device,
            )
        tok, model, device = _EMB_MODEL
        seg = segment(missing)
        with torch.no_grad():
            for s in range(0, len(seg), 32):
                batch = seg[s : s + 32]
                enc = tok(batch, padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt").to(device)
                h = model(**enc).last_hidden_state
                m = enc["attention_mask"].unsqueeze(-1).float()
                vecs = ((h * m).sum(1) / m.sum(1)).cpu().numpy()
                for t, v in zip(missing[s : s + 32], vecs, strict=True):
                    _EMB_CACHE[t] = v
    return np.stack([_EMB_CACHE[t] for t in texts])


def fit_predict_finetune(tr_texts, tr_y, te_texts, seed: int, epochs: int = 8, lr: float = 3e-5, bs: int = 16, **_):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForSequenceClassification.from_pretrained(BASE, num_labels=len(ASPECTS) * len(LABELS)).to(device)

    # Lớp `none` chiếm ~80% ô. Không cân lại thì mô hình đoán `none` hết là đã được 0.8 độ chính xác.
    counts = [sum(1 for row in tr_y for j, v in enumerate(row) if v == k) for k in range(len(LABELS))]
    total = sum(counts)
    w = torch.tensor([total / (len(LABELS) * c) if c else 0.0 for c in counts], dtype=torch.float, device=device)
    lossf = torch.nn.CrossEntropyLoss(weight=w)

    def enc_batch(texts):
        return tok(segment(texts), padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")

    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps = epochs * ((len(tr_texts) + bs - 1) // bs)
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    rng = random.Random(seed)
    order = list(range(len(tr_texts)))
    for _ in range(epochs):
        model.train()
        rng.shuffle(order)
        for s in range(0, len(order), bs):
            idx = order[s : s + bs]
            batch = enc_batch([tr_texts[i] for i in idx]).to(device)
            y = torch.tensor([tr_y[i] for i in idx], device=device)
            logits = model(**batch).logits.view(len(idx), len(ASPECTS), len(LABELS))
            loss = lossf(logits.reshape(-1, len(LABELS)), y.reshape(-1))
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()

    model.eval()
    out = []
    with torch.no_grad():
        for s in range(0, len(te_texts), 32):
            batch = enc_batch(te_texts[s : s + 32]).to(device)
            logits = model(**batch).logits.view(-1, len(ASPECTS), len(LABELS))
            out += logits.argmax(-1).cpu().tolist()
    return out


# ---------- mô hình lai: khía cạnh lấy từ từ điển, chỉ CỰC là học ----------


def rule_feats(rows: list[dict]):
    """Tín hiệu của từ điển làm đặc trưng cho mô hình cực tính.

    Với 160 câu train, học lại từ đầu "từ nào là chê" là vô vọng – từ điển đã có 124 cụm cảm xúc.
    Đưa luôn các số của từ điển vào làm đặc trưng thì mô hình chỉ phải học **cách kết hợp** chúng
    (điều mà `match_polarity` đang làm bằng luật tay), chứ không phải học lại từ vựng.
    """
    import numpy as np

    out = []
    for r in rows:
        n_pos, n_neg = sentiment_counts(r["text"])
        out.append(
            [
                n_pos,
                n_neg,
                n_pos - n_neg,
                float(n_pos > 0 and n_neg > 0),  # câu hai chiều
                float(n_pos == 0 and n_neg == 0),  # không có từ cảm xúc nào
                float(is_advice(r["text"])),
                float(is_missing(r["text"])),
                float(r["section"] == "improvement"),
                float(r["section"] == "liked"),
                float(r["lang"] == "en"),
                min(len(r["text"]), 300) / 300,
            ]
        )
    return np.asarray(out, dtype=float)


def sentence_polarity(row: dict) -> str | None:
    """Cực của cả câu theo nhãn vàng: cực hay gặp nhất trong các cặp của câu.

    Baseline từ điển cũng chỉ cho **một** cực cho cả câu, nên mô hình lai học đúng bài đó để so được.
    Câu có hai khía cạnh trái cực nhau (hiếm: 5/200 câu dev, 3/348 câu TEST) là giới hạn của cả hai bên.
    """
    if not row["gold"]:
        return None
    return collections.Counter(row["gold"].values()).most_common(1)[0][0]


def fit_predict_hybrid(tr_rows, te_rows, seed: int, tfidf: bool = True, emb: bool = False, **_) -> list[dict]:
    import numpy as np
    import scipy.sparse as sp
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    tr = [r for r in tr_rows if sentence_polarity(r)]
    y = [sentence_polarity(r) for r in tr]
    blocks_tr, blocks_te = [rule_feats(tr)], [rule_feats(te_rows)]
    if emb:
        blocks_tr.append(_embed([r["text"] for r in tr]))
        blocks_te.append(_embed([r["text"] for r in te_rows]))
    xtr, xte = np.hstack(blocks_tr), np.hstack(blocks_te)
    if tfidf:
        vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)
        xtr = sp.hstack([vec.fit_transform([r["text"] for r in tr]), sp.csr_matrix(xtr)])
        xte = sp.hstack([vec.transform([r["text"] for r in te_rows]), sp.csr_matrix(xte)])
    clf = LogisticRegression(max_iter=5000, class_weight="balanced", random_state=seed).fit(xtr, y)
    pol = clf.predict(xte)
    return [dict.fromkeys(match_aspects(r["text"]), p) for r, p in zip(te_rows, pol, strict=True)]


def _slots_model(fn):
    """Bọc mô hình 6×4 (học cả khía cạnh lẫn cực) về cùng giao diện rows → [{aspect: polarity}]."""

    def run(tr_rows, te_rows, seed: int, **params):
        yhat = fn(
            [r["text"] for r in tr_rows],
            targets(tr_rows),
            [r["text"] for r in te_rows],
            seed=seed,
            **params,
        )
        return [to_pred(row) for row in yhat]

    return run


MODELS_FN = {
    "tfidf": _slots_model(fit_predict_tfidf),
    "frozen": _slots_model(fit_predict_frozen),
    "finetune": _slots_model(fit_predict_finetune),
    "hybrid": fit_predict_hybrid,
    "hybrid-rules": lambda *a, **k: fit_predict_hybrid(*a, **{**k, "tfidf": False}),
    "hybrid-emb": lambda *a, **k: fit_predict_hybrid(*a, **{**k, "tfidf": False, "emb": True}),
    "hybrid-all": lambda *a, **k: fit_predict_hybrid(*a, **{**k, "emb": True}),
}


# ---------- chọn mô hình và chấm ----------


def sel_score(rep: dict) -> float:
    """Một số để chọn mô hình: trung bình F1 khía cạnh và macro pos/neg theo ô.

    Chọn theo riêng macro pos/neg thì có thể lấy mô hình nhận khía cạnh rất tệ nhưng đoán cực đúng;
    chọn theo riêng F1 khía cạnh thì bỏ qua đúng phần đang yếu. Hai số đều có trong báo cáo.
    """
    return (rep["aspect"]["f1"] + rep["slot"]["macro_f1_2"]) / 2


def folds(groups: list[str], k: int, seed: int) -> list[list[int]]:
    """Chia K fold **theo review**: mọi câu của một review nằm cùng một fold.

    Bản cũ xáo theo câu, nên câu của cùng một review (chung điểm sao, văn phong, ô `section`) rơi cả vào
    train lẫn fold giữ lại – đúng loại rò rỉ đã chặn giữa dev và TEST trong `splits`. 200 câu dev đến từ
    45 review (4,4 câu/review). Đo lại thì số out-of-fold gần như không đổi (0,770 → 0,769, mô hình
    `hybrid`, 3 seed), nhưng cách chia theo review mới là cách đúng.
    """
    uniq = sorted(set(groups))
    random.Random(seed).shuffle(uniq)
    fold_of = {g: i % k for i, g in enumerate(uniq)}
    return [[i for i, g in enumerate(groups) if fold_of[g] == f] for f in range(k)]


def out_of_fold(name: str, rows: list[dict], seed: int, **params) -> list[dict]:
    """Dự đoán out-of-fold cho mọi câu dev: mỗi câu do mô hình **không** thấy nó dự đoán."""
    pred: list[dict | None] = [None] * len(rows)
    groups = [r.get("review_id") or r["sentence_id"] for r in rows]  # thiếu review thì mỗi câu một nhóm
    for fold in folds(groups, N_FOLDS, seed):
        held = set(fold)
        tr = [r for i, r in enumerate(rows) if i not in held]
        yhat = MODELS_FN[name](tr, [rows[i] for i in fold], seed=seed, **params)
        for i, p in zip(fold, yhat, strict=True):
            pred[i] = p
    return [p or {} for p in pred]


def table(runs: list[tuple[str, dict]]) -> str:
    lines = [
        "\n| Hệ | Khía cạnh F1 | Theo ô, 3 lớp | Theo ô, chỉ pos/neg | R negative | P negative | điểm chọn |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, rep in runs:
        s = rep["slot"]
        neg = s["per_class"]["negative"]
        lines.append(
            f"| {name} | {rep['aspect']['f1']:.3f} | {s['macro_f1_3']:.3f} | {s['macro_f1_2']:.3f} |"
            f" {neg['r']:.3f} | {neg['p']:.3f} | {sel_score(rep):.3f} |"
        )
    return "\n".join(lines)


def section_rule(rows: list[dict]) -> list[dict]:
    """Mốc tầm thường quan trọng nhất: khía cạnh của từ điển, cực tính chỉ theo phần của review.

    Form ITviec tách sẵn "Điều tôi thích" / "Đề nghị cải thiện", và trên TEST 83/127 ô ở phần cải
    thiện là `negative` còn ở phần kia chỉ 7/201. Luật một dòng này được 0,583 trên TEST, gần bằng
    mô hình lai (0,590, p = 0,264) – nên mọi kết quả WM3 phải so với nó, không chỉ so với từ điển.
    """
    return [
        dict.fromkeys(match_aspects(r["text"]), "negative" if r["section"] == "improvement" else "positive")
        for r in rows
    ]


def refs(rows: list[dict], sents: list[dict]) -> list[tuple[str, dict]]:
    """Ba mốc so sánh có sẵn: từ điển, nhãn yếu, và luật theo phần của review."""
    gold = [r["gold"] for r in rows]
    return [
        (f"từ điển {DICT_VERSION}", report(gold, [as_dict(dict_predict(r["text"])) for r in rows])),
        (f"nhãn yếu {WEAK_VERSION}", report(gold, [as_dict(weak_label(s)) for s in sents])),
        ("luật phần review", report(gold, section_rule(rows))),
    ]


def cmd_cv(args) -> None:
    drows, dsents, trows, _ = splits(args.gold, args.test_gold, args.sentences)
    print(f"dev {len(drows)} câu / {sum(len(r['gold']) for r in drows)} cặp;  TEST {len(trows)} câu (chưa chạm)")
    gold = [r["gold"] for r in drows]
    names = list(MODELS_FN) if args.model == "all" else [args.model]
    runs = refs(drows, dsents)
    for name in names:
        extra = {"epochs": args.epochs} if name == "finetune" else {}
        t0 = time.time()
        rep = report(gold, out_of_fold(name, drows, args.seed, **extra))
        tag = f"{name}" + (f" (epochs={args.epochs})" if extra else "")
        print(f"\n{fmt(f'{tag} – out-of-fold {N_FOLDS} fold, {round(time.time() - t0)}s', rep)}")
        runs.append((tag, rep))
    print(table(runs))


def cmd_test(args) -> None:
    from experiments.runlog import ids_sha256, save_run

    drows, dsents, trows, tsents = splits(args.gold, args.test_gold, args.sentences)
    extra = {"epochs": args.epochs} if args.model == "finetune" else {}
    t0 = time.time()
    pred = MODELS_FN[args.model](drows, trows, seed=args.seed, **extra)
    minutes = round((time.time() - t0) / 60, 2)
    gold = [r["gold"] for r in trows]
    rep = report(gold, pred)
    name = args.model + (f"-ep{args.epochs}" if extra else "")
    print(f"train trên {len(drows)} câu dev, chấm {len(trows)} câu TEST ({minutes} phút)")
    print("\n" + fmt(f"{name} trên TEST", rep))
    print(table([*refs(trows, tsents), (name, rep)]))
    path = save_run(
        task="WM3",
        rq="RQ3",
        method=f"absa-{name}",
        baseline_of=DICT_VERSION,
        eval_set="absa_test1",
        split="test",
        metrics={
            "aspect_f1_micro": round(rep["aspect"]["f1"], 4),
            "sentiment_f1_macro": round(rep["slot"]["macro_f1_2"], 4),
        },
        ids=[r["sentence_id"] for r in trows],
        n_gold=sum(len(g) for g in gold),
        seed=args.seed,
        train={"data": "absa_dev_gold", "n_items": len(drows), "params": extra or {"class_weight": "balanced"}},
        runtime={"minutes": minutes},
        command=f"uv run python -m absa.supervised test --model {args.model}",
    )
    print(f"\nghi {path.name} (ids_sha256 {ids_sha256([r['sentence_id'] for r in trows])[:12]}…)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("cv", "test"))
    ap.add_argument("--model", default="all", choices=(*MODELS_FN, "all"))
    ap.add_argument("--epochs", type=int, default=8, help="chỉ cho --model finetune")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--gold", type=Path, nargs="+", default=GOLD)
    ap.add_argument("--test-gold", type=Path, default=TEST_GOLD)
    ap.add_argument("--sentences", type=Path, default=SENTS)
    args = ap.parse_args()
    if args.cmd == "cv":
        cmd_cv(args)
    else:
        if args.model == "all":
            raise SystemExit("--model all chỉ dùng cho `cv`; chấm TEST thì chọn đúng một mô hình")
        cmd_test(args)


if __name__ == "__main__":
    main()
