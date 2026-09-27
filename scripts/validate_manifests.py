"""Kiểm manifest của bộ dữ liệu vàng khớp file trên đĩa. Thoát khác 0 nếu có lỗi.

    uv run python scripts/validate_manifests.py

Chỉ là lối vào mỏng; luật kiểm nằm ở `evaluation/dataset.py` (`check`), cùng chỗ với luật nạp và
chia tập, để hai bên không bao giờ lệch nhau.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.dataset import check


def main() -> int:
    problems = check()
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
