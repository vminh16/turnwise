"""Chấm một decider trên bộ dữ liệu vàng: mỗi đoạn nói đã gán nhãn nhận một phán quyết.

Luật chấm, từ `docs/annotation-guide.md` §4.3 và §5.2:

- **Lượt khách** là khoảng từ lúc bot dứt lời tới lúc bot nói câu kế. Decider được reset ở đầu
  mỗi lượt và **chỉ được nhận lượt một lần**: khi nó nhận, bot sẽ lên tiếng, nên mọi đoạn nói
  sau đó trong cùng lượt không còn chấm được (`after_take`).
- Nhận lượt **trong lúc** khách đang nói, hoặc ngay sau một đoạn `hold`, là cắt lời (`cut_in`).
  Sau một đoạn `backchannel` là nhận nhầm tiếng đệm (`backchannel_taken`).
- Sau một đoạn `take`, nhận lượt trước khi khách nói tiếp là đúng, kèm độ trễ. Khách đã nói tiếp
  mà decider vẫn chưa nhận là quá chậm (`no_take`). Hết bản thu mà chưa nhận thì độ trễ vượt quá
  khoảng quan sát được (`no_take_in_window`).
- **Lượt bot** (bot đang phát) chỉ được chấm khi chạy với `during_bot=True`. Đoạn `barge_in` được
  chấm từ **đầu** đoạn nói đè (§5.2). Nhận lượt khi khách không nói gì là bot tự ngắt vì nghe thấy
  chính mình (`self_interrupt`, SPEC R5).

Độ trễ ở đây đo trên file, không phải trên hệ chạy sống (SPEC §9.3 quy tắc 4).
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

from evaluation import annotation, dataset
from evaluation.roleplay import final_syllable_tone
from turnwise.config import AudioConfig
from turnwise.turn.base import TurnDecider
from turnwise.types import TurnOutcome


@dataclass(frozen=True)
class Verdict:
    recording: str
    speaker_id: str
    script: str
    start_s: float
    end_s: float
    act: str
    tone: str
    during_bot: bool
    verdict: str
    latency_ms: int | None


@dataclass(frozen=True)
class Span:
    start_s: float
    end_s: float
    bot: bool
    take_s: float | None  # lần nhận lượt đầu tiên trong khoảng, hoặc None


def replay(
    decider: TurnDecider, rec: dataset.Recording, audio: AudioConfig, during_bot: bool
) -> list[Span]:
    """Chạy decider qua một bản thu, reset ở mỗi lần bot bắt đầu hoặc dứt lời."""
    spans: list[Span] = []
    start = end = 0.0
    bot: bool | None = None
    take: float | None = None
    for frame in dataset.frame_source(rec, audio):
        if frame.bot_speaking != bot:
            if bot is not None:
                spans.append(Span(start, end, bot, take))
            start, bot, take = frame.start_s, frame.bot_speaking, None
            decider.reset()
        end = frame.start_s + frame.duration_s
        if bot and not during_bot:
            continue
        if take is None and decider.decide(frame).outcome == TurnOutcome.TAKE:
            take = end  # bot được nói từ cuối khung này
    if bot is not None:
        spans.append(Span(start, end, bot, take))
    return spans


def judge(
    spans: Sequence[Span], ipus: Sequence[annotation.Ipu], rec: dataset.Recording, during_bot: bool
) -> list[Verdict]:
    out: list[Verdict] = []
    for span in spans:
        inside = [i for i in ipus if span.start_s <= i.start < span.end_s and i.act is not None]
        if span.bot:
            if during_bot:
                out += _judge_bot(span, inside, rec)
            continue
        out += _judge_caller(span, inside, rec)
    return out


def _verdict(
    rec: dataset.Recording, ipu: annotation.Ipu | None, span: Span, verdict: str, ms: float | None
) -> Verdict:
    return Verdict(
        recording=rec.raw().name,
        speaker_id=rec.speaker_id,
        script=rec.script,
        start_s=ipu.start if ipu else span.take_s or span.start_s,
        end_s=ipu.end if ipu else span.take_s or span.start_s,
        act=(ipu.act or "") if ipu else "",
        tone=final_syllable_tone(ipu.words).value if ipu and ipu.words else "",
        during_bot=span.bot,
        verdict=verdict,
        latency_ms=None if ms is None else round(ms * 1000),
    )


def _judge_caller(
    span: Span, ipus: Sequence[annotation.Ipu], rec: dataset.Recording
) -> list[Verdict]:
    out: list[Verdict] = []
    take = span.take_s
    for n, ipu in enumerate(ipus):
        next_start = ipus[n + 1].start if n + 1 < len(ipus) else span.end_s
        if take is not None and take < ipu.start:
            verdict, ms = "after_take", None
        elif take is not None and take < ipu.end:
            verdict, ms = "cut_in", None
        elif take is not None and take < next_start:
            verdict, ms = {
                "take": ("ok", take - ipu.end),
                "hold": ("cut_in", None),
                "backchannel": ("backchannel_taken", None),
            }.get(ipu.act or "", ("taken", None))
        elif ipu.act == "take":
            last = n + 1 == len(ipus)
            verdict, ms = ("no_take_in_window" if last else "no_take"), None
        else:
            verdict, ms = "ok", None
        out.append(_verdict(rec, ipu, span, verdict, ms))
    return out


def _judge_bot(span: Span, ipus: Sequence[annotation.Ipu], rec: dataset.Recording) -> list[Verdict]:
    """Bot đang nói. Đoạn nói gây ra lần dừng là đoạn chứa mốc dừng hoặc ngay trước nó."""
    take = span.take_s
    cause: int | None = None
    if take is not None:
        for n, ipu in enumerate(ipus):
            next_start = ipus[n + 1].start if n + 1 < len(ipus) else span.end_s
            if ipu.start <= take < next_start:
                cause = n
    out: list[Verdict] = []
    for n, ipu in enumerate(ipus):
        if n == cause and take is not None:
            verdict, ms = {
                "barge_in": ("ok", take - ipu.start),
                "backchannel": ("backchannel_taken", None),
            }.get(ipu.act or "", ("taken", None))
        elif cause is not None and n > cause:
            verdict, ms = "after_take", None
        else:
            verdict, ms = ("missed_barge_in" if ipu.act == "barge_in" else "ok"), None
        out.append(_verdict(rec, ipu, span, verdict, ms))
    if take is not None and cause is None:
        out.append(_verdict(rec, None, span, "self_interrupt", None))
    return out


def run(
    decider: TurnDecider,
    recordings: Iterable[dataset.Recording],
    audio: AudioConfig,
    during_bot: bool = False,
) -> list[Verdict]:
    """Phán quyết cho mọi đoạn nói đã gán nhãn. Bản chưa có TextGrid thì bỏ qua."""
    out: list[Verdict] = []
    for rec in recordings:
        grid = annotation.textgrid_path(rec)
        if not grid.exists():
            continue
        ipus = annotation.labels(grid)
        out += judge(replay(decider, rec, audio, during_bot), ipus, rec, during_bot)
    return out


def summary(verdicts: Sequence[Verdict]) -> dict[str, object]:
    """Các con số của SPEC §9.1, luôn đi thành cặp cắt lời và độ trễ (§9.3 quy tắc 1)."""
    caller = [v for v in verdicts if not v.during_bot and v.verdict != "after_take"]
    holds = [v for v in caller if v.act == "hold"]
    takes = [v for v in caller if v.act == "take"]
    backs = [v for v in verdicts if v.act == "backchannel" and v.verdict != "after_take"]
    barges = [v for v in verdicts if v.act == "barge_in" and v.during_bot]
    latencies = [v.latency_ms for v in takes if v.verdict == "ok" and v.latency_ms is not None]
    by_tone: dict[str, Counter[str]] = defaultdict(Counter)
    for v in takes + holds:
        by_tone[v.tone or "?"][v.verdict] += 1
    return {
        "labelled_ipus": len(verdicts),
        "cut_in_rate": _rate(sum(v.verdict == "cut_in" for v in holds), len(holds)),
        "median_latency_ms": median(latencies) if latencies else None,
        "no_take": sum(v.verdict.startswith("no_take") for v in takes),
        "takes": len(takes),
        "backchannel_error_rate": _rate(
            sum(v.verdict == "backchannel_taken" for v in backs), len(backs)
        ),
        "barge_in_median_ms": median(
            [v.latency_ms for v in barges if v.latency_ms is not None] or [0]
        )
        if barges
        else None,
        "self_interrupts": sum(v.verdict == "self_interrupt" for v in verdicts),
        "by_tone": {tone: dict(c) for tone, c in sorted(by_tone.items())},
    }


def _rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


def write(verdicts: Sequence[Verdict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(Verdict.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(v) for v in verdicts)
    return path
