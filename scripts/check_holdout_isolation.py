"""Fail if any training or tuning code references the locked evaluation set.

`data/holdout/` may only be read by `evaluation/`, and only when producing the final report
(SPEC.md §6, AGENTS.md "Off-Limits"). A rule in a document gets forgotten; a red build does not.

Run directly, or through .github/workflows/holdout-guard.yml:

    uv run python scripts/check_holdout_isolation.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Thư mục bị cấm chạm vào holdout. `evaluation/` cố tình không có trong danh sách.
GUARDED_DIRS = ("training", "notebooks", "scripts", "src")

# Bắt cả "data/holdout", "data\holdout" và chuỗi bị tách như Path("data") / "holdout".
PATTERN = re.compile(r"""holdout""", re.IGNORECASE)

# Chính file này nói về holdout nên phải tự loại trừ, nếu không nó luôn tự báo lỗi.
SELF = Path(__file__).resolve()


def scan(root: Path) -> list[tuple[Path, int, str]]:
    """Trả về danh sách (file, số dòng, nội dung dòng) vi phạm."""
    hits: list[tuple[Path, int, str]] = []
    for directory in GUARDED_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in {".py", ".yaml", ".yml", ".ipynb", ".toml"}:
                continue
            if path.resolve() == SELF:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if not PATTERN.search(line):
                    continue
                hits.append((path.relative_to(root), lineno, line.strip()))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    hits = scan(args.root)
    if not hits:
        print(f"holdout isolation OK - no references under {', '.join(GUARDED_DIRS)}/")
        return 0

    print("Locked evaluation set referenced outside evaluation/:", file=sys.stderr)
    for path, lineno, line in hits:
        print(f"  {path}:{lineno}: {line}", file=sys.stderr)
    print(
        "\ndata/holdout/ may only be read by evaluation/, and only for the final report.\n"
        "Use a validation split carved out of data/processed/ instead.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
