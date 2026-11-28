from common.cpu import cgroup_cpus, torch_threads


def test_cgroup_v2_quota(tmp_path):
    f = tmp_path / "cpu.max"
    f.write_text("150000 100000\n")
    assert cgroup_cpus(v2=f) == 2


def test_cgroup_v2_unlimited(tmp_path):
    f = tmp_path / "cpu.max"
    f.write_text("max 100000\n")
    assert cgroup_cpus(v2=f) is None


def test_cgroup_v1(tmp_path):
    q, p = tmp_path / "q", tmp_path / "p"
    q.write_text("100000")
    p.write_text("100000")
    assert cgroup_cpus(v2=tmp_path / "none", v1_quota=q, v1_period=p) == 1


def test_env_wins(monkeypatch):
    monkeypatch.setenv("JOBLENS_TORCH_THREADS", "3")
    assert torch_threads() == 3
