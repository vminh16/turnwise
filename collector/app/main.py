"""Các route của collector.

Hai loại người dùng:

- **Người thu** vào bằng link có mã mời riêng (`/?t=<mã>`). Mã là danh tính duy nhất: không
  tài khoản, không mật khẩu, không họ tên.
- **Quản trị** gửi header `X-Admin-Token`: tạo link mời, thu giọng bot, tải dữ liệu về.

Chạy thử tại máy: `COLLECTOR_ADMIN_TOKEN=... uv run uvicorn app.main:app_factory --factory`.
"""

from __future__ import annotations

import json
import logging
import secrets
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from app.audio import InvalidUpload, check_playback, check_wav
from app.scripts import load_scripts, participant_view, prompt_lines
from app.settings import Settings, load_settings
from app.storage import Store, now

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"
DIALECTS = ("north", "north_central", "central", "south")


class Consent(BaseModel):
    """Phiếu đồng ý ở phụ lục A của `docs/annotation-guide.md`, dạng điện tử.

    Luật 91/2025/QH15 Điều 9: đồng ý theo **từng mục đích**, và im lặng không phải đồng ý —
    nên mục đích 1 phải được tích rõ ràng, mục đích 2 là một lựa chọn riêng.
    """

    purpose_evaluation: bool
    purpose_excerpts: bool
    adult: bool
    wired_headphones: bool
    dialect: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = Store(settings.data_dir)
    scripts = load_scripts(settings.roleplay_dir)
    app = FastAPI(title="Turnwise collector", docs_url=None, redoc_url=None)

    def speaker(t: str) -> str:
        speaker_id = store.speaker_for(t)
        if speaker_id is None:
            raise HTTPException(401, "invite link is not valid")
        return speaker_id

    def admin(x_admin_token: Annotated[str, Header()] = "") -> None:
        if not secrets.compare_digest(x_admin_token.encode(), settings.admin_token.encode()):
            raise HTTPException(401, "admin token required")

    async def read_limited(upload: UploadFile) -> bytes:
        data = await upload.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(413, "file too large")
        return data

    # --- trang ---------------------------------------------------------------------------

    @app.get("/")
    def participant_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/admin")
    def admin_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "admin.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # --- người thu ------------------------------------------------------------------------

    @app.get("/api/config")
    def config(t: str) -> dict[str, Any]:
        speaker_id = speaker(t)
        recorded = store.recorded_scripts(speaker_id)
        prompts = store.prompt_keys()
        # Tình huống người này đã gửi thì không hiện nữa, cho tới khi quản trị xoá bản ghi đó.
        return {
            "done": len(recorded & set(scripts)),
            "total": len(scripts),
            "speaker_id": speaker_id,
            "consented": store.consent_of(speaker_id) is not None,
            "sample_rate_hz": settings.sample_rate_hz,
            "playback_lead_ms": settings.playback_lead_ms,
            "tail_ms": settings.tail_ms,
            "guide_version": settings.guide_version,
            "data_controller": settings.data_controller,
            "scripts": [
                {
                    **participant_view(script),
                    "prompts_ready": all(
                        f"{name}/{index}" in prompts for index in range(len(script["steps"]))
                    ),
                }
                for name, script in scripts.items()
                if name not in recorded
            ],
        }

    @app.post("/api/consent", status_code=201)
    def consent(t: str, body: Consent) -> dict[str, str]:
        speaker_id = speaker(t)
        if not (body.purpose_evaluation and body.adult and body.wired_headphones):
            raise HTTPException(400, "purpose 1, age 18+ and wired headphones are all required")
        if body.dialect not in DIALECTS:
            raise HTTPException(400, f"dialect must be one of {DIALECTS}")
        store.save_consent(
            speaker_id, {**body.model_dump(), "guide_version": settings.guide_version}
        )
        logger.info("consent recorded for %s", speaker_id)
        return {"speaker_id": speaker_id}

    @app.get("/api/prompts/{script}/{step}.wav")
    def prompt_audio(script: str, step: int, t: str) -> FileResponse:
        speaker(t)
        path = store.prompt_path(script, step)
        if path is None or not path.exists():
            raise HTTPException(404, "prompt not recorded yet")
        return FileResponse(path, media_type="audio/wav")

    @app.post("/api/recordings", status_code=201)
    async def upload_recording(
        t: Annotated[str, Form()],
        script: Annotated[str, Form()],
        playback: Annotated[str, Form()],
        client: Annotated[str, Form()],
        audio: Annotated[UploadFile, File()],
    ) -> dict[str, Any]:
        speaker_id = speaker(t)
        consent_record = store.consent_of(speaker_id)
        if consent_record is None:
            raise HTTPException(403, "consent is required before recording")
        if script not in scripts:
            raise HTTPException(404, f"unknown script {script!r}")
        if script in store.recorded_scripts(speaker_id):
            raise HTTPException(409, "this scenario is already recorded for this speaker")
        data = await read_limited(audio)
        try:
            frames = check_wav(data, channels=2, sample_rate_hz=settings.sample_rate_hz)
            entries = check_playback(json.loads(playback), len(scripts[script]["steps"]), frames)
            client_info = json.loads(client)
        except json.JSONDecodeError as error:
            raise HTTPException(400, f"invalid JSON: {error}") from error
        except InvalidUpload as error:
            raise HTTPException(400, str(error)) from error
        sidecar = {
            "layout": {"caller_channel": 0, "bot_channel": 1},
            "sample_rate_hz": settings.sample_rate_hz,
            "playback": entries,
            "client": client_info,
            "consent": consent_record,
            "received_at": now(),
        }
        saved = store.save_recording(speaker_id, script, data, frames, sidecar)
        logger.info("recording %s saved for %s", saved["file"], speaker_id)
        return saved

    # --- quản trị ------------------------------------------------------------------------

    @app.post("/api/admin/invites", status_code=201, dependencies=[Depends(admin)])
    def create_invite() -> dict[str, str]:
        token = secrets.token_urlsafe(16)
        return {"token": token, "speaker_id": store.create_invite(token)}

    @app.get("/api/admin/config", dependencies=[Depends(admin)])
    def admin_config() -> dict[str, int]:
        return {"sample_rate_hz": settings.sample_rate_hz}

    @app.get("/api/admin/invites", dependencies=[Depends(admin)])
    def invites() -> list[dict[str, Any]]:
        return store.list_invites()

    @app.delete("/api/admin/speakers/{speaker_id}", dependencies=[Depends(admin)])
    def withdraw(speaker_id: str) -> dict[str, Any]:
        """Thực hiện quyền rút lại đồng ý và xoá dữ liệu (Luật 91/2025/QH15 Điều 10, 14)."""
        deleted = store.withdraw(speaker_id)
        if deleted is None:
            raise HTTPException(404, f"unknown speaker {speaker_id!r}")
        logger.info("speaker %s withdrew; %d recordings deleted", speaker_id, deleted)
        return {"speaker_id": speaker_id, "recordings_deleted": deleted}

    @app.get("/api/admin/recordings", dependencies=[Depends(admin)])
    def recordings() -> list[dict[str, Any]]:
        return [
            {
                "id": row["id"],
                "speaker_id": row["speaker_id"],
                "script": row["script"],
                "title": scripts.get(row["script"], {}).get("title", row["script"]),
                "seconds": round(row["frames"] / settings.sample_rate_hz, 2),
                "created_at": row["created_at"],
            }
            for row in store.list_recordings()
        ]

    @app.get("/api/admin/recordings/{recording_id}.wav", dependencies=[Depends(admin)])
    def recording_audio(recording_id: int) -> FileResponse:
        path = store.recording_path(recording_id)
        if path is None or not path.exists():
            raise HTTPException(404, "recording not found")
        return FileResponse(path, media_type="audio/wav")

    @app.delete("/api/admin/recordings/{recording_id}", dependencies=[Depends(admin)])
    def delete_recording(recording_id: int) -> dict[str, int]:
        if not store.delete_recording(recording_id):
            raise HTTPException(404, "recording not found")
        logger.info("recording %d deleted by admin", recording_id)
        return {"deleted": recording_id}

    @app.get("/api/admin/lines", dependencies=[Depends(admin)])
    def lines() -> list[dict[str, Any]]:
        recorded = store.prompt_keys()
        return [
            {
                **line,
                "title": scripts[line["script"]]["title"],
                "recorded": f"{line['script']}/{line['step']}" in recorded,
            }
            for line in prompt_lines(scripts)
        ]

    @app.get("/api/admin/prompts/{script}/{step}.wav", dependencies=[Depends(admin)])
    def admin_prompt_audio(script: str, step: int) -> FileResponse:
        path = store.prompt_path(script, step)
        if path is None or not path.exists():
            raise HTTPException(404, "prompt not recorded yet")
        return FileResponse(path, media_type="audio/wav")

    @app.post("/api/admin/prompts", status_code=201, dependencies=[Depends(admin)])
    async def upload_prompt(
        script: Annotated[str, Form()],
        step: Annotated[int, Form()],
        audio: Annotated[UploadFile, File()],
    ) -> dict[str, str]:
        if script not in scripts or not 0 <= step < len(scripts[script]["steps"]):
            raise HTTPException(404, "unknown script step")
        data = await read_limited(audio)
        try:
            check_wav(data, channels=1, sample_rate_hz=settings.sample_rate_hz)
        except InvalidUpload as error:
            raise HTTPException(400, str(error)) from error
        return {"key": store.save_prompt(script, step, data)}

    @app.get("/api/admin/export", dependencies=[Depends(admin)])
    def export() -> FileResponse:
        """Toàn bộ dữ liệu trong một file zip: bản sao nhất quán của database và mọi file."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as handle:
            archive = Path(handle.name)
        with tempfile.TemporaryDirectory() as scratch:
            snapshot = Path(scratch) / "collector.sqlite3"
            with (
                closing(sqlite3.connect(store.db_path)) as source,
                closing(sqlite3.connect(snapshot)) as target,
            ):
                source.backup(target)
            # Không nén: PCM gần như không nhỏ đi (~7%) mà nén làm chậm gấp nhiều lần.
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as bundle:
                bundle.write(snapshot, "collector.sqlite3")
                for folder in ("sessions", "prompts"):
                    for path in sorted((settings.data_dir / folder).rglob("*")):
                        if path.is_file():
                            bundle.write(path, path.relative_to(settings.data_dir).as_posix())
        return FileResponse(
            archive,
            filename=f"turnwise-collector-{now()}.zip",
            background=BackgroundTask(archive.unlink),
        )

    return app


def app_factory() -> FastAPI:
    """Điểm vào cho uvicorn: `uvicorn app.main:app_factory --factory`."""
    logging.basicConfig(level=logging.INFO)
    return create_app()
