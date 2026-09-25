"""Pha 1.6: bản nháp TextGrid cho người gán nhãn, và đọc lại nhãn người đã gán.

    uv run python -m evaluation.annotation prepare            # mọi bản dev chưa có TextGrid
    uv run python -m evaluation.annotation prepare --no-asr   # bỏ lớp chép lời nháp, nhanh hơn
    uv run python -m evaluation.annotation status             # đã gán bao nhiêu

Mỗi bản thu nhận một file `.TextGrid` nằm cạnh file wav, nên Praat mở cả hai cùng thư mục và
`dataset.lock` chuyển nhãn theo âm thanh. **Không bao giờ ghi đè** một TextGrid đã có: đó là
công của người gán.

Năm lớp, theo `docs/annotation-guide.md` §4:

- `bot` — khoảng bot phát, nhãn là số bước. Lấy từ log phát, đúng tới từng mẫu; không sửa.
- `caller_act` — mỗi đoạn nói của khách (IPU) là một khoảng mang nhãn `?`. Người gán **sửa ranh
  giới ngay trên lớp này** và thay `?` bằng một nhãn của §4.3, thuộc tính viết sau cách một dấu
  cách: `hold filled`, `take agent`.
- `caller_words` — cùng ranh giới ban đầu, để trống cho người gán chép lời theo §5.1.
- `asr_draft` — chép lời tự động, chỉ để gõ nhanh hơn. Không phải nhãn.
- `nonspeech` — trống, cho ho, cười, tiếng bot vọng (§4.2).

Praat lưu file có chữ Việt bằng UTF-16; `read_textgrid` đọc được cả UTF-16 lẫn UTF-8.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from evaluation import dataset
from turnwise.config import AnnotationConfig

ACTS = frozenset({"hold", "take", "backchannel", "barge_in", "aside"})
ATTRIBUTES = frozenset({"agent", "explicit", "filled", "cut_in"})
UNLABELLED = "?"
TIERS = ("bot", "caller_act", "caller_words", "asr_draft", "nonspeech")

Interval = tuple[float, float, str]


# --- IPU nháp --------------------------------------------------------------------------


def ipus(caller: np.ndarray, rate: int, config: AnnotationConfig) -> list[tuple[float, float]]:
    """Khoảng có tiếng theo năng lượng, gộp lặng ngắn và bỏ đoạn quá ngắn (§4.1)."""
    size = rate * config.vad_frame_ms // 1000
    n = len(caller) // size * size
    rms = np.sqrt(np.mean(caller[:n].reshape(-1, size).astype(np.float64) ** 2, axis=1))
    loud = 20 * np.log10(np.maximum(rms, 1e-12)) > config.vad_floor_dbfs
    edges = np.flatnonzero(np.diff(np.concatenate([[0], loud.astype(np.int8), [0]])))
    merged: list[list[int]] = []
    for start, end in zip(edges[::2], edges[1::2], strict=True):
        if merged and (start - merged[-1][1]) * config.vad_frame_ms < config.ipu_merge_ms:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    step = config.vad_frame_ms / 1000
    return [
        (round(s * step, 3), round(e * step, 3))
        for s, e in merged
        if (e - s) * config.vad_frame_ms >= config.ipu_min_ms
    ]


def asr_draft(caller: np.ndarray, rate: int, config: AnnotationConfig) -> list[Interval]:
    """Chép lời tự động theo đoạn. Chỉ chạy khi có mô hình của asr-check/."""
    from faster_whisper import WhisperModel
    from scipy.signal import resample_poly

    if not (config.asr_model_dir / "model.bin").exists():
        raise FileNotFoundError(f"{config.asr_model_dir} missing; run asr-check once, or --no-asr")
    audio = resample_poly(caller, 16_000, rate).astype(np.float32) if rate != 16_000 else caller
    model = WhisperModel(str(config.asr_model_dir), device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        audio, language="vi", beam_size=5, vad_filter=True, condition_on_previous_text=False
    )
    return [(round(s.start, 3), round(s.end, 3), s.text.strip()) for s in segments]


# --- TextGrid ---------------------------------------------------------------------------


def fill(intervals: Sequence[Interval], xmax: float) -> list[Interval]:
    """Chèn khoảng trống để lớp phủ kín [0, xmax], như Praat đòi."""
    out: list[Interval] = []
    t = 0.0
    for start, end, text in sorted(intervals):
        start, end = max(start, t), min(end, xmax)
        if end <= start:
            continue
        if start > t:
            out.append((t, start, ""))
        out.append((start, end, text))
        t = end
    if t < xmax:
        out.append((t, xmax, ""))
    return out


def write_textgrid(path: Path, xmax: float, tiers: dict[str, Sequence[Interval]]) -> None:
    def q(text: str) -> str:
        return '"' + text.replace('"', '""') + '"'

    lines = [
        'File type = "ooTextFile"',
        'Object class = "TextGrid"',
        "",
        "xmin = 0",
        f"xmax = {xmax}",
        "tiers? <exists>",
        f"size = {len(tiers)}",
        "item []:",
    ]
    for i, (name, intervals) in enumerate(tiers.items(), 1):
        filled = fill(intervals, xmax)
        lines += [
            f"    item [{i}]:",
            '        class = "IntervalTier"',
            f"        name = {q(name)}",
            "        xmin = 0",
            f"        xmax = {xmax}",
            f"        intervals: size = {len(filled)}",
        ]
        for j, (start, end, text) in enumerate(filled, 1):
            lines += [
                f"        intervals [{j}]:",
                f"            xmin = {start}",
                f"            xmax = {end}",
                f"            text = {q(text)}",
            ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


_FIELD = re.compile(r'^\s*(name|xmin|xmax|text) = (?:"((?:[^"]|"")*)"|(\S+))\s*$')


def read_textgrid(path: Path) -> dict[str, list[Interval]]:
    """Đọc lại TextGrid dạng dài (dạng Praat lưu mặc định), UTF-8 hoặc UTF-16."""
    raw = path.read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8")
    tiers: dict[str, list[Interval]] = {}
    current: list[Interval] | None = None
    start = end = 0.0
    for line in text.splitlines():
        if (match := _FIELD.match(line)) is None:
            continue
        key, quoted, bare = match.groups()
        if key == "name":
            current = tiers.setdefault(quoted.replace('""', '"'), [])
        elif current is None:
            continue  # xmin/xmax của cả file, trước lớp đầu tiên
        elif key == "xmin":
            start = float(bare)
        elif key == "xmax":
            end = float(bare)
        elif key == "text":
            current.append((start, end, quoted.replace('""', '"')))
    return tiers


# --- nhãn -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Ipu:
    start: float
    end: float
    act: str | None  # None khi người gán chưa gán
    attributes: frozenset[str]
    words: str


def labels(path: Path) -> list[Ipu]:
    """Các đoạn nói của khách, kèm nhãn và lời. Nhãn sai chính tả thì nổ, không lặng lẽ bỏ qua."""
    tiers = read_textgrid(path)
    words = [w for w in tiers.get("caller_words", []) if w[2].strip()]
    out = []
    for start, end, text in tiers["caller_act"]:
        if not text.strip():
            continue
        act, *attrs = text.split()
        if act != UNLABELLED and act not in ACTS:
            raise ValueError(f"{path.name} {start:.2f}s: unknown act {act!r}")
        if bad := set(attrs) - ATTRIBUTES:
            raise ValueError(f"{path.name} {start:.2f}s: unknown attributes {sorted(bad)}")
        said = " ".join(w for s, e, w in words if start <= (s + e) / 2 < end)
        out.append(
            Ipu(start, end, None if act == UNLABELLED else act, frozenset(attrs), said.strip())
        )
    return out


# --- lệnh -------------------------------------------------------------------------------


def textgrid_path(rec: dataset.Recording) -> Path:
    return rec.raw().with_suffix(".TextGrid")


def prepare(rec: dataset.Recording, config: AnnotationConfig, with_asr: bool) -> Path | None:
    out = textgrid_path(rec)
    if out.exists():
        return None
    audio, rate = sf.read(rec.raw(), dtype="float32", always_2d=True)
    caller = audio[:, 0]
    xmax = round(len(caller) / rate, 3)
    bot = [
        (e["start_sample"] / rate, e["end_sample"] / rate, str(e["step"]))
        for e in rec.sidecar()["playback"]
    ]
    speech = [(s, e, UNLABELLED) for s, e in ipus(caller, rate, config)]
    write_textgrid(
        out,
        xmax,
        {
            "bot": bot,
            "caller_act": speech,
            "caller_words": [(s, e, "") for s, e, _ in speech],
            "asr_draft": asr_draft(caller, rate, config) if with_asr else [],
            "nonspeech": [],
        },
    )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    from turnwise.config import load_settings

    parser = argparse.ArgumentParser(prog="evaluation.annotation")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--no-asr", action="store_true")
    sub.add_parser("status")
    args = parser.parse_args(argv)

    recs = dataset.recordings(dataset.DEV)
    if args.command == "prepare":
        config = load_settings().annotation
        for rec in recs:
            made = prepare(rec, config, with_asr=not args.no_asr)
            sys.stdout.write(f"{'wrote' if made else 'kept '} {textgrid_path(rec).name}\n")
        return 0

    counts: Counter[str] = Counter()
    for rec in recs:
        if textgrid_path(rec).exists():
            counts.update(ipu.act or UNLABELLED for ipu in labels(textgrid_path(rec)))
        else:
            counts["(no TextGrid)"] += 1
    sys.stdout.write(f"{dict(counts)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
