"""Test các job batch/ (image mô hình theo ADR 0001 D3) và producer Kafka – không cần cụm, không cần model."""

import json

import pytest

from batch import absa_scorer, job_dedup, skill_extractor
from batch.tables import harmonize, read_file, write_file
from crawler import producer
from crawler.common import job_message, review_message

JOBS = [
    {
        "job_uid": "a",
        "source": "topcv",
        "title": "Backend Developer (Java)",
        "company_name": "Công ty TNHH ABC",
        "description": "Phát triển API bằng Java và Spring Boot.\nLàm việc với PostgreSQL.",
        "requirements_text": "Có kinh nghiệm Docker, Kubernetes.",
        "skill_tags": ["Java", "Spring Boot"],
        "date_posted": "2026-11-01",
    },
    {  # trùng a: cùng tiêu đề sau khi bỏ "Hà Nội", cùng công ty
        "job_uid": "b",
        "source": "itviec",
        "title": "Backend Developer (Java) - Hà Nội",
        "company_name": "ABC Company Limited",
        "description": "Phát triển API bằng Java và Spring Boot.\nLàm việc với PostgreSQL.",
        "requirements_text": "Có kinh nghiệm Docker, Kubernetes.",
        "skill_tags": [],
        "date_posted": "2026-11-05",
    },
    {
        "job_uid": "c",
        "source": "topcv",
        "title": "Kế toán tổng hợp",
        "company_name": "Công ty XYZ",
        "description": "Lập báo cáo tài chính, quyết toán thuế.",
        "requirements_text": "Thành thạo Excel.",
        "skill_tags": None,
        "date_posted": None,
    },
]


def test_harmonize_fills_both_names():
    r = harmonize([{"requirements_text": "x", "date_posted": "d"}])[0]
    assert r["requirements"] == "x" and r["posted_date"] == "d"


def test_skill_extractor_stub_spans_match_text():
    jobs = harmonize([dict(j) for j in JOBS])
    rows = skill_extractor.extract(jobs, stub=True, run_id="t")
    assert rows, "từ điển phải bắt được Java/Docker"
    by_uid = {j["job_uid"]: j for j in jobs}
    for r in rows:
        if r["field"] == "skill_tags":
            assert r["span_end"] == r["span_start"] + 1
        else:
            assert by_uid[r["job_uid"]][r["field"]][r["span_start"] : r["span_end"]] == r["surface_form"]
        assert r["extractor_version"].endswith("-stub") and r["run_id"] == "t"
    keys = [(r["job_uid"], r["field"], r["span_start"], r["span_end"]) for r in rows]
    assert len(keys) == len(set(keys)), "khóa chính không được trùng"
    assert {"Java", "Docker"} <= {r["surface_form"] for r in rows}


def test_bio_spans_to_chars():
    toks = [(0, 4), (5, 9), (10, 13)]
    assert skill_extractor.bio_spans(toks, ["B-SKILL", "I-SKILL", "O"]) == [(0, 9)]
    assert skill_extractor.bio_spans(toks, ["I-SKILL", "O", "B-SKILL"]) == [(0, 4), (10, 13)]


@pytest.mark.parametrize("stub", [True, False])
def test_dedup_groups(stub):
    rows = job_dedup.dedup(harmonize([dict(j) for j in JOBS]), stub=stub, run_id="t")
    group = {r["job_uid"]: r["dup_group_id"] for r in rows}
    assert len(rows) == len(JOBS), "mỗi tin đúng một dòng"
    assert group["c"] == "c"
    if not stub:  # khóa mềm bỏ "- Hà Nội" nên gộp được a và b; đại diện là tin đăng sớm hơn
        assert group["a"] == group["b"] == "a"
        score = {r["job_uid"]: r["score"] for r in rows}
        assert score["a"] is None and 0.5 < score["b"] <= 1.0  # tiêu đề lệch "- Hà Nội" nên chưa tới 1
    else:  # khóa chính xác: hai tiêu đề khác nhau nên không gộp
        assert group["b"] == "b"


def test_union_find_transitive():
    uf = job_dedup.UnionFind("xyz")
    uf.union("x", "y")
    uf.union("y", "z")
    assert uf.find("x") == uf.find("z")


def review(rid="r1"):
    return review_message(
        "itviec",
        rid,
        "abc",
        "https://itviec.com/nha-tuyen-dung/abc/danh-gia",
        {
            "review_month": "2026-10",
            "company_name": "Công ty Cổ phần ABC Software",
            "title": "Ổn",
            "liked_text": "Lương tốt, đồng nghiệp thân thiện. Liên hệ 0912345678",
            "improvement_text": "Hay phải OT cuối tuần.",
        },
    )


