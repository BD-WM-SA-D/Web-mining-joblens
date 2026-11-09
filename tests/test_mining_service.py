"""Test hợp đồng mining-service: mọi response khớp schema trong service/contract/mining.v1.yaml."""

import time
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

import service.app as svc
from service.index import build
from service.skills import SkillCatalog, slug

CONTRACT = yaml.safe_load((Path(__file__).parents[1] / "service/contract/mining.v1.yaml").read_text(encoding="utf-8"))


def check(name: str, body: dict) -> None:
    schema = {"$ref": f"#/components/schemas/{name}", "components": CONTRACT["components"]}
    Draft202012Validator(schema).validate(body)


@pytest.fixture
def client(monkeypatch):
    cat = SkillCatalog()
    rows = [
        {"job_uid": "a" * 40, "title": "Python Developer", "description": "Python, Django, SQL", "skill_tags": []},
        {"job_uid": "b" * 40, "title": "Tester", "description": "Viết test case", "skill_tags": ["SQL"]},
        {"job_uid": "c" * 40, "title": "Kế toán", "description": "Lập báo cáo thuế", "skill_tags": []},
    ]
    monkeypatch.setattr(svc, "job_index", {k: set(v) for k, v in build(rows, cat).items()})
    monkeypatch.setattr(svc, "index_snapshot", "fixture")
    return TestClient(svc.app)


def test_slug():
    assert slug("C++") == "cplusplus"
    assert slug("Thiết kế đồ họa") == "thiet-ke-do-hoa"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    check("Health", r.json())


def test_extract_matches_contract_and_offsets(client):
    text = "Yêu cầu: thành thạo Python và SQL, biết Docker."
    body = client.post("/v1/skills:extract", json={"text": text}).json()
    check("ExtractResponse", body)
    forms = [s["surface_form"] for s in body["skills"]]
    assert {"Python", "SQL", "Docker"} <= set(forms)
    for s in body["skills"]:
        assert text[s["start"] : s["end"]] == s["surface_form"]
        assert s["skill_id"].startswith(("joblens:", "http"))


def test_extract_min_confidence_filters(client):
    body = client.post("/v1/skills:extract", json={"text": "Python", "min_confidence": 0.95}).json()
    assert body["skills"] == []


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/v1/skills:extract", {"text": ""}),
        ("/v1/skills:extract", {"text": "x" * 20001}),
        ("/v1/skills:extract", {"text": "Python", "extra": 1}),
        ("/v1/recommend", {"skill_ids": []}),
        ("/v1/recommend", {"skill_ids": ["x"], "k": 0}),
    ],
)
def test_bad_request_is_400(client, path, payload):
    r = client.post(path, json=payload)
    assert r.status_code == 400
    check("Error", r.json())
    assert "x" * 50 not in r.json()["error"]  # không lặp lại văn bản đầu vào


def test_malformed_json_is_400(client):
    r = client.post("/v1/skills:extract", content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    check("Error", r.json())


def test_recommend_ranks_by_overlap(client):
    ids = sorted(SkillCatalog().skill_ids("Python SQL"))
    body = client.post("/v1/recommend", json={"skill_ids": ids, "k": 5}).json()
    check("RecommendResponse", body)
    uids = [i["job_uid"] for i in body["items"]]
    assert uids[0] == "a" * 40 and "c" * 40 not in uids


def test_latency_under_3s(client):
    text = "Kinh nghiệm Java, Spring Boot, MySQL, Docker, Kubernetes. " * 300
    t = time.perf_counter()
    client.post("/v1/skills:extract", json={"text": text[:20000]})
    assert time.perf_counter() - t < 3
