from recsys.judge_kit import ndcg, top_k


def test_ndcg_thu_tu_ly_tuong_bang_1():
    grades = {"a": 2, "b": 1, "c": 0}
    assert ndcg(["a", "b", "c"], grades) == 1.0


def test_ndcg_dao_thu_tu_nho_hon_1_va_khong_cham_tinh_0():
    grades = {"a": 2, "b": 1}
    assert 0 < ndcg(["b", "x", "a"], grades) < 1


def test_ndcg_khong_tin_nao_hop_bang_0():
    assert ndcg(["a", "b"], {"a": 0, "b": 0}) == 0.0


def test_top_k_hoa_diem_xep_theo_job_uid():
    assert top_k({"b": 1.0, "a": 1.0, "c": 2.0})[:3] == ["c", "a", "b"]
