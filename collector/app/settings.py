"""Cấu hình của collector, đọc từ biến môi trường.

Collector chạy trên một server riêng (Railway, Render, Docker), không có `configs/` của repo
bên cạnh, nên cấu hình đi qua biến môi trường như mọi web app. Tốc độ lấy mẫu phải khớp
`audio.sample_rate_hz` trong `configs/default.yaml`; lệch thì `WavFrameSource` từ chối file
ngay khi đọc, nên lỗi không lọt qua được.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIN_ADMIN_TOKEN_CHARS = 16


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    roleplay_dir: Path
    admin_token: str
    sample_rate_hz: int
    max_upload_bytes: int
    playback_lead_ms: int
    tail_ms: int
    guide_version: str
    data_controller: str


def load_settings() -> Settings:
    token = os.environ.get("COLLECTOR_ADMIN_TOKEN", "")
    if len(token) < MIN_ADMIN_TOKEN_CHARS:
        raise RuntimeError(
            f"COLLECTOR_ADMIN_TOKEN must be set to at least {MIN_ADMIN_TOKEN_CHARS} characters"
        )
    return Settings(
        data_dir=Path(os.environ.get("COLLECTOR_DATA_DIR", REPO_ROOT / "data" / "collector")),
        roleplay_dir=Path(os.environ.get("COLLECTOR_ROLEPLAY_DIR", REPO_ROOT / "roleplay")),
        admin_token=token,
        sample_rate_hz=int(os.environ.get("COLLECTOR_SAMPLE_RATE_HZ", "16000")),
        max_upload_bytes=int(os.environ.get("COLLECTOR_MAX_UPLOAD_BYTES", str(64 * 1024 * 1024))),
        playback_lead_ms=int(os.environ.get("COLLECTOR_PLAYBACK_LEAD_MS", "100")),
        tail_ms=int(os.environ.get("COLLECTOR_TAIL_MS", "1500")),
        guide_version=os.environ.get("COLLECTOR_GUIDE_VERSION", "1.2"),
        data_controller=os.environ.get("COLLECTOR_DATA_CONTROLLER", "[chưa điền]"),
    )
