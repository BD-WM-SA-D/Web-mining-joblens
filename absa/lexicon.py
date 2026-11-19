"""WM3 baseline – từ điển khía cạnh và từ điển cảm xúc (so khớp theo cụm từ).

Baseline bắt buộc phải báo cáo trước khi so với PhoBERT (AGENTS.md, "Ghi nguồn số liệu").

Cách làm: với mỗi câu, tìm **cụm từ** của từ điển khía cạnh xuất hiện trong câu (so khớp
theo biên từ, cụm dài được ưu tiên) → tập khía cạnh. Cực tính lấy theo số từ cảm xúc tích cực
trừ số từ tiêu cực, có xử lý **phủ định** ("không tốt", "not good") bằng cách đảo dấu khi
trước từ cảm xúc ≤ NEG_WINDOW từ có từ phủ định.

Từ điển viết tay từ 144 review công khai, có cả tiếng Việt và tiếng Anh. Đây là *baseline*:
nó mù với câu nói vòng ("lương chỉ bằng một nửa thị trường") – đó là lý do cần mô hình học.
"""

from __future__ import annotations

import csv
import functools
import re
import unicodedata
from pathlib import Path

VERSION = "absa-dict"  # bản cơ bản chỉ đếm từ cảm xúc; bản mở rộng thêm bảng 2c + luật đề nghị; bản đủ luật thêm luật "không có" và luật hòa
RES = Path(__file__).parent / "resources"
ASPECTS = (
    "salary_benefits",
    "training_learning",
    "management_care",
    "culture_fun",
    "office_workspace",
    "work_life_balance",
)
POLARITIES = ("positive", "negative", "neutral")
NEGATORS = frozenset("không chưa chẳng chả đừng kém thiếu no not never lacks lack without".split())
NEG_WINDOW = 3  # số từ trước từ cảm xúc còn tính là phủ định

ADVICE_NEG_WINDOW = 5  # "không có gì cần cải thiện cả": phủ định cách "cải thiện" 4 từ

# Dấu hiệu "đang đề nghị công ty sửa gì" (guideline luật 9: đề nghị = chê). Cố ý KHÔNG có "thêm" và
# "bổ sung" đứng một mình: chúng xuất hiện cả trong câu khen ("có thêm nhiều phúc lợi nhỏ").
ADVICE_TERMS = sorted(
    (
        ("advice", t)
        for t in (
            # "nên" nhập nhằng: vừa là "should" vừa là "vì thế" ("việc nhiều nên phải OT"). Giữ vì trên
            # tập dev nó đúng nhiều hơn sai, nhưng đây là nguồn lỗi đã biết, ghi vào phân tích lỗi.
            "nên",
            "cần",
            "mong",
            "hy vọng",
            "hi vọng",
            "đề nghị",
            "góp ý",
            "cải thiện",
            "cải tiến",
            "nâng cấp",
            "xem lại",
            "cân nhắc",
            "should",
            "shoud",
            # "need to"/"needs to" đứng một mình quá rộng: khớp cả "Rarely need to do OT" (là khen).
            "needs to be",
            "need to be",
            "could be better",
            "could be",
            "would be better",
            "would help",
            "sẽ giúp",
            "tuyệt vời hơn",
            "hope",
            "wish",
            "improve",
            "improvement",
            "more transparent",
        )
    ),
    key=lambda r: -len(r[1]),
)

# "cải thiện" cũng xuất hiện trong câu khen ("luôn được học hỏi và cải thiện kỹ năng", "công ty cố
# gắng cải thiện"). Những từ này đứng ngay trước thì đó không phải lời đề nghị.
ADVICE_NOT = frozenset("được giúp đã luôn cố đang tự muốn để và".split())
ADVICE_NOT_WINDOW = 3

# Dấu hiệu "thứ này không có": "Không có company trip", "Chưa có chế độ làm việc online".
# "không có **gì** để chê" là khen, không phải thiếu thứ gì – chặn bằng lookahead.
MISSING_RE = re.compile(r"(?:không|chưa|chẳng)\s+(?:có|được|đủ)\s+(?!gì|nhiều)|(?:^|\s)(?:no|without)\s")
WS_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def norm(text: str) -> str:
    """NFC + chữ thường + gộp khoảng trắng; giữ dấu tiếng Việt (bỏ dấu sẽ nhập nhằng)."""
    return WS_RE.sub(" ", unicodedata.normalize("NFC", text or "").lower()).strip()


def _load(path: Path, key: str) -> list[tuple[str, str]]:
    with path.open(encoding="utf-8") as f:
        rows = [(r[key], norm(r["term"])) for r in csv.DictReader(f) if r.get("term")]
    # cụm dài trước: "work life balance" phải khớp trước "balance"
    return sorted(rows, key=lambda r: -len(r[1]))


@functools.cache
def aspect_terms() -> list[tuple[str, str]]:
    return _load(RES / "aspect_lexicon.csv", "aspect")


@functools.cache
def sentiment_terms() -> list[tuple[str, str]]:
    return _load(RES / "sentiment_lexicon.csv", "polarity")


