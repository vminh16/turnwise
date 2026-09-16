"""Luồng thật từ đầu tới cuối: Chrome thật, micro giả, giọng bot giả, server thật.

Chạy: `COLLECTOR_E2E=1 uv run pytest tests/e2e -v`. Mặc định server được dựng tại chỗ trên một
cổng trống; đặt `COLLECTOR_E2E_URL` và `COLLECTOR_E2E_ADMIN_TOKEN` để chạy vào một server khác
(ví dụ container Docker).

Tín hiệu giả được chọn để mỗi lỗi có một dấu vết riêng:

- **Giọng bot** là sóng sin 440 Hz (bước 0, có một chỗ ngắt hơi im tuyệt đối ở giữa) và 660 Hz
  (bước 1). Kênh bot trong file phải **trùng từng mẫu** với file đã upload, tại đúng vị trí
  nhật ký ghi. Lệch một mẫu là sóng sin lệch pha, sai số nhảy vọt.
- **Micro giả** phát 1500 Hz. Kênh khách phải có 1500 Hz và **không** có 440/660 Hz: có nghĩa là
  tiếng bot đã lọt vào kênh khách.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import wave
import zipfile
from collections.abc import Iterator
from pathlib import Path

import httpx
import numpy as np
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("COLLECTOR_E2E") != "1", reason="set COLLECTOR_E2E=1 to run the browser flow"
)

RATE = 16000
SCRIPT = "n5-a-agent-first"
SCRIPT_TITLE = "Gặp nhân viên, nói đè ngay từ lời chào"
BOT_FREQS = (440.0, 660.0)
MIC_FREQ = 1500.0
LEAD_SAMPLES = 1600  # COLLECTOR_PLAYBACK_LEAD_MS=100 mặc định
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def sine(freq: float, seconds: float, rate: int, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(round(seconds * rate)) / rate
    return (amplitude * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)


def wav_bytes(samples: np.ndarray, rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(samples.tobytes())
    return buffer.getvalue()


def bot_prompts() -> list[np.ndarray]:
    first = np.concatenate(
        [sine(440, 0.5, RATE), np.zeros(RATE * 3 // 10, np.int16), sine(440, 0.4, RATE)]
    )
    return [first, sine(660, 0.8, RATE)]


def dominant_freq(signal: np.ndarray, rate: int) -> float:
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal))))
    return float(np.fft.rfftfreq(len(signal), 1 / rate)[int(np.argmax(spectrum))])


def band_energy(signal: np.ndarray, rate: int, freq: float) -> float:
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal)))) ** 2
    freqs = np.fft.rfftfreq(len(signal), 1 / rate)
    return float(spectrum[np.abs(freqs - freq) < 20].sum() / spectrum.sum())


# --- server ------------------------------------------------------------------------------


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def server() -> Iterator[tuple[str, str]]:
    url = os.environ.get("COLLECTOR_E2E_URL")
    if url:
        yield url.rstrip("/"), os.environ["COLLECTOR_E2E_ADMIN_TOKEN"]
        return
    token = secrets.token_urlsafe(24)
    port = free_port()
    with tempfile.TemporaryDirectory() as data_dir:
        env = {**os.environ, "COLLECTOR_ADMIN_TOKEN": token, "COLLECTOR_DATA_DIR": data_dir}
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app_factory",
                "--factory",
                "--port",
                str(port),
            ],
            cwd=Path(__file__).resolve().parents[2],
            env=env,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            for _ in range(100):
                try:
                    httpx.get(base, timeout=0.5)
                    break
                except httpx.TransportError:
                    time.sleep(0.1)
            yield base, token
        finally:
            process.terminate()
            process.wait(timeout=10)


# --- luồng -------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def recorded(server: tuple[str, str], tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Chạy trọn một buổi thu trong Chrome, trả về mọi thứ cần kiểm."""
    from playwright.sync_api import sync_playwright

    base, token = server
    admin = {"X-Admin-Token": token}
    prompts = bot_prompts()
    for step, samples in enumerate(prompts):
        response = httpx.post(
            f"{base}/api/admin/prompts",
            headers=admin,
            data={"script": SCRIPT, "step": str(step)},
            files={"audio": ("p.wav", wav_bytes(samples, RATE), "audio/wav")},
        )
        assert response.status_code == 201, response.text
    invite = httpx.post(f"{base}/api/admin/invites", headers=admin).json()

    work = tmp_path_factory.mktemp("e2e")
    mic = work / "mic.wav"
    mic.write_bytes(wav_bytes(sine(MIC_FREQ, 20, 48000, amplitude=0.3), 48000))

    console: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=str(CHROME) if CHROME.exists() else None,
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                f"--use-file-for-fake-audio-capture={mic}",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )
        page = browser.new_page()
        page.on("console", lambda msg: console.append(f"{msg.type}: {msg.text}"))
        page.on("pageerror", lambda error: console.append(f"pageerror: {error}"))
        page.goto(f"{base}/?t={invite['token']}")

        consent_locked = page.is_disabled("#consent-submit")  # chưa tích gì thì chưa cho đi tiếp
        page.check("input[name=purpose_evaluation]")
        page.check("input[name=adult]")
        page.check("input[name=wired_headphones]")
        page.get_by_text("Bắc", exact=True).click()
        page.click("#consent-submit")

        page.wait_for_selector("#mic:not([hidden])")
        page.click("#mic-start")
        page.wait_for_function("!document.getElementById('mic-ok').disabled", timeout=10000)
        mic_warning_hidden = page.is_hidden("#banner")
        page.click("#mic-ok")

        page.wait_for_selector("#list:not([hidden])")
        offered_before = page.text_content("#scenario-list")
        page.locator(".scenario", has_text=SCRIPT_TITLE).get_by_role("button").click()
        # Lỗi đã gặp: nút bấm được trong lúc đang tải giọng bot, cú bấm bị nuốt mất.
        disabled_while_loading = page.is_disabled("#run-next")
        button = page.locator("#run-next")
        page.wait_for_function("document.getElementById('run-next').textContent === 'Bắt đầu'")
        button.click()  # bắt đầu ghi + bước 0
        page.wait_for_selector("#run-recorder.recording")
        recording_indicator = page.is_visible("#run-recorder.recording .rec-dot")
        page.wait_for_function("!document.getElementById('run-next').disabled", timeout=10000)
        instruction_0 = page.text_content("#run-instruction")
        page.wait_for_timeout(700)  # khách "nói"
        button.click()  # bước 1
        page.wait_for_function(
            "document.getElementById('run-next').textContent === 'Kết thúc'", timeout=10000
        )
        page.wait_for_timeout(500)
        button.click()  # kết thúc -> nghe lại
        page.wait_for_selector("#review:not([hidden])", timeout=20000)
        review_audio_ready = page.eval_on_selector(
            "#review-audio", "a => a.src.startsWith('blob:')"
        )
        uploaded_before_send = httpx.get(f"{base}/api/admin/recordings", headers=admin).json()
        page.click("#review-send")
        page.wait_for_selector("#list:not([hidden]), #message:not([hidden])", timeout=20000)
        offered_after = page.text_content("#scenario-list")
        browser.close()

    export = httpx.get(f"{base}/api/admin/export", headers=admin, timeout=60)
    assert export.status_code == 200
    bundle = zipfile.ZipFile(io.BytesIO(export.content))
    bundle.extractall(work / "export")
    return {
        "work": work / "export",
        "speaker_id": invite["speaker_id"],
        "prompts": prompts,
        "console": console,
        "mic_warning_hidden": mic_warning_hidden,
        "disabled_while_loading": disabled_while_loading,
        "instruction_0": instruction_0,
        "consent_locked": consent_locked,
        "recording_indicator": recording_indicator,
        "review_audio_ready": review_audio_ready,
        "uploaded_before_send": uploaded_before_send,
        "offered_before": offered_before,
        "offered_after": offered_after,
        "base": base,
        "token": token,
        "mic": mic,
        "invite_token": invite["token"],
    }


