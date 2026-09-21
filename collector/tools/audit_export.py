"""Kiểm chất lượng một file export của collector, trước khi đưa vào pipeline.

    uv run python tools/audit_export.py <export.zip>

Không sửa gì. In ra từng kiểm tra, và thoát mã 1 nếu có kiểm tra hỏng. Chạy lại được trên dữ liệu
thật: mọi ngưỡng ở đây là ngưỡng về **tính toàn vẹn** (file khớp database, nhật ký khớp tín hiệu),
không phải ngưỡng về nội dung lời nói.
"""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import wave
import zipfile
from itertools import pairwise
from pathlib import Path

import numpy as np

PCM16_MAX = 32767
BOT_SILENCE_TOLERANCE = 2  # sai số lượng tử khi trình duyệt ghi lại một mẫu PCM16


class Audit:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.lines: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        self.lines.append(f"  [{'ok' if ok else 'FAIL'}] {label}{f' — {detail}' if detail else ''}")
        if not ok:
            self.failures.append(label)

    def info(self, text: str) -> None:
        self.lines.append(f"  {text}")


def read_wav(data: bytes) -> tuple[tuple[int, int, int], np.ndarray]:
    with wave.open(io.BytesIO(data)) as wav:
        shape = (wav.getnchannels(), wav.getframerate(), wav.getsampwidth())
        samples = np.frombuffer(wav.readframes(wav.getnframes()), np.int16)
    return shape, samples.reshape(-1, shape[0])


def audit(export: Path, rate: int = 48000) -> Audit:
    result = Audit()
    bundle = zipfile.ZipFile(export)
    names = set(bundle.namelist())
    with tempfile.TemporaryDirectory() as scratch:
        db_path = Path(scratch) / "collector.sqlite3"
        db_path.write_bytes(bundle.read("collector.sqlite3"))
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        try:
            run(result, db, bundle, names, rate)
        finally:
            db.close()
    return result


