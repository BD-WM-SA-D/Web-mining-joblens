"""Chấm WM3: nhận diện khía cạnh (P/R/F1) và cảm xúc (macro-F1). Không phụ thuộc Label Studio.

Quy ước nhãn của một câu: dict {aspect: polarity}. Khía cạnh **không có** trong dict nghĩa là câu
không nhắc tới nó – KHÔNG phải `neutral`. Đây là quy ước của guideline mục 2, giữ nguyên ở đây để
đừng biến "để trống" thành một lớp cảm xúc.

Ba con số báo cáo, vì một con số không nói được mô hình sai ở đâu:
  aspect   P/R/F1 trên tập khía cạnh mỗi câu – mô hình có tìm đúng khía cạnh không
  polarity macro-F1 trên các khía cạnh *cả hai* bên đều tìm ra – tìm đúng rồi thì đoán đúng thái độ không
  slot     macro-F1 3 lớp trên từng ô (câu × 6 khía cạnh), ô không nhắc tới = `none` – số tổng hợp
"""

from __future__ import annotations

from absa.lexicon import ASPECTS, POLARITIES

NONE = "none"


def as_dict(items: list[dict]) -> dict[str, str]:
    """Đổi [{aspect, polarity}] (dạng trả về của `predict`/`weak_label`) sang {aspect: polarity}."""
    return {d["aspect"]: d["polarity"] for d in items}


def prf(gold: list[set], pred: list[set]) -> dict:
    """gold, pred: hai list song song các tập hợp. Trả về precision/recall/F1 vi mô."""
    tp = sum(len(g & p) for g, p in zip(gold, pred, strict=True))
    n_pred = sum(len(p) for p in pred)
    n_gold = sum(len(g) for g in gold)
    p = tp / n_pred if n_pred else 0.0
    r = tp / n_gold if n_gold else 0.0
    return {
        "p": p,
        "r": r,
        "f1": 2 * p * r / (p + r) if p + r else 0.0,
        "tp": tp,
        "n_pred": n_pred,
        "n_gold": n_gold,
    }


def per_class(y_true: list[str], y_pred: list[str], labels: tuple[str, ...]) -> dict:
    out = {}
    for lab in labels:
        tp = fp = fn = 0
        for t, p in zip(y_true, y_pred, strict=True):
            if t == lab and p == lab:
                tp += 1
            elif p == lab:
                fp += 1
            elif t == lab:
                fn += 1
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        out[lab] = {
            "p": prec,
            "r": rec,
            "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "support": tp + fn,
        }
    return out


def macro_f1(y_true: list[str], y_pred: list[str], labels: tuple[str, ...] = POLARITIES) -> tuple[float, dict]:
    """Macro-F1 lấy trung bình trên `labels`. Lớp không xuất hiện vẫn tính F1 = 0, không bỏ qua:
    bỏ qua thì mô hình chỉ đoán toàn `positive` lại được điểm cao."""
    per = per_class(y_true, y_pred, labels)
    return sum(v["f1"] for v in per.values()) / len(labels), per


def slots(gold: list[dict], pred: list[dict]) -> tuple[list[str], list[str]]:
    """Mở mỗi câu thành 6 ô (một ô một khía cạnh), ô không nhắc tới mang nhãn `none`."""
    y_true, y_pred = [], []
    for g, p in zip(gold, pred, strict=True):
        for a in ASPECTS:
            y_true.append(g.get(a, NONE))
            y_pred.append(p.get(a, NONE))
    return y_true, y_pred


def report(gold: list[dict], pred: list[dict]) -> dict:
    """Ba nhóm số liệu cho một cặp (nhãn vàng, dự đoán) trên cùng danh sách câu."""
    aspect = prf([set(g) for g in gold], [set(p) for p in pred])

    pol_true, pol_pred = [], []
    for g, p in zip(gold, pred, strict=True):
        for a in set(g) & set(p):
            pol_true.append(g[a])
            pol_pred.append(p[a])
    pol_macro, pol_per = macro_f1(pol_true, pol_pred)

    slot_true, slot_pred = slots(gold, pred)
    slot_macro, slot_per = macro_f1(slot_true, slot_pred)
    slot_4 = per_class(slot_true, slot_pred, (NONE, *POLARITIES))
    # `neutral` rất hiếm ở mức câu (1-2 mẫu / 57 câu) nên macro-F1 3 lớp bị một lớp tí xíu kéo lệch.
    # Báo cáo thêm macro-F1 chỉ trên positive/negative, kèm support, để số đọc được. Không thay thế
    # số 3 lớp: contract silver.review_aspects vẫn có ba giá trị.
    slot_macro_2 = (slot_4["positive"]["f1"] + slot_4["negative"]["f1"]) / 2

    return {
        "n_sentences": len(gold),
        "aspect": aspect,
        "polarity_on_matched": {"macro_f1": pol_macro, "n": len(pol_true), "per_class": pol_per},
        "slot": {"macro_f1_3": slot_macro, "macro_f1_2": slot_macro_2, "per_class": slot_4, "per_class_3": slot_per},
    }


def fmt(name: str, rep: dict) -> str:
    a, s = rep["aspect"], rep["slot"]
    pol = rep["polarity_on_matched"]
    lines = [
        f"== {name} ({rep['n_sentences']} câu)",
        f"   khía cạnh : P {a['p']:.3f}  R {a['r']:.3f}  F1 {a['f1']:.3f}"
        f"   (đúng {a['tp']}, dự đoán {a['n_pred']}, vàng {a['n_gold']})",
        f"   cảm xúc   : macro-F1 {pol['macro_f1']:.3f} trên {pol['n']} khía cạnh trùng nhau",
        f"   tổng hợp  : macro-F1 theo ô – 3 lớp {s['macro_f1_3']:.3f}" f"   |  chỉ pos/neg {s['macro_f1_2']:.3f}",
    ]
    for lab, v in s["per_class"].items():
        lines.append(f"     {lab:<9} P {v['p']:.3f}  R {v['r']:.3f}  F1 {v['f1']:.3f}  (vàng {v['support']})")
    return "\n".join(lines)
