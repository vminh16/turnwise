"""Pha 1.5: gói export của collector thành bộ dữ liệu có manifest, chia tập theo người nói.

    uv run python -m evaluation.dataset ingest <export.zip>   # nạp bản thu, mọi người vào dev
    uv run python -m evaluation.dataset lock S005 S009        # chuyển hai người sang holdout
    uv run python -m evaluation.dataset check                 # kiểm manifest khớp file

Bản thô 48 kHz vào `data/raw/<người nói>/` và không bao giờ bị sửa. Cạnh mỗi bản là một bản
`.16k.wav` cùng hai kênh, lấy mẫu lại theo `audio.sample_rate_hz` của config để `WavFrameSource`
đọc thẳng; bản này sinh lại được nên không cần giữ gìn.

Tập chia theo **người nói**, không theo bản thu. Ai mới nạp cũng vào `dev`; `lock` chuyển cả thư
mục của người đó sang `data/holdout/` và chỉ chạy được một lần. Tác giả kịch bản không bao giờ
vào holdout: họ biết trước lời bot nên phản ứng không tự nhiên.

`data/manifests/recordings.csv` là thứ được commit: đủ để kiểm bộ dữ liệu khớp hay không mà
không cần file âm thanh.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import zipfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from math import gcd
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from turnwise.audio.source import WavFrameSource
from turnwise.config import AudioConfig

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
AUTHORS = frozenset({"S001", "S002"})  # người viết kịch bản (docs/progress.md)
DEV, LOCKED = "dev", "holdout"
DERIVED_SUFFIX = ".16k.wav"


@dataclass(frozen=True)
class Recording:
    path: str  # tương đối so với gốc repo, dấu "/"
    sha256: str
    speaker_id: str
    script: str
    frames: int
    sample_rate_hz: int
    dialect: str
    playback: str  # headset | loudspeaker
    split: str

    def raw(self, root: Path = REPO) -> Path:
        return root / self.path

    def derived(self, root: Path = REPO) -> Path:
        return self.raw(root).with_suffix(DERIVED_SUFFIX)

    def sidecar(self, root: Path = REPO) -> dict[str, Any]:
        meta: dict[str, Any] = json.loads(self.raw(root).with_suffix(".json").read_text("utf-8"))
        return meta


def manifest_path(data: Path) -> Path:
    return data / "manifests" / "recordings.csv"


def read_manifest(data: Path = DATA) -> list[Recording]:
    path = manifest_path(data)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    ints = {"frames", "sample_rate_hz"}
    return [Recording(**{k: int(v) if k in ints else v for k, v in r.items()}) for r in rows]  # type: ignore[arg-type]


def write_manifest(recordings: Sequence[Recording], data: Path = DATA) -> None:
    path = manifest_path(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(Recording.__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for rec in sorted(recordings, key=lambda r: r.path):
            writer.writerow(asdict(rec))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def derive(raw: Path, target_rate_hz: int) -> Path:
    """Ghi bản hai kênh lấy mẫu lại cạnh bản thô; bản thô không đổi."""
    audio, rate = sf.read(raw, dtype="float32", always_2d=True)
    step = gcd(rate, target_rate_hz)
    resampled = resample_poly(audio, target_rate_hz // step, rate // step, axis=0)
    out = raw.with_suffix(DERIVED_SUFFIX)
    sf.write(out, np.clip(resampled, -1.0, 1.0), target_rate_hz, subtype="PCM_16")
    return out


def ingest(
    export: Path, audio: AudioConfig, data: Path = DATA, root: Path = REPO
) -> list[Recording]:
    """Nạp mọi bản thu trong gói export. Nạp lại cùng gói thì không đổi gì."""
    known = {r.sha256: r for r in read_manifest(data)}
    added: list[Recording] = []
    with zipfile.ZipFile(export) as z:
        wavs = [n for n in z.namelist() if n.startswith("sessions/") and n.endswith(".wav")]
        for name in wavs:
            meta = json.loads(z.read(name[: -len(".wav")] + ".json"))
            if meta["sha256"] in known:
                continue
            speaker = meta["speaker_id"]
            dest = data / "raw" / speaker / Path(name).name
            if dest.exists():
                raise FileExistsError(
                    f"{dest} exists with other content; raw files are never overwritten"
                )
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(name))
            dest.with_suffix(".json").write_bytes(z.read(name[: -len(".wav")] + ".json"))
            digest = sha256(dest)
            if digest != meta["sha256"]:
                raise ValueError(f"{name}: sha256 in the export does not match the file")
            info = sf.info(dest)
            derive(dest, audio.sample_rate_hz)
            consent = meta["consent"]
            rec = Recording(
                path=dest.relative_to(root).as_posix(),
                sha256=digest,
                speaker_id=speaker,
                script=meta["script"],
                frames=info.frames,
                sample_rate_hz=info.samplerate,
                dialect=consent["dialect"],
                playback="headset" if consent.get("wired_headphones") else "loudspeaker",
                split=DEV,
            )
            known[digest] = rec
            added.append(rec)
    write_manifest(list(known.values()), data)
    return added


def lock(speakers: Sequence[str], data: Path = DATA, root: Path = REPO) -> None:
    """Chuyển những người nói này sang holdout. Chỉ làm được một lần."""
    recordings = read_manifest(data)
    if any(r.split == LOCKED for r in recordings):
        raise RuntimeError("holdout is already locked; speakers cannot be added later")
    if authors := AUTHORS & set(speakers):
        raise ValueError(f"{sorted(authors)} wrote the scripts and never go into holdout")
    present = {r.speaker_id for r in recordings}
    if missing := set(speakers) - present:
        raise ValueError(f"no recordings for {sorted(missing)}")
    updated = []
    for rec in recordings:
        if rec.speaker_id in speakers:
            src = rec.raw(root)
            dest = data / LOCKED / rec.speaker_id / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            for suffix in (".wav", ".json", DERIVED_SUFFIX, ".TextGrid"):
                if src.with_suffix(suffix).exists():  # nhãn đi theo âm thanh, nếu đã có
                    shutil.move(src.with_suffix(suffix), dest.with_suffix(suffix))
            rec = Recording(
                **{**asdict(rec), "path": dest.relative_to(root).as_posix(), "split": LOCKED}
            )
        updated.append(rec)
    write_manifest(updated, data)


def check(data: Path = DATA, root: Path = REPO) -> list[str]:
    """Danh sách lỗi; rỗng là khớp manifest. Lời nhắn tiếng Anh vì in ra console Windows.

    Bản holdout không bị mở ra để băm: sha256 của nó đã ghi lúc nạp, khi còn ở `dev`, và
    holdout chỉ được đọc khi làm báo cáo cuối (`.claude/rules/evaluation.md`).
    """
    problems: list[str] = []
    splits: dict[str, set[str]] = {}
    for rec in read_manifest(data):
        splits.setdefault(rec.speaker_id, set()).add(rec.split)
        if rec.split == LOCKED:
            if rec.speaker_id in AUTHORS:
                problems.append(f"{rec.path}: a script author is in holdout")
            continue
        if not rec.raw(root).exists():
            problems.append(f"{rec.path}: file missing")
            continue
        if sha256(rec.raw(root)) != rec.sha256:
            problems.append(f"{rec.path}: sha256 does not match the manifest")
        if not rec.derived(root).exists():
            problems.append(f"{rec.path}: {DERIVED_SUFFIX} copy missing")
    problems += [
        f"{s}: in more than one split {sorted(v)}" for s, v in splits.items() if len(v) > 1
    ]
    return problems


def recordings(split: str, data: Path = DATA) -> list[Recording]:
    return [r for r in read_manifest(data) if r.split == split]


def frame_source(rec: Recording, audio: AudioConfig, root: Path = REPO) -> WavFrameSource:
    """Khung của tiếng khách, cờ `bot_speaking` lấy từ log phát."""
    rate = rec.sample_rate_hz
    intervals = [
        (e["start_sample"] / rate, e["end_sample"] / rate) for e in rec.sidecar(root)["playback"]
    ]
    return WavFrameSource(rec.derived(root), audio, bot_intervals=intervals)


def main(argv: Sequence[str] | None = None) -> int:
    from turnwise.config import load_settings

    parser = argparse.ArgumentParser(prog="evaluation.dataset")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest").add_argument("export", type=Path, nargs="+")
    sub.add_parser("lock").add_argument("speakers", nargs="+")
    sub.add_parser("check")
    args = parser.parse_args(argv)

    if args.command == "ingest":
        audio = load_settings().audio
        for export in args.export:
            added = ingest(export, audio)
            sys.stdout.write(f"{export.name}: {len(added)} new recordings\n")
    elif args.command == "lock":
        lock(args.speakers)
    problems = check()
    for problem in problems:
        sys.stdout.write(problem + "\n")
    counts = {s: len(recordings(s)) for s in (DEV, LOCKED)}
    sys.stdout.write(f"{counts}, {len(problems)} problems\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