def run(
    result: Audit, db: sqlite3.Connection, bundle: zipfile.ZipFile, names: set[str], rate: int
) -> None:
    result.info("database")
    result.check(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "integrity_check")
    result.check(not db.execute("PRAGMA foreign_key_check").fetchall(), "foreign_key_check")

    invites = {row["speaker_id"]: row for row in db.execute("SELECT * FROM invites")}
    consents = {
        row["speaker_id"]: json.loads(row["record"]) for row in db.execute("SELECT * FROM consents")
    }
    recordings = db.execute("SELECT * FROM recordings ORDER BY id").fetchall()
    prompts = {row["key"]: row for row in db.execute("SELECT * FROM prompts")}
    result.info(
        f"{len(invites)} invites, {len(consents)} consents, {len(recordings)} recordings, "
        f"{len(prompts)} prompts"
    )
    result.check(
        len({row["token"] for row in invites.values()}) == len(invites), "invite tokens unique"
    )
    withdrawn = {sid for sid, row in invites.items() if row["withdrawn_at"]}
    result.check(
        not withdrawn & set(consents), "withdrawn speakers have no consent left", str(withdrawn)
    )

    result.info("prompts")
    prompt_audio: dict[str, np.ndarray] = {}
    for key, row in sorted(prompts.items()):
        if row["file"] not in names:
            result.check(False, f"prompt {key} file present")
            continue
        data = bundle.read(row["file"])
        shape, samples = read_wav(data)
        result.check(
            hashlib.sha256(data).hexdigest() == row["sha256"] and shape == (1, rate, 2),
            f"prompt {key}: sha256 and mono PCM16 {rate} Hz",
            f"{len(samples) / rate:.2f}s",
        )
        prompt_audio[key] = samples[:, 0]

    referenced: set[str] = set()
    for row in recordings:
        label = f"recording #{row['id']} {row['speaker_id']}/{row['script']}"
        result.info(label)
        wav_name, json_name = row["file"], row["file"][: -len(".wav")] + ".json"
        referenced |= {wav_name, json_name}
        if wav_name not in names or json_name not in names:
            result.check(False, "wav and sidecar present")
            continue
        data = bundle.read(wav_name)
        sidecar = json.loads(bundle.read(json_name))
        shape, audio = read_wav(data)
        digest = hashlib.sha256(data).hexdigest()

        result.check(
            row["speaker_id"] not in withdrawn, "speaker has not withdrawn", row["speaker_id"]
        )
        result.check(row["speaker_id"] in consents, "speaker has consent on record")
        result.check(sidecar["consent"] == consents.get(row["speaker_id"]), "sidecar consent = db")
        result.check(
            digest == row["sha256"] == sidecar["sha256"] and len(data) == row["bytes"],
            "sha256 and size: file = db = sidecar",
        )
        result.check(
            shape == (2, rate, 2) and sidecar["sample_rate_hz"] == rate,
            f"stereo PCM16 {rate} Hz, sidecar agrees",
            str(shape),
        )
        result.check(len(audio) == row["frames"], "frames = db", f"{len(audio)} vs {row['frames']}")
        result.check(
            sidecar["speaker_id"] == row["speaker_id"] and sidecar["script"] == row["script"],
            "sidecar speaker and script = db",
        )

        log = sidecar["playback"]
        steps = [entry["step"] for entry in log]
        ordered = all(
            0 <= e["pressed_sample"] <= e["start_sample"] < e["end_sample"] <= len(audio)
            for e in log
        ) and all(a["end_sample"] <= b["start_sample"] for a, b in pairwise(log))
        result.check(steps == sorted(set(steps)) and ordered, "playback log ordered, inside file")

        caller = audio[:, sidecar["layout"]["caller_channel"]].astype(np.int32)
        bot = audio[:, sidecar["layout"]["bot_channel"]].astype(np.int32)
        mask = np.ones(len(audio), bool)
        worst = 0
        for entry in log:
            mask[entry["start_sample"] : entry["end_sample"]] = False
            prompt = prompt_audio.get(f"{row['script']}/{entry['step']}")
            if prompt is not None and len(prompt) == entry["end_sample"] - entry["start_sample"]:
                segment = bot[entry["start_sample"] : entry["end_sample"]]
                worst = max(worst, int(np.abs(segment - prompt.astype(np.int32)).max()))
            else:
                worst = PCM16_MAX
        result.check(
            worst <= BOT_SILENCE_TOLERANCE,
            "bot channel = prompt sample for sample at logged positions",
            f"max error {worst}",
        )
        outside = int(np.abs(bot[mask]).max()) if mask.any() else 0
        result.check(
            outside <= BOT_SILENCE_TOLERANCE, "bot channel silent outside the log", f"max {outside}"
        )

        rms = float(np.sqrt(np.mean((caller / 32768.0) ** 2)))
        clipped = float(np.mean(np.abs(caller) >= PCM16_MAX))
        result.check(rms > 0.001, "caller channel not silent", f"rms {rms:.3f}")
        result.check(
            clipped < 0.001, "caller channel not clipping", f"{100 * clipped:.3f}% clipped"
        )
        result.info(
            f"    {len(audio) / rate:.2f}s, {len(log)} bot lines, "
            f"dc {caller.mean() / 32768:+.4f}, "
            f"latency base {sidecar['client'].get('base_latency_s')}s "
            f"output {sidecar['client'].get('output_latency_s')}s"
        )

    session_files = {
        name for name in names if name.startswith("sessions/") and not name.endswith("/")
    }
    prompt_files = {
        name for name in names if name.startswith("prompts/") and not name.endswith("/")
    }
    result.info("files")
    result.check(
        session_files == referenced,
        "no orphan session files",
        str(sorted(session_files - referenced)),
    )
    result.check(
        prompt_files == {row["file"] for row in prompts.values()}, "no orphan prompt files"
    )


def main() -> int:
    if len(sys.argv) not in (2, 3):
        sys.stderr.write("usage: audit_export.py <export.zip> [sample_rate_hz, default 48000]\n")
        return 2
    result = audit(Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) == 3 else 48000)
    sys.stdout.write("\n".join(result.lines) + "\n")
    sys.stdout.write(f"{len(result.failures)} failed checks\n")
    return 1 if result.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
