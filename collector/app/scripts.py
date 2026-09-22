"""Đọc kịch bản `roleplay/nX-*.yaml` cho web.

Không kiểm lại schema: `evaluation/roleplay.py` và bộ test ở gốc repo đã kiểm từng file.
Collector cố ý không import `turnwise` để khỏi kéo numpy và cả gói runtime lên server thu.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_scripts(directory: Path) -> dict[str, dict[str, Any]]:
    scripts: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("n[1-5]-*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        scripts[raw["name"]] = raw
    if not scripts:
        raise RuntimeError(f"no role-play scripts found in {directory}")
    return scripts


def participant_view(script: dict[str, Any]) -> dict[str, Any]:
    """Kịch bản cho người thu: **không** có lời bot.

    Người thu đọc trước lời bot thì biết trước bot sắp nói gì, và phản ứng không còn là phản
    ứng với thứ vừa nghe. Họ chỉ thấy tình huống, thẻ giả và chỉ dẫn của từng bước.
    """
    return {
        "name": script["name"],
        "flow": script["flow"],
        "title": script["title"],
        "persona": script["persona"],
        "props": script.get("props", {}),
        "steps": [
            {
                "customer": step["customer"],
                "example": step.get("example"),
                "replies": step.get("replies", []),
            }
            for step in script["steps"]
        ],
    }


def prompt_lines(scripts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Mọi câu bot cần thu giọng, cho trang quản trị."""
    return [
        {"script": name, "step": index, "bot": step["bot"]}
        for name, script in scripts.items()
        for index, step in enumerate(script["steps"])
    ]
