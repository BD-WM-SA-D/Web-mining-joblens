"""Kiểm tra môi trường: thư viện chính import được và hợp đồng dữ liệu dùng được."""

from datasketch import MinHash
from underthesea import word_tokenize

from joblens_contracts import job_uid, load_schema, load_table_contract


def test_contracts():
    assert job_uid("synthetic", "syn-000001") == "862e0278ea284bae21ffed05e1dafedc6baac559"
    assert load_schema("job_posting.v1")["properties"]["schema_version"]["const"] == "job_posting.v1"
    assert load_table_contract("silver.job_skills")["writer_repo"] == "Web-mining-joblens"


def test_vietnamese_tokenizer():
    assert "lập trình viên" in word_tokenize("Tuyển lập trình viên Python tại Hà Nội")


def test_minhash():
    def mh(text):
        m = MinHash(num_perm=64)
        for token in text.lower().split():
            m.update(token.encode())
        return m

    a = mh("Kỹ sư Xử Lý Nước Thải tại TP.HCM")
    b = mh("Kỹ sư Xử Lí Nước Thải tại TP.HCM")
    assert a.jaccard(b) > 0.5
