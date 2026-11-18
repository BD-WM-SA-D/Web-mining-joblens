from annotation.export_bio import TOKEN_RE
from ie.baseline_dict import build_index, spans, tag
from ie.weak_rules import refine


def run(sent: str, forms: list[str]) -> list[str]:
    toks = TOKEN_RE.findall(sent)
    index, n = build_index(forms)
    return [s for _, _, s in spans(toks, refine(toks, tag(toks, index, n)))]


def test_tach_dau_gach_cheo():
    assert run("Biết Maven/Gradle và Docker.", ["Maven/Gradle", "Docker"]) == ["Maven", "Gradle", "Docker"]


def test_giu_ten_viet_lien():
    assert run("Kinh nghiệm CI/CD, UI/UX.", ["CI/CD", "UI/UX"]) == ["CI / CD", "UI / UX"]


def test_bo_stop_sau_khi_tach():
    assert run("Quản trị server/storage, VMware.", ["server/storage", "VMware"]) == ["VMware"]


def test_bo_tu_chung_va_tai_lieu():
    assert run("Viết BRD, SRS và gọi API bằng Postman.", ["BRD", "SRS", "API", "Postman"]) == ["Postman"]


def test_ai_dung_rieng_va_bo_ngu():
    assert run("Am hiểu AI, cloud.", ["AI", "cloud"]) == ["AI", "cloud"]
    assert run("Deliver AI solutions as an AI Engineer.", ["AI"]) == []
    assert run("Tư vấn giải pháp AI cho khách hàng.", ["AI"]) == []


def test_self_train_merge_chi_them_span_dong_thuan():
    from ie.self_train import merge

    toks = TOKEN_RE.findall("Biết Kafka, Redis và API.")
    weak = ["O", "B-SKILL", "O", "O", "O", "O", "O"]
    p1 = ["O", "B-SKILL", "O", "B-SKILL", "O", "B-SKILL", "O"]
    p2 = ["O", "B-SKILL", "O", "B-SKILL", "O", "O", "O"]
    tags, kept = merge(toks, weak, [p1, p2])
    assert kept == ["Redis"]
    assert tags == ["O", "B-SKILL", "O", "B-SKILL", "O", "O", "O"]
