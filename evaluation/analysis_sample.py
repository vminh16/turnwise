"""Bộ phân tích: bốc hội thoại, bốc cửa sổ, sinh TextGrid, đọc lại nhãn (ADR-0007).

    uv run python -m evaluation.analysis_sample rank      # xếp hạng ngẫu nhiên mọi mục đủ điều kiện
    uv run python -m evaluation.analysis_sample prepare   # cửa sổ + TextGrid cho mục đã có audio
    uv run python -m evaluation.analysis_sample status    # tiến độ theo vùng, theo nhãn, theo thanh

Quy tắc ở `docs/annotation-guide-conversation.md`. Ba điều module này giữ cho người gán:

- **Người không chọn.** Thứ hạng của một mục là `sha256(seed:source:item_id)`, nên nó không đổi
  khi danh mục được bổ sung, và không ai sắp lại được bằng tay.
- **Một cửa sổ mỗi hội thoại**, vị trí gieo từ cùng khoá, tái lập được.
- **Không ghi đè công người.** `rank` giữ nguyên các cột người gán đã điền; `prepare` không bao
  giờ ghi đè một TextGrid đã có.

Repo chỉ chứa danh mục và manifest. Audio nằm dưới `data/raw/analysis/`, không vào git.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from evaluation.annotation import ipus, read_textgrid, write_textgrid
from evaluation.roleplay import final_syllable_tone
from turnwise.config import AnalysisSampleConfig, AnnotationConfig

REGIONS = ("north", "central", "south", "unknown")
ONSETS = frozenset({"H", "S", "O", "PI", "I", "BI", "BC", "BC_O", "X"})
ATTRIBUTES = frozenset({"filled", "laugh", "question"})
EXCLUSIONS = frozenset(
    {
        "no_audio",
        "not_two_party",
        "music",
        "edited",
        "unintelligible",
        "not_vietnamese",
        "private_sensitive",
        "too_short",
    }
)
SPEAKERS = ("A", "B")
AUDIO_SUFFIXES = (".wav", ".flac", ".mp3", ".ogg")

CATALOG_COLUMNS = (
    "source",
    "item_id",
    "url",
    "language",
    "birth_year",
    "birthplace",
    "province",
    "region",
    "restricted",
    "notes",
)
MACHINE_COLUMNS = ("source", "item_id", "region", "rank", "key", "url")
WINDOW_COLUMNS = ("audio_file", "context_start_s", "window_start_s", "window_end_s")
HUMAN_COLUMNS = ("excluded", "dialect_heard", "annotator", "guide_version", "minutes_spent")
SAMPLE_COLUMNS = MACHINE_COLUMNS + WINDOW_COLUMNS + HUMAN_COLUMNS

Row = dict[str, str]


# --- bốc hội thoại ----------------------------------------------------------------------


def sample_key(seed: int, source: str, item_id: str) -> str:
    return hashlib.sha256(f"{seed}:{source}:{item_id}".encode()).hexdigest()


def eligible(row: Row) -> bool:
    """Chỉ mục tiếng Việt, không bị hạn chế. Không có tiêu chí nội dung (§3.1)."""
    return row["language"].strip() == "vi" and row["restricted"].strip().lower() != "yes"


def read_csv(path: Path) -> list[Row]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Sequence[Row], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rank(catalog: Sequence[Row], previous: Sequence[Row], seed: int) -> list[Row]:
    """Xếp hạng trong từng vùng theo khoá ngẫu nhiên; giữ cột cửa sổ và cột người đã điền."""
    kept = {(r["source"], r["item_id"]): r for r in previous}
    seen: set[tuple[str, str]] = set()
    rows: list[Row] = []
    for item in catalog:
        ident = (item["source"].strip(), item["item_id"].strip())
        if ident in seen:
            raise ValueError(f"duplicate catalog entry {ident}")
        seen.add(ident)
        region = item["region"].strip() or "unknown"
        if region not in REGIONS:
            raise ValueError(f"{ident}: unknown region {region!r}, expected one of {REGIONS}")
        if not eligible(item):
            continue
        old = kept.get(ident, {})
        row = {c: old.get(c, "") for c in WINDOW_COLUMNS + HUMAN_COLUMNS}
        row.update(
            source=ident[0],
            item_id=ident[1],
            region=region,
            key=sample_key(seed, *ident),
            url=item["url"].strip(),
        )
        rows.append(row)
    rows.sort(key=lambda r: (REGIONS.index(r["region"]), r["key"]))
    counter: Counter[str] = Counter()
    for row in rows:
        counter[row["region"]] += 1
        row["rank"] = str(counter[row["region"]])
    return rows


def due(rows: Sequence[Row], per_region: int) -> list[Row]:
    """Các mục cần gán lúc này: theo thứ hạng, bỏ mục đã loại, tới khi mỗi vùng đủ số cửa sổ."""
    out: list[Row] = []
    taken: Counter[str] = Counter()
    for row in rows:
        if row["region"] == "unknown" or row["excluded"].strip():
            continue
        if taken[row["region"]] < per_region:
            taken[row["region"]] += 1
            out.append(row)
    return out


# --- bốc cửa sổ -------------------------------------------------------------------------


def audio_parts(audio_dir: Path, source: str, item_id: str) -> list[Path]:
    """`<item_id>.mp3`, hoặc `<item_id>_1.mp3`, `<item_id>_2.mp3`… khi kho chia nhiều file."""
    folder = audio_dir / source
    if not folder.is_dir():
        return []
    return sorted(
        p
        for p in folder.iterdir()
        if p.suffix.lower() in AUDIO_SUFFIXES
        and (p.stem == item_id or p.stem.startswith(f"{item_id}_"))
    )


@dataclass(frozen=True)
class Window:
    part: int
    context_start: float
    start: float
    end: float


def choose_window(durations: Sequence[float], key: str, cfg: AnalysisSampleConfig) -> Window | None:
    """Vị trí đều trên toàn hội thoại; cửa sổ và ngữ cảnh nằm trọn trong một file.

    Bỏ `skip_head_s` ở đầu file đầu và `skip_tail_s` ở cuối file cuối. Không đủ chỗ thì None.
    """
    spans: list[tuple[int, float, float]] = []
    for i, duration in enumerate(durations):
        low = cfg.context_s + (cfg.skip_head_s if i == 0 else 0.0)
        high = duration - cfg.window_s - (cfg.skip_tail_s if i == len(durations) - 1 else 0.0)
        if high >= low:
            spans.append((i, low, high))
    if not spans:
        return None
    rng = np.random.default_rng(int(key[:16], 16))
    lengths = np.array([high - low for _, low, high in spans])
    if lengths.sum() == 0:
        i, start, _ = spans[0]
    else:
        offset = float(rng.uniform(0, lengths.sum()))
        k = int(np.searchsorted(np.cumsum(lengths), offset, side="right"))
        k = min(k, len(spans) - 1)
        i, low, _ = spans[k]
        start = low + offset - float(lengths[:k].sum())
    start = round(start, 3)
    return Window(i, round(start - cfg.context_s, 3), start, round(start + cfg.window_s, 3))


def textgrid_path(audio: Path) -> Path:
    return audio.with_suffix(".TextGrid")


def prepare(row: Row, cfg: AnalysisSampleConfig, vad: AnnotationConfig) -> str:
    """Điền cửa sổ vào `row` và sinh TextGrid. Trả một chữ cho log."""
    parts = audio_parts(cfg.audio_dir, row["source"], row["item_id"])
    if not parts:
        return "no audio yet"
    durations = [sf.info(str(p)).duration for p in parts]
    window = choose_window(durations, row["key"], cfg)
    if window is None:
        row["excluded"] = "too_short"
        return "too_short"
    audio = parts[window.part]
    row.update(
        audio_file=audio.relative_to(cfg.audio_dir).as_posix(),
        context_start_s=f"{window.context_start:.3f}",
        window_start_s=f"{window.start:.3f}",
        window_end_s=f"{window.end:.3f}",
    )
    out = textgrid_path(audio)
    if out.exists():
        return f"kept {out.name}"
    info = sf.info(str(audio))
    first = int(window.context_start * info.samplerate)
    last = int(window.end * info.samplerate)
    signal, rate = sf.read(str(audio), start=first, stop=last, dtype="float32", always_2d=True)
    mono = signal.mean(axis=1)
    draft = [
        (s + window.context_start, e + window.context_start, "") for s, e in ipus(mono, rate, vad)
    ]
    write_textgrid(
        out,
        round(info.duration, 3),
        {
            "window": [
                (window.context_start, window.start, "context"),
                (window.start, window.end, "label"),
            ],
            "draft": draft,
            "A": draft,
            "B": draft,
            "nonspeech": [],
        },
    )
    return f"wrote {out.name}"


# --- nhãn -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Ipu:
    speaker: str
    start: float
    end: float
    onset: str
    attributes: frozenset[str]
    words: str


def parse(speaker: str, start: float, end: float, text: str, where: str) -> Ipu:
    """`<nhãn> [thuộc tính ...] | <lời>` (§4.1). Gõ sai thì nổ, không lặng lẽ bỏ qua."""
    head, _, words = text.partition("|")
    onset, *attrs = head.split() or [""]
    if onset not in ONSETS:
        raise ValueError(f"{where} {speaker} {start:.2f}s: unknown onset {onset!r}")
    if bad := set(attrs) - ATTRIBUTES:
        raise ValueError(f"{where} {speaker} {start:.2f}s: unknown attributes {sorted(bad)}")
    return Ipu(speaker, start, end, onset, frozenset(attrs), words.strip())


def labels(path: Path, start: float, end: float) -> list[Ipu]:
    """Các IPU đã gán bắt đầu trong cửa sổ, cả hai người, theo thời gian."""
    tiers = read_textgrid(path)
    out = [
        parse(speaker, s, e, text, path.name)
        for speaker in SPEAKERS
        for s, e, text in tiers[speaker]
        if text.strip() and start <= s < end
    ]
    return sorted(out, key=lambda ipu: (ipu.start, ipu.speaker))


def unassigned(path: Path, start: float, end: float) -> int:
    """Khoảng nháp trong cửa sổ mà cả `A` lẫn `B` đều trống: chưa gán, hoặc là tiếng không lời."""
    tiers = read_textgrid(path)
    spoken = [(s, e) for speaker in SPEAKERS for s, e, text in tiers[speaker] if text.strip()]
    return sum(
        1
        for s, e, _ in tiers["draft"]
        if start <= s < end and not any(a < e and s < b for a, b in spoken)
    )


@dataclass(frozen=True)
class Ending:
    ipu: Ipu
    outcome: str  # hold, shift, interrupted, other, censored
    backchannel: bool  # người kia chêm tiếng đệm trước khi kết thúc được quyết định
    tone: str


def endings(ipus_: Sequence[Ipu]) -> list[Ending]:
    """Kết thúc của mỗi IPU, suy từ nhãn mở đầu của đoạn kế tiếp (§5.2).

    `BC`, `BC_O`, `BI` của người kia không quyết định kết thúc; `X` thì quyết định thành `other`.
    """
    out: list[Ending] = []
    for k, ipu in enumerate(ipus_):
        later = ipus_[k + 1 :]
        own_next = next((n for n in later if n.speaker == ipu.speaker), None)
        horizon = own_next.start if own_next else float("inf")
        backchannel = False
        outcome = "censored"
        for n in later:
            if n.speaker == ipu.speaker or n.start >= horizon:
                continue
            if n.onset in {"BC", "BC_O", "BI"}:
                backchannel |= n.onset != "BI"
                continue
            if n.onset == "I" and n.start >= ipu.end:
                outcome = "other"  # `I` phải chồng lên lời; bắt đầu trong khoảng lặng là `PI`
                break
            outcome = {"S": "shift", "O": "shift", "PI": "interrupted", "I": "interrupted"}.get(
                n.onset, "other"
            )
            break
        else:
            if own_next is not None:
                outcome = "hold" if own_next.onset == "H" else "other"
        tone = final_syllable_tone(ipu.words).value if ipu.words else "unknown"
        out.append(Ending(ipu, outcome, backchannel, tone))
    return out


# --- lệnh -------------------------------------------------------------------------------


def _window_of(row: Row) -> tuple[float, float]:
    return float(row["window_start_s"]), float(row["window_end_s"])


def status(rows: Sequence[Row], cfg: AnalysisSampleConfig) -> str:
    lines: list[str] = []
    excluded = Counter(r["excluded"] for r in rows if r["excluded"].strip())
    if bad := set(excluded) - EXCLUSIONS:
        raise ValueError(f"unknown exclusion reasons {sorted(bad)}")
    eligible_per_region = Counter(r["region"] for r in rows)
    onsets: Counter[str] = Counter()
    outcome_by_tone: Counter[tuple[str, str]] = Counter()
    done: Counter[str] = Counter()
    for row in due(rows, cfg.windows_per_region):
        if not row["audio_file"]:
            continue
        grid = textgrid_path(cfg.audio_dir / row["audio_file"])
        if not grid.exists():
            continue
        start, end = _window_of(row)
        labelled = labels(grid, start, end)
        if labelled and unassigned(grid, start, end) == 0:
            done[row["region"]] += 1
        onsets.update(i.onset for i in labelled)
        outcome_by_tone.update((e.outcome, e.tone) for e in endings(labelled))
    lines.append(f"eligible per region: {dict(eligible_per_region)}")
    lines.append(f"excluded: {dict(excluded)}")
    lines.append(
        "windows done: "
        + ", ".join(f"{r} {done[r]}/{cfg.windows_per_region}" for r in REGIONS[:-1])
    )
    lines.append(f"onsets: {dict(onsets)}")
    for outcome in ("shift", "hold", "interrupted"):
        by_tone = {t: n for (o, t), n in sorted(outcome_by_tone.items()) if o == outcome}
        lines.append(f"{outcome} by final tone: {by_tone}")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    from turnwise.config import load_settings

    parser = argparse.ArgumentParser(prog="evaluation.analysis_sample")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("rank")
    sub.add_parser("prepare")
    sub.add_parser("status")
    args = parser.parse_args(argv)

    settings = load_settings()
    cfg = settings.analysis_sample
    if args.command == "rank":
        catalog = read_csv(cfg.catalog)
        if not catalog:
            sys.stderr.write(
                f"{cfg.catalog} is missing or empty; see analysis-catalog.template.csv\n"
            )
            return 1
        rows = rank(catalog, read_csv(cfg.sample), cfg.seed)
        write_csv(cfg.sample, rows, SAMPLE_COLUMNS)
        sys.stdout.write(f"ranked {len(rows)} eligible items -> {cfg.sample}\n")
        return 0

    rows = read_csv(cfg.sample)
    if args.command == "prepare":
        # `prepare` có thể loại mục quá ngắn, nên lặp tới khi danh sách cần gán không đổi.
        handled: set[tuple[str, str]] = set()
        while todo := [
            r
            for r in due(rows, cfg.windows_per_region)
            if (r["source"], r["item_id"]) not in handled
        ]:
            for row in todo:
                handled.add((row["source"], row["item_id"]))
                result = prepare(row, cfg, settings.annotation)
                sys.stdout.write(
                    f"{row['region']:<8} #{row['rank']:<3} {row['item_id']}: {result}\n"
                )
        write_csv(cfg.sample, rows, SAMPLE_COLUMNS)
        return 0

    sys.stdout.write(status(rows, cfg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
