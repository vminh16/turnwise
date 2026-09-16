"""Lưu trữ: SQLite cho bảng, thư mục cho file âm thanh.

SQLite có sẵn trong thư viện chuẩn, và cả thư mục dữ liệu nằm trên một volume duy nhất —
mount một ổ bền trên Railway/Render là đủ, không cần dịch vụ database riêng.

Mỗi bản ghi âm có thêm một file `.json` bên cạnh với nhật ký phát và thông tin buổi thu, để
thư mục tải về vẫn tự mô tả được kể cả khi không có database.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS invites (
    token TEXT PRIMARY KEY,
    speaker_id TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    withdrawn_at TEXT
);
CREATE TABLE IF NOT EXISTS consents (
    speaker_id TEXT PRIMARY KEY REFERENCES invites(speaker_id),
    created_at TEXT NOT NULL,
    record TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    speaker_id TEXT NOT NULL REFERENCES invites(speaker_id),
    script TEXT NOT NULL,
    file TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    frames INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prompts (
    key TEXT PRIMARY KEY,
    file TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


class Store:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / "collector.sqlite3"
        with self._db() as db:
            db.executescript(SCHEMA)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(invites)")}
            if "withdrawn_at" not in columns:  # database tạo trước khi có quyền rút lại
                db.execute("ALTER TABLE invites ADD COLUMN withdrawn_at TEXT")

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    # --- mời người thu ------------------------------------------------------------------

    def create_invite(self, token: str) -> str:
        with self._db() as db:
            count = db.execute("SELECT COUNT(*) FROM invites").fetchone()[0]
            speaker_id = f"S{count + 1:03d}"
            db.execute(
                "INSERT INTO invites (token, speaker_id, created_at) VALUES (?, ?, ?)",
                (token, speaker_id, now()),
            )
        return speaker_id

    def speaker_for(self, token: str) -> str | None:
        with self._db() as db:
            row = db.execute(
                "SELECT speaker_id FROM invites WHERE token = ? AND withdrawn_at IS NULL", (token,)
            ).fetchone()
        return None if row is None else str(row["speaker_id"])

    def list_invites(self) -> list[dict[str, Any]]:
        with self._db() as db:
            rows = db.execute(
                """
                SELECT i.token, i.speaker_id, i.created_at,
                       i.withdrawn_at IS NOT NULL AS withdrawn,
                       c.speaker_id IS NOT NULL AS consented,
                       (SELECT COUNT(*) FROM recordings r WHERE r.speaker_id = i.speaker_id)
                           AS recordings
                FROM invites i LEFT JOIN consents c ON c.speaker_id = i.speaker_id
                ORDER BY i.speaker_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def withdraw(self, speaker_id: str) -> int | None:
        """Rút lại đồng ý: xoá bản ghi, file đi kèm và bản đồng ý; link mời hết hiệu lực.

        Dòng mời **giữ lại** với mốc rút lại, để mã người nói không bao giờ được cấp lại cho
        người khác. Trả số bản ghi đã xoá, hoặc `None` nếu không có người nói đó.
        """
        with self._db() as db:
            if (
                db.execute("SELECT 1 FROM invites WHERE speaker_id = ?", (speaker_id,)).fetchone()
                is None
            ):
                return None
            files = [
                row["file"]
                for row in db.execute(
                    "SELECT file FROM recordings WHERE speaker_id = ?", (speaker_id,)
                )
            ]
            for relative in files:
                target = self.data_dir / relative
                target.unlink(missing_ok=True)
                target.with_suffix(".json").unlink(missing_ok=True)
            db.execute("DELETE FROM recordings WHERE speaker_id = ?", (speaker_id,))
            db.execute("DELETE FROM consents WHERE speaker_id = ?", (speaker_id,))
            db.execute(
                "UPDATE invites SET withdrawn_at = ? WHERE speaker_id = ?", (now(), speaker_id)
            )
        return len(files)

    # --- đồng ý -------------------------------------------------------------------------

    def save_consent(self, speaker_id: str, record: dict[str, Any]) -> None:
        with self._db() as db:
            db.execute(
                "INSERT OR REPLACE INTO consents (speaker_id, created_at, record) VALUES (?, ?, ?)",
                (speaker_id, now(), json.dumps(record, ensure_ascii=False)),
            )

    def consent_of(self, speaker_id: str) -> dict[str, Any] | None:
        with self._db() as db:
            row = db.execute(
                "SELECT record FROM consents WHERE speaker_id = ?", (speaker_id,)
            ).fetchone()
        return None if row is None else dict(json.loads(row["record"]))

    # --- bản ghi âm ---------------------------------------------------------------------

    def save_recording(
        self, speaker_id: str, script: str, audio: bytes, frames: int, sidecar: dict[str, Any]
    ) -> dict[str, Any]:
        stamp = now()
        relative = Path("sessions") / speaker_id / f"{script}-{stamp}.wav"
        target = self.data_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(audio)
        digest = hashlib.sha256(audio).hexdigest()
        sidecar = {**sidecar, "speaker_id": speaker_id, "script": script, "sha256": digest}
        target.with_suffix(".json").write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        with self._db() as db:
            db.execute(
                """
                INSERT INTO recordings (speaker_id, script, file, sha256, bytes, frames, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (speaker_id, script, relative.as_posix(), digest, len(audio), frames, stamp),
            )
        return {"file": relative.as_posix(), "sha256": digest, "frames": frames}

    def list_recordings(self) -> list[dict[str, Any]]:
        with self._db() as db:
            rows = db.execute(
                "SELECT id, speaker_id, script, frames, bytes, created_at FROM recordings "
                "ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def recording_path(self, recording_id: int) -> Path | None:
        with self._db() as db:
            row = db.execute("SELECT file FROM recordings WHERE id = ?", (recording_id,)).fetchone()
        return None if row is None else self.data_dir / row["file"]

    def delete_recording(self, recording_id: int) -> bool:
        """Xoá một bản ghi và file đi kèm. Tình huống đó sẽ hiện lại cho người thu."""
        with self._db() as db:
            row = db.execute("SELECT file FROM recordings WHERE id = ?", (recording_id,)).fetchone()
            if row is None:
                return False
            target = self.data_dir / row["file"]
            target.unlink(missing_ok=True)
            target.with_suffix(".json").unlink(missing_ok=True)
            db.execute("DELETE FROM recordings WHERE id = ?", (recording_id,))
        return True

    def recorded_scripts(self, speaker_id: str) -> set[str]:
        with self._db() as db:
            rows = db.execute(
                "SELECT DISTINCT script FROM recordings WHERE speaker_id = ?", (speaker_id,)
            ).fetchall()
        return {str(row["script"]) for row in rows}

    # --- giọng bot ----------------------------------------------------------------------

    def save_prompt(self, script: str, step: int, audio: bytes) -> str:
        key = f"{script}/{step}"
        relative = Path("prompts") / script / f"{step}.wav"
        target = self.data_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(audio)
        with self._db() as db:
            db.execute(
                "INSERT OR REPLACE INTO prompts (key, file, sha256, created_at) "
                "VALUES (?, ?, ?, ?)",
                (key, relative.as_posix(), hashlib.sha256(audio).hexdigest(), now()),
            )
        return key

    def prompt_path(self, script: str, step: int) -> Path | None:
        with self._db() as db:
            row = db.execute(
                "SELECT file FROM prompts WHERE key = ?", (f"{script}/{step}",)
            ).fetchone()
        return None if row is None else self.data_dir / row["file"]

    def prompt_keys(self) -> set[str]:
        with self._db() as db:
            return {str(row["key"]) for row in db.execute("SELECT key FROM prompts")}