def test_absa_stub_rows_follow_contract():
    rows = absa_scorer.score([review()], stub=True, run_id="t")
    assert rows
    cols = {
        "review_uid",
        "company_key",
        "review_date",
        "sentence_index",
        "sentence_text",
        "aspect",
        "polarity",
        "confidence",
        "model_version",
        "run_id",
    }
    assert all(set(r) == cols for r in rows)
    assert {r["company_key"] for r in rows} == {"abc-software"}
    assert all(r["review_date"].isoformat() == "2026-10-01" for r in rows)
    assert all("0912345678" not in r["sentence_text"] for r in rows), "câu ghi ra phải qua bộ lọc PII"
    assert rows[0]["sentence_index"] == 0  # câu đầu của "Điều tôi thích"
    keys = [(r["review_uid"], r["sentence_index"], r["aspect"]) for r in rows]
    assert len(keys) == len(set(keys))


def test_absa_reads_bronze_payload_json():
    msg = review()
    bronze = {k: v for k, v in msg.items() if k != "payload"} | {"payload_json": json.dumps(msg["payload"])}
    assert absa_scorer.score([bronze], stub=True, run_id="t") == absa_scorer.score([msg], stub=True, run_id="t")


def test_company_key_strips_legal_forms():
    assert absa_scorer.company_key("CÔNG TY TNHH CÔNG NGHỆ PHẦN MỀM NASANI") == "cong-nghe-phan-mem-nasani"
    assert absa_scorer.company_key("FPT Software Co., Ltd") == "fpt-software"
    assert absa_scorer.company_key("") is None


def job(sid="1", **payload):
    base = {"title": "Dev", "company_name": "ABC", "description": "x"}
    return job_message("topcv", sid, f"https://www.topcv.vn/viec-lam/dev/{sid}.html", base | payload)


def test_producer_routes_by_kind_and_source():
    topic, key, value = producer.route(job("42"))
    assert (topic, key) == ("jobs.raw.topcv.v1", "42") and value["source_job_id"] == "42"
    topic, key, _ = producer.route(review("r9"))
    assert (topic, key) == ("reviews.raw.itviec.v1", "r9")


def test_producer_sends_bad_message_to_dlq():
    bad = job("7")
    del bad["payload"]
    topic, key, value = producer.route(bad)
    assert topic == producer.DLQ and key == "7"
    assert value["schema_version"] == "parse_error.v1" and value["error_type"] == "schema"


class FakeProducer:
    def __init__(self):
        self.sent = []

    def produce(self, topic, key, value, on_delivery):
        self.sent.append((topic, key, json.loads(value)))
        on_delivery(None, None)

    def poll(self, _):
        return 0

    def flush(self, _):
        return 0


def test_producer_send_file(tmp_path):
    path = tmp_path / "jobs.jsonl"
    write_file([job("1"), job("2"), review("r1")], path)
    fake = FakeProducer()
    count = producer.send([path], fake)
    assert count == {"jobs.raw.topcv.v1": 2, "reviews.raw.itviec.v1": 1}
    assert [k for _, k, _ in fake.sent] == [b"1", b"2", b"r1"]
    assert producer.send([path]) == count  # dry-run: đếm như nhau, không gửi


def test_file_roundtrip(tmp_path):
    for name in ("x.parquet", "x.jsonl"):
        write_file([{"a": 1, "b": "c"}], tmp_path / name)
        assert read_file(tmp_path / name) == [{"a": 1, "b": "c"}]


def test_iceberg_write_is_idempotent(tmp_path):
    pyiceberg = pytest.importorskip("pyiceberg")
    import pyarrow as pa
    from pyiceberg.catalog.sql import SqlCatalog

    from batch.tables import read_table, write_table

    assert pyiceberg
    cat = SqlCatalog("t", uri=f"sqlite:///{tmp_path / 'c.db'}", warehouse=f"file://{tmp_path.as_posix()}")
    cat.create_namespace("silver")
    schema = pa.schema(
        [
            pa.field("job_uid", pa.string(), nullable=False),
            pa.field("dup_group_id", pa.string(), nullable=False),
            pa.field("score", pa.float64()),
            pa.field("dedup_version", pa.string(), nullable=False),
            pa.field("run_id", pa.string(), nullable=False),
        ]
    )
    cat.create_table("silver.job_dedup", schema=schema)
    rows = job_dedup.dedup(harmonize([dict(j) for j in JOBS]), stub=False, run_id="r1")
    write_table(rows, "silver.job_dedup", "job_uid", cat=cat)
    write_table([dict(r, run_id="r2") for r in rows], "silver.job_dedup", "job_uid", cat=cat)
    got = read_table("silver.job_dedup", None, cat=cat)
    assert len(got) == len(JOBS), "chạy lại không được sinh bản trùng"
    assert {r["run_id"] for r in got} == {"r2"}


