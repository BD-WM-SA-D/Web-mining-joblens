"""Bootstrap theo cụm: mỗi mẫu lấy nguyên cả nhóm, không cắt nhóm."""

from experiments.bootstrap import ci, cluster_indices


def test_moi_mau_lay_nguyen_ca_nhom():
    groups = ["a", "a", "a", "b", "c", "c"]
    for ix in cluster_indices(groups, b=50, seed=1):
        picked = [groups[i] for i in ix]
        for g in set(picked):
            # số câu của nhóm g trong mẫu phải là bội số kích thước nhóm
            assert picked.count(g) % groups.count(g) == 0


def test_khoang_tin_cay():
    lo, hi, p0 = ci([0.1, 0.2, 0.3, 0.4, -0.1])
    assert lo < hi
    assert p0 == 0.2