def test_consent_cannot_be_submitted_empty(recorded: dict) -> None:
    assert recorded["consent_locked"]


def test_recording_shows_a_live_indicator(recorded: dict) -> None:
    assert recorded["recording_indicator"]


def test_nothing_is_uploaded_until_the_participant_listens_and_sends(recorded: dict) -> None:
    assert recorded["review_audio_ready"]
    assert recorded["uploaded_before_send"] == []


def test_a_sent_scenario_disappears_from_the_participant_list(recorded: dict) -> None:
    assert SCRIPT_TITLE in recorded["offered_before"]
    assert SCRIPT_TITLE not in recorded["offered_after"]


def test_admin_records_a_bot_line_and_deleting_a_recording_brings_the_scenario_back(
    recorded: dict,
) -> None:
    """Luồng quản trị qua giao diện thật: thu, nghe lại, lưu; xoá bản ghi thì tình huống hiện lại"""
    from playwright.sync_api import sync_playwright

    base, token = recorded["base"], recorded["token"]
    admin = {"X-Admin-Token": token}
    before = {
        (line["script"], line["step"]): line["recorded"]
        for line in httpx.get(f"{base}/api/admin/lines", headers=admin).json()
    }
    target = ("n1-a-outage-reading-number", 0)
    assert before[target] is False

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=str(CHROME) if CHROME.exists() else None,
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                f"--use-file-for-fake-audio-capture={recorded['mic']}",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )
        page = browser.new_page()
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(f"{base}/admin")
        page.fill("#token", token)
        page.click("#login-form button[type=submit]")
        page.wait_for_selector("#panel:not([hidden])")

        group = page.locator("details[data-script='n1-a-outage-reading-number']")
        if not group.evaluate("d => d.open"):
            group.locator("summary").click()
        row = group.locator(".row").first
        row.get_by_role("button", name="Thu", exact=True).click()
        page.wait_for_selector(".panel .recorder.recording")
        page.wait_for_timeout(1200)
        row.get_by_role("button", name="Dừng").click()
        assert row.locator(".panel audio").count() == 1
        assert row.get_by_text("Chưa lưu").is_visible()
        row.get_by_role("button", name="Lưu").click()
        page.wait_for_function(
            "document.getElementById('banner').textContent.includes('Đã lưu câu 1')"
        )

        page.locator("#recordings tr", has_text=SCRIPT_TITLE).get_by_role(
            "button", name="Xoá"
        ).click()
        page.wait_for_function(
            "document.getElementById('banner').textContent.includes('Đã xoá bản ghi')"
        )
        browser.close()

    after = {
        (line["script"], line["step"]): line["recorded"]
        for line in httpx.get(f"{base}/api/admin/lines", headers=admin).json()
    }
    assert after[target] is True
    assert httpx.get(f"{base}/api/admin/recordings", headers=admin).json() == []
    offered = httpx.get(f"{base}/api/config", params={"t": recorded["invite_token"]}).json()
    assert SCRIPT in {script["name"] for script in offered["scripts"]}


