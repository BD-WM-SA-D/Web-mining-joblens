"""Bootstrap theo cụm: lấy lại **nhóm** (tin, review) có hoàn lại, không lấy lại từng câu.

Câu trong cùng một tin tuyển dụng (hay một review) không độc lập: chung người viết, chung văn phong,
chung kỹ năng lặp lại. Lấy lại theo câu coi chúng như độc lập nên cho khoảng tin cậy **hẹp giả**.
Lấy lại theo nhóm giữ nguyên sự phụ thuộc đó trong mỗi mẫu.

    from experiments.bootstrap import cluster_indices
    for ix in cluster_indices(groups, b=1000, seed=0):
        ...  # ix là mảng chỉ số câu của một mẫu bootstrap
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import numpy as np


def cluster_indices(groups: Sequence[str], b: int = 1000, seed: int = 0) -> Iterator[np.ndarray]:
    """Mỗi lần: rút len(nhóm) nhóm có hoàn lại, trả về chỉ số mọi câu của các nhóm đã rút."""
    rng = np.random.default_rng(seed)
    uniq = sorted(set(groups))
    members: dict[str, list[int]] = {g: [] for g in uniq}
    for i, g in enumerate(groups):
        members[g].append(i)
    arrays = [np.array(members[g]) for g in uniq]
    for _ in range(b):
        picks = rng.integers(0, len(uniq), size=len(uniq))
        yield np.concatenate([arrays[k] for k in picks])


def sentence_indices(n: int, b: int = 1000, seed: int = 0) -> Iterator[np.ndarray]:
    """Lấy lại theo câu (cách cũ) – giữ để so độ rộng khoảng tin cậy."""
    rng = np.random.default_rng(seed)
    for _ in range(b):
        yield rng.integers(0, n, size=n)


def ci(values: Sequence[float]) -> tuple[float, float, float]:
    """(cận dưới 2,5%, cận trên 97,5%, tỷ lệ mẫu có giá trị ≤ 0)."""
    v = np.asarray(values)
    lo, hi = np.percentile(v, [2.5, 97.5])
    return float(lo), float(hi), float(np.mean(v <= 0))
