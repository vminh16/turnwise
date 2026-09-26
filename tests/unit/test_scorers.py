"""Hợp đồng scorer (`.claude/rules/turn.md`): bỏ phiếu trắng khi chưa đủ cơ sở, và cùng đầu vào
sau một lần reset cho ra cùng đầu ra."""

import numpy as np
import pytest

from turnwise.config import load_settings
from turnwise.turn.base import Scorer
from turnwise.turn.scorers.final_rise import FinalRiseScorer
from turnwise.turn.scorers.short_ipu import ShortIpuScorer
from turnwise.turn.scorers.silence import SilenceScorer
from turnwise.turn.scorers.smart_turn import SmartTurnScorer
from turnwise.types import FeatureFrame

RATE, FRAME_S = 16_000, 0.02
N = int(RATE * FRAME_S)
TURN = load_settings("configs/proposed/draft.yaml").turn
assert TURN.gate is not None and TURN.acoustic_onnx is not None
GATE, SETTINGS, ACOUSTIC = TURN.gate, TURN.scorer_settings, TURN.acoustic_onnx


def tone(hz_from: float, hz_to: float, frames: int) -> list[np.ndarray]:
    """Một nguyên âm giả có F0 trượt tuyến tính, cắt thành khung."""
    t = np.arange(frames * N) / RATE
    f = np.linspace(hz_from, hz_to, len(t))
    wave = 0.2 * np.sin(2 * np.pi * np.cumsum(f) / RATE)
    return [wave[i * N : (i + 1) * N].astype(np.float32) for i in range(frames)]


def frames(pattern: str, voiced: list[np.ndarray] | None = None) -> list[FeatureFrame]:
    """'s' có tiếng (lấy lần lượt từ `voiced` nếu có), '.' im lặng. Nền ồn -80 dBFS."""
    rng = np.random.default_rng(0)
    source = iter(voiced or [])
    out = []
    for i, mark in enumerate(pattern):
        if mark == "s":
            samples = next(source, None)
            if samples is None:
                samples = (rng.standard_normal(N) * 0.2).astype(np.float32)
        else:
            samples = np.zeros(N, np.float32)
        out.append(FeatureFrame(i, i * FRAME_S, FRAME_S, samples, noise_floor_dbfs=-80.0))
    return out


def run(scorer: Scorer, given: list[FeatureFrame]) -> list[float | None]:
    return [scorer.score(f) for f in given]


def all_scorers() -> list[Scorer]:
    assert SETTINGS.silence and SETTINGS.final_rise and SETTINGS.short_ipu
    return [
        SilenceScorer(GATE, SETTINGS.silence),
        SmartTurnScorer(lambda audio: 0.7, GATE, ACOUSTIC),
        FinalRiseScorer(GATE, SETTINGS.final_rise),
        ShortIpuScorer(GATE, SETTINGS.short_ipu),
    ]


@pytest.mark.parametrize("scorer", all_scorers(), ids=lambda s: s.name)
def test_every_scorer_fits_the_protocol(scorer: Scorer) -> None:
    assert isinstance(scorer, Scorer)


@pytest.mark.parametrize("scorer", all_scorers(), ids=lambda s: s.name)
def test_silence_before_any_speech_is_an_abstention(scorer: Scorer) -> None:
    assert set(run(scorer, frames("." * 60))) == {None}


@pytest.mark.parametrize("scorer", all_scorers(), ids=lambda s: s.name)
def test_reset_gives_identical_output_for_identical_input(scorer: Scorer) -> None:
    given = frames("s" * 15 + "." * 30, tone(120, 180, 15))
    first = run(scorer, given)
    scorer.reset()
    assert run(scorer, given) == first


def test_silence_score_grows_with_silence() -> None:
    assert SETTINGS.silence
    scores = run(SilenceScorer(GATE, SETTINGS.silence), frames("s" * 5 + "." * 60))
    assert scores[4] == 0.0 and scores[-1] == 1.0
    tail = [s for s in scores[5:] if s is not None]
    assert tail == sorted(tail)


def test_smart_turn_is_asked_once_per_pause_and_hears_the_turn() -> None:
    heard: list[int] = []

    def model(audio: np.ndarray) -> float:
        heard.append(len(audio))
        return 0.8

    scores = run(SmartTurnScorer(model, GATE, ACOUSTIC), frames("s" * 10 + "." * 20))
    assert len(heard) == 1 and heard[0] >= 10 * N
    assert scores[-1] == 0.8


def test_a_rising_tail_scores_higher_than_a_falling_one() -> None:
    assert SETTINGS.final_rise
    rise = run(
        FinalRiseScorer(GATE, SETTINGS.final_rise), frames("s" * 20 + "." * 15, tone(120, 200, 20))
    )
    fall = run(
        FinalRiseScorer(GATE, SETTINGS.final_rise), frames("s" * 20 + "." * 15, tone(200, 120, 20))
    )
    assert rise[-1] is not None and fall[-1] is not None
    assert rise[-1] > 0.5 > fall[-1]


def test_a_short_blip_looks_like_a_backchannel_and_a_long_turn_does_not() -> None:
    assert SETTINGS.short_ipu
    blip = run(ShortIpuScorer(GATE, SETTINGS.short_ipu), frames("s" * 5 + "." * 15))
    long = run(ShortIpuScorer(GATE, SETTINGS.short_ipu), frames("s" * 50 + "." * 15))
    assert blip[-1] is not None and blip[-1] > 0.5
    assert long[-1] == 0.0
