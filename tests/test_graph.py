"""WM6 – đồ thị đồng xuất hiện kỹ năng: đếm cạnh, NPMI, lọc cạnh, chia nửa."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from graph.analyze import halves, labels, louvain, prune_npmi
from graph.build import cooccurrence, from_json, spans_to_labels, to_json


def jobs(*skill_sets: set[str]) -> dict[str, set[str]]:
    return {f"job{i}": s for i, s in enumerate(skill_sets)}


def test_trong_so_canh_la_so_tin_chua_ca_hai():
    g = cooccurrence(jobs({"A", "B"}, {"A", "B"}, {"A", "C"}), min_df=1, min_weight=1)
    assert g["A"]["B"]["weight"] == 2
    assert g["A"]["C"]["weight"] == 1
    assert not g.has_edge("B", "C")


def test_npmi_bang_1_khi_hai_ky_nang_luon_di_cung_nhau():
    """Hai kỹ năng xuất hiện đúng cùng một tập tin → NPMI = 1 (gắn bó hoàn toàn)."""
    g = cooccurrence(jobs({"A", "B"}, {"A", "B"}, {"C", "D"}), min_df=1, min_weight=1)
    assert g["A"]["B"]["npmi"] == pytest.approx(1.0, abs=1e-6)


def test_npmi_am_khi_hai_ky_nang_pho_bien_it_gap_nhau():
    """A và B đều có mặt 3/4 tin nhưng chỉ gặp nhau 2/4 → ít hơn mức ngẫu nhiên, NPMI < 0."""
    g = cooccurrence(
        jobs({"A", "B"}, {"A", "B"}, {"A", "X"}, {"B", "X"}),
        min_df=1,
        min_weight=1,
    )
    assert g["A"]["B"]["npmi"] < 0


def test_loc_ky_nang_it_tin_va_canh_yeu():
    g = cooccurrence(jobs({"A", "B", "R"}, {"A", "B"}, {"A", "B"}), min_df=2, min_weight=3)
    assert set(g) == {"A", "B"}  # R chỉ 1 tin → bỏ
    g2 = cooccurrence(jobs({"A", "B"}, {"A", "C"}, {"A", "C"}), min_df=1, min_weight=2)
    assert not g2.has_edge("A", "B")  # cạnh chỉ 1 tin → bỏ


def test_dinh_tro_troi_bi_bo():
    g = cooccurrence(jobs({"A", "B"}, {"A", "B"}, {"Z"}, {"Z"}), min_df=2, min_weight=2)
    assert "Z" not in g  # đủ số tin nhưng không có cạnh nào


def test_prune_npmi_bo_canh_yeu_va_dinh_con_lai_tro_troi():
    g = cooccurrence(jobs({"A", "B"}, {"A", "B"}, {"C", "D"}, {"C", "D"}), min_df=1, min_weight=1)
    g.add_edge("A", "C", weight=1, npmi=-0.5)
    h = prune_npmi(g, 0.0)
    assert not h.has_edge("A", "C")
    assert h.has_edge("A", "B") and h.has_edge("C", "D")
    assert h.graph["n_jobs"] == g.graph["n_jobs"]


def test_json_di_ve_khong_mat_gi():
    g = cooccurrence(jobs({"A", "B"}, {"A", "B", "C"}), min_df=1, min_weight=1)
    h = from_json(to_json(g))
    assert set(h) == set(g)
    assert h["A"]["B"] == g["A"]["B"]
    assert h.nodes["A"]["df"] == g.nodes["A"]["df"]


def test_span_bio_doi_thanh_nhan_canonical():
    class Catalog:
        def lookup(self, form):
            table = {"reactjs": type("S", (), {"label": "ReactJS"})()}
            return table.get(form.lower())

    tokens = ["Yêu", "cầu", "ReactJS", "và", "Khong", "Co"]
    tags = ["O", "O", "B-SKILL", "O", "B-SKILL", "I-SKILL"]
    assert spans_to_labels(tokens, tags, Catalog()) == {"ReactJS"}  # span lạ bị bỏ


def test_chia_nua_theo_nguon():
    df = pd.DataFrame(
        [
            {"source": "topcv", "date_posted": "2026-01-01"},
            {"source": "itviec", "date_posted": "2026-02-01"},
            {"source": "itviec", "date_posted": "2026-03-01"},
        ]
    )
    a, b = halves(df, "source", seed=1)
    assert set(a["source"]) == {"topcv"} and set(b["source"]) == {"itviec"}


def test_chia_nua_theo_thoi_gian_giu_dung_thu_tu():
    df = pd.DataFrame([{"source": "x", "date_posted": d} for d in ["2026-03-01", "2026-01-01", "2026-02-01"]])
    a, b = halves(df, "time", seed=1)
    assert list(a["date_posted"]) == ["2026-01-01"]
    assert list(b["date_posted"]) == ["2026-02-01", "2026-03-01"]


def test_louvain_tach_duoc_hai_khoi_roi_nhau():
    g = cooccurrence(jobs({"A", "B"}, {"A", "B"}, {"C", "D"}, {"C", "D"}), min_df=1, min_weight=2)
    parts = louvain(g, "weight", 1.0, 1)
    assert len(parts) == 2
    assert len(set(labels(g, parts))) == 2
    assert math.isclose(sum(len(p) for p in parts), 4)


def test_npmi_bang_0_khi_ca_hai_ky_nang_co_trong_moi_tin():
    """Trường hợp p(u,v) = 1: PMI = 0 và mẫu số -log p = 0. Giới hạn đặt là 0, không được chia cho 0."""
    g = cooccurrence(jobs({"A", "B"}, {"A", "B"}), min_df=1, min_weight=1)
    assert g["A"]["B"]["npmi"] == 0.0


def test_toa_do_duoc_chuan_hoa_ve_0_1_va_lap_lai_duoc():
    from graph.export_viz import layout

    g = cooccurrence(jobs({"A", "B"}, {"A", "B"}, {"C", "D"}, {"C", "D"}), min_df=1, min_weight=1)
    pos = layout(g, seed=1)
    assert set(pos) == set(g)
    xs = [p[0] for p in pos.values()]
    assert min(xs) == 0.0 and max(xs) == 1.0
    assert layout(g, seed=1) == pos  # cùng seed thì cùng hình


def test_cum_duoc_danh_so_theo_kich_thuoc_giam_dan():
    from graph.export_viz import export, layout

    g = cooccurrence(
        jobs({"A", "B", "C"}, {"A", "B", "C"}, {"X", "Y"}, {"X", "Y"}),
        min_df=1,
        min_weight=2,
    )
    parts = louvain(g, "weight", 1.0, 1)
    out = export(g, parts, layout(g))
    sizes = [c["size"] for c in out["communities"]]
    assert sizes == sorted(sizes, reverse=True)
    assert [c["id"] for c in out["communities"]] == list(range(len(sizes)))
    big = out["communities"][0]
    assert {n["community"] for n in out["nodes"] if n["skill"] in big["top"]} == {0}


# ---------- gợi ý kỹ năng (graph/recommend.py) ----------


def two_clusters():
    from graph.recommend import pos_weight

    g = cooccurrence(
        jobs(
            {"A", "B", "C"},
            {"A", "B", "C"},
            {"A", "B", "C"},
            {"X", "Y", "Z"},
            {"X", "Y", "Z"},
            {"X", "Y", "Z"},
        ),
        min_df=1,
        min_weight=2,
    )
    return pos_weight(g)


def test_trong_so_am_duoc_ha_ve_gan_0_chu_khong_bi_bo():
    from graph.recommend import pos_weight

    g = cooccurrence(jobs({"A", "B"}, {"A", "B"}), min_df=1, min_weight=1)
    g["A"]["B"]["npmi"] = -0.4
    h = pos_weight(g)
    assert h.has_edge("A", "B")
    assert h["A"]["B"]["w"] == 0.001


def test_goi_y_khong_tra_lai_ky_nang_da_co_trong_ho_so():
    from graph.recommend import rank_count, rank_popular, rank_ppr

    g = two_clusters()
    for fn in (rank_popular, rank_count, rank_ppr):
        out = fn(g, {"A", "B"})
        assert "A" not in out and "B" not in out


def test_pagerank_ca_nhan_hoa_uu_tien_cum_cua_ho_so():
    from graph.recommend import rank_ppr

    g = two_clusters()
    assert rank_ppr(g, {"A", "B"})[0] == "C"
    assert rank_ppr(g, {"X", "Y"})[0] == "Z"


def test_che_mot_ky_nang_va_bo_tin_qua_it_ky_nang():
    from graph.recommend import build_cases

    vocab = {"A", "B", "C", "D"}
    cases = build_cases([{"A", "B", "C", "D"}, {"A", "B"}], vocab, seed=1)
    assert len(cases) == 1  # tin hai kỹ năng bị bỏ
    profile, held = cases[0]
    assert held in vocab
    assert held not in profile
    assert profile | {held} == vocab


def test_ky_nang_ngoai_do_thi_khong_bao_gio_bi_che():
    from graph.recommend import build_cases

    cases = build_cases([{"A", "B", "C", "D", "LaHoac"}] * 6, {"A", "B", "C", "D"}, seed=3)
    assert all(held != "LaHoac" for _, held in cases)


def test_build_cases_giu_ma_tin_va_cung_ca_voi_ban_khong_ma():
    from graph.recommend import build_cases, build_cases_ids

    jobs_ = [{"A", "B", "C", "D"}, {"A", "B"}, {"B", "C", "D", "E"}]
    vocab = {"A", "B", "C", "D", "E"}
    plain = build_cases(jobs_, vocab, seed=7)
    with_ids = build_cases_ids([(f"j{i}", s) for i, s in enumerate(jobs_)], vocab, seed=7)
    assert [(p, h) for _, p, h in with_ids] == plain
    assert [u for u, _, _ in with_ids] == ["j0", "j2"]