# ---------- lọc đầu vào: nguồn và chạy tăng dần ----------

ROWS_FILTER = [
    {"job_uid": "a", "source": "topcv", "updated_ts": "2026-11-20T08:00:00"},
    {"job_uid": "b", "source": "itviec", "updated_ts": "2026-11-23T09:30:00"},
    {"job_uid": "c", "source": "vietjobs", "updated_ts": "2026-11-23T10:00:00"},
    {"job_uid": "d", "source": "synthetic", "updated_ts": "2026-11-23T10:00:00"},
    {"job_uid": "e", "source": "topcv", "updated_ts": None},
]


def uids(rows):
    return [r["job_uid"] for r in rows]


def test_filter_rows_theo_nguon():
    from batch.tables import filter_rows

    got = filter_rows(ROWS_FILTER, ("topcv", "itviec"), None, "updated_ts")
    assert uids(got) == ["a", "b", "e"], "phải bỏ vietjobs và dữ liệu mô phỏng"


def test_filter_rows_theo_moc_thoi_gian():
    from batch.tables import filter_rows, parse_ts

    got = filter_rows(ROWS_FILTER, (), parse_ts("2026-11-23"), "updated_ts")
    assert uids(got) == ["b", "c", "d"], "dòng cũ hơn mốc và dòng không có mốc đều bị bỏ"


def test_filter_rows_ket_hop_hai_dieu_kien():
    from batch.tables import filter_rows, parse_ts

    got = filter_rows(ROWS_FILTER, ("topcv", "itviec"), parse_ts("2026-11-23T09:00:00"), "updated_ts")
    assert uids(got) == ["b"]


def test_filter_rows_khong_co_dieu_kien_thi_giu_nguyen():
    from batch.tables import filter_rows

    assert filter_rows(ROWS_FILTER, (), None, "updated_ts") == ROWS_FILTER


def test_changed_since_bao_loi_khi_file_thieu_cot():
    from batch.tables import filter_rows, parse_ts

    with pytest.raises(SystemExit, match="crawl_ts"):
        filter_rows([{"job_uid": "a", "source": "itviec"}], (), parse_ts("2026-11-23"), "crawl_ts")


def test_moc_thoi_gian_sai_dinh_dang_bao_loi():
    from batch.tables import parse_ts

    with pytest.raises(SystemExit, match="changed-since"):
        parse_ts("hôm qua")


def test_load_input_loc_file_theo_nguon(tmp_path):
    from batch.tables import load_input

    path = tmp_path / "in.jsonl"
    write_file(ROWS_FILTER, path)
    ap = __import__("argparse").ArgumentParser()
    from batch.tables import add_io_args

    add_io_args(ap, "silver.job_skills")
    args = ap.parse_args(
        ["--input-file", str(path), "--output-file", str(tmp_path / "o.jsonl"), "--run-id", "t", "--sources", "topcv"]
    )
    assert uids(load_input(args)) == ["a", "e"]


def test_job_dedup_khong_nhan_changed_since():
    """Dedup phải so tin mới với toàn bộ kho tin, nên không được có tham số này."""
    import argparse

    from batch.tables import add_io_args

    ap = argparse.ArgumentParser()
    add_io_args(ap, "silver.job_dedup", changed_since_col=None)
    with pytest.raises(SystemExit):
        ap.parse_args(
            [
                "--input-table",
                "silver.job_postings",
                "--output-table",
                "silver.job_dedup",
                "--run-id",
                "t",
                "--changed-since",
                "2026-11-23",
            ]
        )


def test_table_filter_dung_bieu_thuc_iceberg():
    pytest.importorskip("pyiceberg")
    from pyiceberg.expressions import AlwaysTrue

    from batch.tables import parse_ts, table_filter

    assert table_filter((), None, None) == AlwaysTrue()
    expr = table_filter(("topcv",), parse_ts("2026-11-23"), "updated_ts")
    assert "topcv" in str(expr) and "updated_ts" in str(expr)