def _hits(text: str, terms: list[tuple[str, str]]) -> list[tuple[str, int]]:
    """Các (label, vị trí ký tự) khớp theo biên từ; vùng đã khớp bị che để cụm ngắn không khớp lại."""
    s = norm(text)
    taken = bytearray(len(s))
    out = []
    for label, term in terms:
        for m in re.finditer(rf"(?<![^\W_]){re.escape(term)}(?![^\W_])", s):
            if any(taken[m.start() : m.end()]):
                continue
            taken[m.start() : m.end()] = b"\x01" * (m.end() - m.start())
            out.append((label, m.start()))
    return out


def match_aspects(text: str) -> list[str]:
    """Các khía cạnh câu nói tới, theo thứ tự xuất hiện. Rỗng = baseline không nhận ra."""
    seen, out = set(), []
    for label, _ in sorted(_hits(text, aspect_terms()), key=lambda h: h[1]):
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def _negated(words: list[str], char_pos: int, s: str, window: int = NEG_WINDOW) -> bool:
    """Có từ phủ định trong `window` từ ngay trước vị trí này?"""
    before = WORD_RE.findall(s[:char_pos])
    return any(w in NEGATORS for w in before[-window:])


def is_advice(text: str) -> bool:
    """Câu có đang đề nghị công ty sửa gì không (và lời đề nghị đó không bị phủ định)?

    Lý do có hàm này: trên tập dev, 12/25 lỗi cực tính của từ điển là câu chê bằng cách đề nghị –
    "Cần chú ý thêm chế độ thưởng OT", "Công ty nên mua thêm máy", "Cải thiện cơ sở vật chất" – không
    chứa một từ cảm xúc xấu nào nên từ điển chấm `neutral`. Guideline mục 2 luật 9: đề nghị = chê.

    Phủ định phải kiểm: "Không có gì cần cải thiện cả" là khen, không phải đề nghị.
    """
    s = norm(text)
    words = WORD_RE.findall(s)
    for _, pos in _hits(text, ADVICE_TERMS):
        if _negated(words, pos, s, ADVICE_NEG_WINDOW):
            continue
        if any(w in ADVICE_NOT for w in WORD_RE.findall(s[:pos])[-ADVICE_NOT_WINDOW:]):
            continue
        return True
    return False


def is_missing(text: str) -> bool:
    """Câu có dạng "không có / chưa có <thứ gì đó của công ty>" không?

    "Không có company trip", "Không có lương OT", "Chưa có chế độ làm việc online" đều là chê, nhưng
    không chứa từ cảm xúc nào nên từ điển cũ chấm `neutral`. Yêu cầu câu phải nói tới ít nhất một
    khía cạnh, để "Không có gì để chê" không bị hiểu nhầm.
    """
    return bool(MISSING_RE.search(norm(text))) and bool(match_aspects(text))


def sentiment_counts(text: str) -> tuple[int, int]:
    """(số từ khen, số từ chê) sau khi đã đảo dấu theo phủ định.

    `match_polarity` nén hai số này thành một nhãn. Mô hình học cực tính (`absa/supervised.py`) cần
    chính hai số đó làm đặc trưng, nên tách ra đây thay vì tính lại bằng cách khác.
    """
    s = norm(text)
    words = WORD_RE.findall(s)
    n_pos = n_neg = 0
    for label, pos in _hits(text, sentiment_terms()):
        positive = label == "positive"
        if _negated(words, pos, s):
            positive = not positive
        if positive:
            n_pos += 1
        else:
            n_neg += 1
    return n_pos, n_neg


def match_polarity(text: str, advice: bool = True, missing: bool = True, tie: bool = True) -> str:
    """'positive' / 'negative' / 'neutral' theo đếm từ cảm xúc, có đảo dấu khi bị phủ định.

    Ba luật thêm, bật/tắt được để báo cáo đóng góp của từng cái (`absa/eval_dev.py`):

    - `advice`: câu đề nghị sửa thì là `negative`, kể cả khi có từ khen
      ("Lương ổn nhưng mong công ty xem lại chế độ OT").
    - `missing`: "không có / chưa có <khía cạnh>" là `negative` dù không có từ cảm xúc nào.
    - `tie`: câu có từ cảm xúc cả hai phía, trừ nhau bằng 0 thì lấy `negative` chứ không lấy
      `neutral`. "Great environment, but unfair performance review" là một lời chê; `neutral` dành
      cho câu **không đánh giá gì**, không phải câu đánh giá hai chiều (guideline mục 2d).

    Tắt cả ba là baseline từ điển cơ bản (chỉ đếm từ cảm xúc).
    """
    s = norm(text)
    words = WORD_RE.findall(s)
    score = n_hits = 0
    for label, pos in _hits(text, sentiment_terms()):
        sign = 1 if label == "positive" else -1
        if _negated(words, pos, s):
            sign = -sign
        score += sign
        n_hits += 1
    if advice and is_advice(text):
        return "negative"
    if missing and is_missing(text):
        return "negative"
    if tie and n_hits and score == 0:
        return "negative"
    return "positive" if score > 0 else "negative" if score < 0 else "neutral"


def predict(text: str, **opts) -> list[dict]:
    """Baseline WM3: câu → danh sách {aspect, polarity}. Cực tính dùng chung cho mọi khía cạnh
    trong câu (baseline không tách được cực tính riêng từng khía cạnh).

    `opts` chuyển thẳng cho `match_polarity` (`advice`, `missing`, `tie`).
    """
    polarity = match_polarity(text, **opts)
    return [{"aspect": a, "polarity": polarity} for a in match_aspects(text)]