def db_rows(export: Path, sql: str, *args: object) -> list[sqlite3.Row]:
    connection = sqlite3.connect(export / "collector.sqlite3")
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(sql, args).fetchall()
    finally:
        connection.close()


def the_recording(recorded: dict) -> tuple[sqlite3.Row, np.ndarray, dict]:
    rows = db_rows(
        recorded["work"], "SELECT * FROM recordings WHERE speaker_id = ?", recorded["speaker_id"]
    )
    assert len(rows) == 1
    row = rows[0]
    path = recorded["work"] / row["file"]
    with wave.open(str(path)) as wav:
        assert (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) == (2, RATE, 2)
        audio = np.frombuffer(wav.readframes(wav.getnframes()), np.int16).reshape(-1, 2)
    sidecar = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    return row, audio, sidecar


# --- kiểm tra ----------------------------------------------------------------------------


def test_the_page_ran_without_errors(recorded: dict) -> None:
    errors = [line for line in recorded["console"] if line.startswith(("error", "pageerror"))]
    assert not errors, errors


def test_the_call_button_is_locked_until_the_bot_voice_has_loaded(recorded: dict) -> None:
    assert recorded["disabled_while_loading"]


def test_chrome_honoured_raw_microphone_constraints(recorded: dict) -> None:
    assert recorded["mic_warning_hidden"]


