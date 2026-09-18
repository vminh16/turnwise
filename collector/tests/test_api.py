"""Hợp đồng của collector: ai được làm gì, và file nào được nhận.

Mỗi lần server nhận nhầm một file hỏng là một buổi thu mất trắng mà không ai biết cho tới
lúc gán nhãn. Nên phần lớn test ở đây là test **từ chối**.
"""

from __future__ import annotations

import io
import json
import struct
import wave
import zipfile
from pathlib import Path

import pytest
from app.main import create_app
from app.settings import REPO_ROOT, Settings
from fastapi.testclient import TestClient

ADMIN = {"X-Admin-Token": "a" * 32}
RATE = 16000
SCRIPT = "n5-a-agent-first"  # hai bước


def wav_bytes(channels: int = 2, rate: int = RATE, frames: int = RATE * 3) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(struct.pack("<h", 0) * frames * channels)
    return buffer.getvalue()


def playback(first_end: int = 16000, second_start: int = 24000) -> str:
    return json.dumps(
        [
            {"step": 0, "pressed_sample": 0, "start_sample": 1600, "end_sample": first_end},
            {"step": 1, "pressed_sample": 20000, "start_sample": second_start, "end_sample": 40000},
        ]
    )


CONSENT = {
    "purpose_evaluation": True,
    "purpose_excerpts": False,
    "adult": True,
    "wired_headphones": True,
    "dialect": "south",
}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        roleplay_dir=REPO_ROOT / "roleplay",
        admin_token=ADMIN["X-Admin-Token"],
        sample_rate_hz=RATE,
        max_upload_bytes=4 * 1024 * 1024,
        playback_lead_ms=100,
        tail_ms=1500,
        guide_version="test",
        data_controller="test",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def invite(client: TestClient) -> str:
    response = client.post("/api/admin/invites", headers=ADMIN)
    assert response.status_code == 201
    return str(response.json()["token"])


def upload(client: TestClient, token: str, **overrides: object) -> object:
    form = {"t": token, "script": SCRIPT, "playback": playback(), "client": "{}"}
    audio = overrides.pop("audio", wav_bytes())
    form.update({key: str(value) for key, value in overrides.items()})
    return client.post("/api/recordings", data=form, files={"audio": ("a.wav", audio, "audio/wav")})


# --- quyền ------------------------------------------------------------------------------


def test_the_app_refuses_to_start_without_a_strong_admin_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.settings import load_settings

    monkeypatch.setenv("COLLECTOR_ADMIN_TOKEN", "short")
    with pytest.raises(RuntimeError, match="COLLECTOR_ADMIN_TOKEN"):
        load_settings()


