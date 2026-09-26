"""Luật chấm trên bộ dữ liệu vàng: mỗi đoạn nói đã gán nhãn nhận đúng một phán quyết."""

from evaluation import dataset, golden
from evaluation.annotation import Ipu

REC = dataset.Recording(
    path="data/raw/S009/x.wav",
    sha256="0",
    speaker_id="S009",
    script="n1-a",
    frames=0,
    sample_rate_hz=48_000,
    dialect="north",
    playback="headset",
    split="dev",
)


def ipu(start: float, end: float, act: str, words: str = "") -> Ipu:
    return Ipu(start, end, act, frozenset(), words)


def verdicts(
    span: golden.Span, *ipus: Ipu, during_bot: bool = False
) -> list[tuple[str, int | None]]:
    return [(v.verdict, v.latency_ms) for v in golden.judge([span], ipus, REC, during_bot)]


def caller(take: float | None) -> golden.Span:
    return golden.Span(0.0, 10.0, bot=False, take_s=take)


def test_taking_after_a_finished_turn_is_right_and_timed() -> None:
    assert verdicts(caller(2.3), ipu(1.0, 2.0, "take")) == [("ok", 300)]


def test_taking_after_a_hold_is_a_cut_in_and_ends_the_turn() -> None:
    got = verdicts(caller(2.5), ipu(1.0, 2.0, "hold"), ipu(3.0, 4.0, "take"))
    assert got == [("cut_in", None), ("after_take", None)]


def test_taking_while_the_caller_speaks_is_a_cut_in() -> None:
    assert verdicts(caller(1.5), ipu(1.0, 2.0, "take")) == [("cut_in", None)]


def test_holding_through_a_hold_then_taking_is_right() -> None:
    got = verdicts(caller(4.4), ipu(1.0, 2.0, "hold"), ipu(3.0, 4.0, "take"))
    assert got == [("ok", None), ("ok", 400)]


def test_a_take_answered_only_after_the_caller_spoke_again_is_too_slow() -> None:
    got = verdicts(caller(None), ipu(1.0, 2.0, "take"), ipu(5.0, 6.0, "take"))
    assert got == [("no_take", None), ("no_take_in_window", None)]


def test_taking_after_a_backchannel_is_an_error() -> None:
    assert verdicts(caller(1.6), ipu(1.0, 1.3, "backchannel")) == [("backchannel_taken", None)]


def test_bot_spans_are_not_scored_unless_asked() -> None:
    bot = golden.Span(0.0, 10.0, bot=True, take_s=2.0)
    assert verdicts(bot, ipu(1.8, 3.0, "barge_in")) == []


def test_a_barge_in_is_timed_from_its_onset() -> None:
    bot = golden.Span(0.0, 10.0, bot=True, take_s=2.1)
    got = verdicts(bot, ipu(1.8, 3.0, "barge_in"), during_bot=True)
    assert got == [("ok", 300)]


def test_stopping_with_nobody_speaking_is_a_self_interrupt() -> None:
    bot = golden.Span(0.0, 10.0, bot=True, take_s=0.5)
    got = verdicts(bot, ipu(1.8, 3.0, "barge_in"), during_bot=True)
    assert ("self_interrupt", None) in got and ("missed_barge_in", None) in got


def test_summary_pairs_cut_in_rate_with_latency_and_splits_by_tone() -> None:
    vs = golden.judge(
        [caller(2.3)], [ipu(0.2, 0.5, "hold", "chờ chút"), ipu(1.0, 2.0, "take", "Dạ.")], REC, False
    )
    s = golden.summary(vs)
    assert s["cut_in_rate"] == 0.0 and s["median_latency_ms"] == 300
    assert s["by_tone"] == {"drop": {"ok": 1}, "rising": {"ok": 1}}
