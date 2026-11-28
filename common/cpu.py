"""Số luồng CPU cho torch khi chạy trong container.

torch mặc định dùng số nhân của cả máy chủ, kể cả khi pod chỉ được cấp 1-2 CPU. Khi đó các luồng tranh nhau
phần CPU được cấp, bị bóp (throttle) liên tục và chạy chậm hơn so với dùng ít luồng. Hàm ở đây lấy số luồng theo
thứ tự: biến môi trường JOBLENS_TORCH_THREADS, giới hạn CPU của cgroup (giới hạn của pod), rồi số nhân của máy.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

CGROUP_V2 = Path("/sys/fs/cgroup/cpu.max")
CGROUP_V1_QUOTA = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
CGROUP_V1_PERIOD = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")


def cgroup_cpus(
    v2: Path = CGROUP_V2, v1_quota: Path = CGROUP_V1_QUOTA, v1_period: Path = CGROUP_V1_PERIOD
) -> int | None:
    """Số CPU pod được cấp (làm tròn lên), hoặc None nếu không giới hạn hay không đọc được."""
    try:
        if v2.exists():
            quota, period = v2.read_text().split()[:2]
            if quota != "max":
                return max(1, math.ceil(int(quota) / int(period)))
            return None
        if v1_quota.exists() and v1_period.exists():
            quota = int(v1_quota.read_text())
            if quota > 0:
                return max(1, math.ceil(quota / int(v1_period.read_text())))
    except (OSError, ValueError):
        return None
    return None


def torch_threads() -> int:
    env = os.environ.get("JOBLENS_TORCH_THREADS")
    if env and env.isdigit() and int(env) > 0:
        return int(env)
    cores = os.cpu_count() or 1
    limit = cgroup_cpus()
    return min(cores, limit) if limit else cores


def setup_torch_threads() -> int:
    """Đặt số luồng cho torch, trả số luồng đã đặt. Gọi trước khi chạy mô hình."""
    import torch

    n = torch_threads()
    torch.set_num_threads(n)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:  # đã khởi động luồng song song thì không đổi được nữa
        pass
    return n