def test_the_app_refuses_to_start_when_the_data_dir_is_not_a_mounted_volume(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Trên Railway/Render không gắn volume thì mỗi lần deploy lại là mất sạch dữ liệu."""
    from app.settings import load_settings

    monkeypatch.setenv("COLLECTOR_ADMIN_TOKEN", "a" * 32)
    monkeypatch.setenv("COLLECTOR_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("COLLECTOR_REQUIRE_VOLUME", "1")
    with pytest.raises(RuntimeError, match="volume"):
        load_settings()


def test_admin_routes_need_the_admin_token(client: TestClient) -> None:
    assert client.post("/api/admin/invites").status_code == 401
    assert client.post("/api/admin/invites", headers={"X-Admin-Token": "b" * 32}).status_code == 401


def test_an_unknown_invite_link_is_refused(client: TestClient) -> None:
    assert client.get("/api/config", params={"t": "nope"}).status_code == 401


def test_invites_get_sequential_pseudonymous_speaker_ids(client: TestClient) -> None:
    ids = [client.post("/api/admin/invites", headers=ADMIN).json()["speaker_id"] for _ in range(3)]
    assert ids == ["S001", "S002", "S003"]


# --- người thu không thấy lời bot ---------------------------------------------------------


def test_the_participant_never_receives_bot_lines(client: TestClient) -> None:
    config = client.get("/api/config", params={"t": invite(client)}).json()
    payload = json.dumps(config, ensure_ascii=False)
    bot_lines = [line["bot"] for line in client.get("/api/admin/lines", headers=ADMIN).json()]

    assert len(config["scripts"]) == 9
    assert bot_lines
    assert not [line for line in bot_lines if line in payload]
    assert config["consented"] is False


# --- đồng ý -----------------------------------------------------------------------------


def test_recording_before_consent_is_refused(client: TestClient) -> None:
    assert upload(client, invite(client)).status_code == 403  # type: ignore[attr-defined]


@pytest.mark.parametrize("missing", ["purpose_evaluation", "adult", "wired_headphones"])
def test_consent_requires_each_mandatory_box_ticked(client: TestClient, missing: str) -> None:
    """Im lặng không phải đồng ý: ô không tích là không đồng ý."""
    body = {**CONSENT, missing: False}
    assert client.post("/api/consent", params={"t": invite(client)}, json=body).status_code == 400


def test_an_unknown_dialect_is_refused(client: TestClient) -> None:
    body = {**CONSENT, "dialect": "saigon"}
    assert client.post("/api/consent", params={"t": invite(client)}, json=body).status_code == 400


# --- bản ghi âm -------------------------------------------------------------------------


def consented(client: TestClient) -> str:
    token = invite(client)
    assert client.post("/api/consent", params={"t": token}, json=CONSENT).status_code == 201
    return token


def test_a_valid_recording_is_stored_with_its_checksum_and_sidecar(
    client: TestClient, settings: Settings
) -> None:
    token = consented(client)
    response = upload(client, token)
    assert response.status_code == 201, response.text  # type: ignore[attr-defined]
    saved = response.json()  # type: ignore[attr-defined]

    audio = settings.data_dir / saved["file"]
    sidecar = json.loads(audio.with_suffix(".json").read_text(encoding="utf-8"))
    assert audio.read_bytes() == wav_bytes()
    assert sidecar["sha256"] == saved["sha256"]
    assert sidecar["layout"] == {"caller_channel": 0, "bot_channel": 1}
    assert sidecar["consent"]["dialect"] == "south"
    assert [entry["step"] for entry in sidecar["playback"]] == [0, 1]

    config = client.get("/api/config", params={"t": token}).json()
    assert SCRIPT not in {s["name"] for s in config["scripts"]}


@pytest.mark.parametrize(
    ("audio", "reason"),
    [
        (wav_bytes(channels=1), "channel"),
        (wav_bytes(rate=48000), "48000"),
        (b"RIFF not really a wav", "WAV"),
    ],
    ids=["mono", "48khz", "garbage"],
)
def test_audio_in_the_wrong_format_is_refused(
    client: TestClient, audio: bytes, reason: str
) -> None:
    response = upload(client, consented(client), audio=audio)
    assert response.status_code == 400  # type: ignore[attr-defined]
    assert reason in response.text  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "log",
    [
        playback(first_end=30000, second_start=24000),  # câu sau bắt đầu trước khi câu trước hết
        json.dumps([{"step": 0, "pressed_sample": 0, "start_sample": 0, "end_sample": RATE * 9}]),
        json.dumps([{"step": 5, "pressed_sample": 0, "start_sample": 0, "end_sample": 10}]),
        json.dumps([{"step": 0, "pressed_sample": 10, "start_sample": 5, "end_sample": 10}]),
        json.dumps([]),
        "not json",
    ],
    ids=["overlap", "past-end", "bad-step", "pressed-after-start", "empty", "not-json"],
)
def test_a_malformed_playback_log_is_refused(client: TestClient, log: str) -> None:
    assert upload(client, consented(client), playback=log).status_code == 400  # type: ignore[attr-defined]


def test_an_unknown_script_is_refused(client: TestClient) -> None:
    assert upload(client, consented(client), script="n9-nope").status_code == 404  # type: ignore[attr-defined]


def test_an_oversized_upload_is_refused(client: TestClient) -> None:
    big = wav_bytes(frames=RATE * 200)
    assert upload(client, consented(client), audio=big).status_code == 413  # type: ignore[attr-defined]


# --- giọng bot và xuất dữ liệu -----------------------------------------------------------


def test_prompts_are_mono_and_served_only_to_invited_participants(client: TestClient) -> None:
    files = {"audio": ("p.wav", wav_bytes(channels=1, frames=RATE), "audio/wav")}
    form = {"script": SCRIPT, "step": "0"}
    assert (
        client.post("/api/admin/prompts", data=form, files=files, headers=ADMIN).status_code == 201
    )

    stereo = {"audio": ("p.wav", wav_bytes(channels=2, frames=RATE), "audio/wav")}
    assert (
        client.post("/api/admin/prompts", data=form, files=stereo, headers=ADMIN).status_code == 400
    )

    token = invite(client)
    assert client.get(f"/api/prompts/{SCRIPT}/0.wav", params={"t": token}).status_code == 200
    assert client.get(f"/api/prompts/{SCRIPT}/0.wav", params={"t": "nope"}).status_code == 401

    lines = client.get("/api/admin/lines", headers=ADMIN).json()
    assert {(line["script"], line["step"]): line["recorded"] for line in lines}[(SCRIPT, 0)] is True


def test_export_contains_the_database_and_every_recording(client: TestClient) -> None:
    upload(client, consented(client))
    response = client.get("/api/admin/export", headers=ADMIN)
    assert response.status_code == 200

    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert "collector.sqlite3" in names
    assert any(name.startswith("sessions/S001/") and name.endswith(".wav") for name in names)
    assert any(name.endswith(".json") for name in names)


# --- rút lại đồng ý ---------------------------------------------------------------------


def test_withdrawal_deletes_recordings_and_consent_and_kills_the_link(
    client: TestClient, settings: Settings
) -> None:
    """Phiếu đồng ý hứa quyền rút lại và xoá (Luật 91/2025/QH15 Điều 10, 14)."""
    token = consented(client)
    saved = upload(client, token).json()  # type: ignore[attr-defined]
    audio = settings.data_dir / saved["file"]
    assert audio.exists()

    response = client.delete("/api/admin/speakers/S001", headers=ADMIN)
    assert response.status_code == 200, response.text
    assert response.json() == {"speaker_id": "S001", "recordings_deleted": 1}

    assert not audio.exists()
    assert not audio.with_suffix(".json").exists()
    assert client.get("/api/config", params={"t": token}).status_code == 401
    listed = {
        row["speaker_id"]: row for row in client.get("/api/admin/invites", headers=ADMIN).json()
    }
    assert listed["S001"]["withdrawn"] and listed["S001"]["recordings"] == 0


def test_speaker_ids_are_never_reused_after_a_withdrawal(client: TestClient) -> None:
    consented(client)
    client.delete("/api/admin/speakers/S001", headers=ADMIN)
    assert client.post("/api/admin/invites", headers=ADMIN).json()["speaker_id"] == "S002"


def test_withdrawing_an_unknown_speaker_is_404(client: TestClient) -> None:
    assert client.delete("/api/admin/speakers/S999", headers=ADMIN).status_code == 404


def test_a_non_ascii_admin_header_is_refused_not_a_server_error(client: TestClient) -> None:
    response = client.post("/api/admin/invites", headers={"X-Admin-Token": "tổng-đài".encode()})
    assert response.status_code == 401


# --- tình huống đã thu --------------------------------------------------------------------


def names_offered(client: TestClient, token: str) -> set[str]:
    return {s["name"] for s in client.get("/api/config", params={"t": token}).json()["scripts"]}


def test_a_recorded_scenario_is_no_longer_offered_to_that_speaker(client: TestClient) -> None:
    token = consented(client)
    assert SCRIPT in names_offered(client, token)
    assert upload(client, token).status_code == 201  # type: ignore[attr-defined]
    assert SCRIPT not in names_offered(client, token)
    config = client.get("/api/config", params={"t": token}).json()
    assert (config["done"], config["total"]) == (1, 9)


def test_a_second_upload_of_the_same_scenario_is_refused(client: TestClient) -> None:
    """Bấm gửi hai lần, hoặc hai tab cùng lúc, không được sinh ra hai bản ghi."""
    token = consented(client)
    assert upload(client, token).status_code == 201  # type: ignore[attr-defined]
    assert upload(client, token).status_code == 409  # type: ignore[attr-defined]


def test_other_speakers_still_see_a_scenario_someone_else_recorded(client: TestClient) -> None:
    upload(client, consented(client))
    assert SCRIPT in names_offered(client, consented(client))


def test_admin_lists_plays_and_deletes_recordings(client: TestClient, settings: Settings) -> None:
    token = consented(client)
    saved = upload(client, token).json()  # type: ignore[attr-defined]

    listed = client.get("/api/admin/recordings", headers=ADMIN).json()
    assert len(listed) == 1
    row = listed[0]
    assert (row["speaker_id"], row["script"], row["seconds"]) == ("S001", SCRIPT, 3.0)
    assert row["title"]

    audio = client.get(f"/api/admin/recordings/{row['id']}.wav", headers=ADMIN)
    assert audio.status_code == 200
    assert audio.content == wav_bytes()

    assert client.delete(f"/api/admin/recordings/{row['id']}", headers=ADMIN).status_code == 200
    assert not (settings.data_dir / saved["file"]).exists()
    assert client.get("/api/admin/recordings", headers=ADMIN).json() == []
    assert SCRIPT in names_offered(client, token)  # xoá xong thì tình huống hiện lại


def test_recording_routes_need_the_admin_token(client: TestClient) -> None:
    assert client.get("/api/admin/recordings").status_code == 401
    assert client.delete("/api/admin/recordings/1").status_code == 401


def test_deleting_an_unknown_recording_is_404(client: TestClient) -> None:
    assert client.delete("/api/admin/recordings/42", headers=ADMIN).status_code == 404
