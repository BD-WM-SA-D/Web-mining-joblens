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
