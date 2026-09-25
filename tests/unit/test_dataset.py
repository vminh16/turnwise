"""Pha 1.5: nạp gói export, chia tập theo người nói, và holdout chỉ khoá được một lần."""

import hashlib
import io
import json
import zipfile
import zlib
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from evaluation import dataset
from turnwise.config import AudioConfig

RATE = 48_000


def recording(speaker: str, script: str, seconds: float = 0.3) -> tuple[bytes, dict[str, object]]:
    n = int(RATE * seconds)
    audio = np.zeros((n, 2), dtype=np.float32)
    # Mỗi bản một mức khác nhau: bản thu thật không bao giờ trùng sha256, bản giả thì dễ trùng.
    audio[:, 0] = (zlib.crc32((speaker + script).encode()) % 1000) / 10_000  # khách
    audio[: n // 2, 1] = 0.2  # bot nói nửa đầu
    buf = io.BytesIO()
    sf.write(buf, audio, RATE, format="WAV", subtype="PCM_16")
    wav = buf.getvalue()
    meta = {
        "speaker_id": speaker,
        "script": script,
        "sample_rate_hz": RATE,
        "sha256": hashlib.sha256(wav).hexdigest(),
        "playback": [{"step": 0, "start_sample": 0, "end_sample": n // 2}],
        "consent": {"dialect": "north", "wired_headphones": True},
    }
    return wav, meta


def export(tmp_path: Path, *items: tuple[str, str]) -> Path:
    path = tmp_path / f"export-{len(list(tmp_path.glob('export-*')))}.zip"
    with zipfile.ZipFile(path, "w") as z:
        for speaker, script in items:
            wav, meta = recording(speaker, script)
            stem = f"sessions/{speaker}/{script}-20260925T000000Z"
            z.writestr(stem + ".wav", wav)
            z.writestr(stem + ".json", json.dumps(meta))
    return path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "data").mkdir()
    return tmp_path


def ingest(root: Path, audio: AudioConfig, *items: tuple[str, str]) -> list[dataset.Recording]:
    return dataset.ingest(export(root, *items), audio, data=root / "data", root=root)


def test_ingest_writes_a_manifest_row_and_a_resampled_copy(root: Path, audio: AudioConfig) -> None:
    [rec] = ingest(root, audio, ("S005", "n1-a"))

    assert rec.split == "dev" and rec.playback == "headset" and rec.frames == int(RATE * 0.3)
    assert dataset.sha256(rec.raw(root)) == rec.sha256
    info = sf.info(rec.derived(root))
    assert (info.samplerate, info.channels) == (audio.sample_rate_hz, 2)
    assert dataset.read_manifest(root / "data") == [rec]
    assert dataset.check(root / "data", root) == []


def test_ingesting_the_same_export_twice_changes_nothing(root: Path, audio: AudioConfig) -> None:
    path = export(root, ("S005", "n1-a"))
    dataset.ingest(path, audio, data=root / "data", root=root)
    assert dataset.ingest(path, audio, data=root / "data", root=root) == []
    assert len(dataset.read_manifest(root / "data")) == 1


def test_frames_carry_the_bot_flag_from_the_playback_log(root: Path, audio: AudioConfig) -> None:
    [rec] = ingest(root, audio, ("S005", "n1-a"))
    flags = [f.bot_speaking for f in dataset.frame_source(rec, audio, root)]
    assert flags[0] and not flags[-1]


def test_lock_moves_whole_speakers_and_refuses_a_second_time(
    root: Path, audio: AudioConfig
) -> None:
    assert len(ingest(root, audio, ("S005", "n1-a"), ("S005", "n2-a"), ("S006", "n1-a"))) == 3
    dataset.lock(["S005"], data=root / "data", root=root)

    splits = {(r.speaker_id, r.split) for r in dataset.read_manifest(root / "data")}
    assert splits == {("S005", "holdout"), ("S006", "dev")}
    assert dataset.check(root / "data", root) == []
    with pytest.raises(RuntimeError):
        dataset.lock(["S006"], data=root / "data", root=root)


def test_script_authors_never_go_into_holdout(root: Path, audio: AudioConfig) -> None:
    ingest(root, audio, ("S002", "n1-a"))
    with pytest.raises(ValueError, match="S002"):
        dataset.lock(["S002"], data=root / "data", root=root)


def test_check_catches_a_modified_raw_file(root: Path, audio: AudioConfig) -> None:
    [rec] = ingest(root, audio, ("S005", "n1-a"))
    rec.raw(root).write_bytes(rec.raw(root).read_bytes() + b"\0\0")
    assert any("sha256" in p for p in dataset.check(root / "data", root))