def test_instructions_follow_the_bot_line(recorded: dict) -> None:
    assert "gặp người thật" in recorded["instruction_0"]


def test_database_row_matches_the_file_and_sidecar(recorded: dict) -> None:
    row, audio, sidecar = the_recording(recorded)
    data = (recorded["work"] / row["file"]).read_bytes()
    assert row["script"] == SCRIPT
    assert row["frames"] == len(audio)
    assert row["bytes"] == len(data)
    assert row["sha256"] == hashlib.sha256(data).hexdigest() == sidecar["sha256"]
    assert sidecar["speaker_id"] == recorded["speaker_id"]
    assert sidecar["consent"]["dialect"] == "north"
    assert sidecar["client"]["track_settings"]["echoCancellation"] is False


def test_consent_and_prompts_are_in_the_database(recorded: dict) -> None:
    consent = db_rows(
        recorded["work"], "SELECT record FROM consents WHERE speaker_id = ?", recorded["speaker_id"]
    )
    assert len(consent) == 1
    record = json.loads(consent[0]["record"])
    assert record["purpose_evaluation"] is True and record["purpose_excerpts"] is False
    keys = {r["key"] for r in db_rows(recorded["work"], "SELECT key FROM prompts")}
    assert {f"{SCRIPT}/0", f"{SCRIPT}/1"} <= keys


def test_playback_log_has_both_steps_with_the_configured_lead(recorded: dict) -> None:
    _, audio, sidecar = the_recording(recorded)
    log = sidecar["playback"]
    assert [entry["step"] for entry in log] == [0, 1]
    for entry, prompt in zip(log, recorded["prompts"], strict=True):
        assert entry["end_sample"] - entry["start_sample"] == len(prompt)
        assert abs(entry["start_sample"] - entry["pressed_sample"] - LEAD_SAMPLES) <= 1
        assert entry["end_sample"] <= len(audio)


def test_bot_channel_is_the_uploaded_prompt_sample_for_sample(recorded: dict) -> None:
    _, audio, sidecar = the_recording(recorded)
    bot = audio[:, 1].astype(np.int32)
    for entry, prompt in zip(sidecar["playback"], recorded["prompts"], strict=True):
        segment = bot[entry["start_sample"] : entry["end_sample"]]
        error = np.abs(segment - prompt.astype(np.int32)).max()
        assert error <= 2, f"step {entry['step']}: max sample error {error}"


def test_bot_channel_is_silent_outside_the_logged_intervals(recorded: dict) -> None:
    _, audio, sidecar = the_recording(recorded)
    mask = np.ones(len(audio), bool)
    for entry in sidecar["playback"]:
        mask[entry["start_sample"] : entry["end_sample"]] = False
    assert np.abs(audio[mask, 1]).max() <= 2


def test_caller_channel_carries_the_microphone_and_not_the_bot(recorded: dict) -> None:
    _, audio, sidecar = the_recording(recorded)
    caller = audio[:, 0].astype(np.float64) / 32768
    assert np.sqrt(np.mean(caller**2)) > 0.05
    assert abs(dominant_freq(caller, RATE) - MIC_FREQ) < 20
    first = sidecar["playback"][0]
    during_bot = caller[first["start_sample"] : first["end_sample"]]
    assert all(band_energy(during_bot, RATE, freq) < 0.01 for freq in BOT_FREQS)
