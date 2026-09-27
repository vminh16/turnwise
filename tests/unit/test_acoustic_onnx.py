"""B2 phải vận hành smart-turn đúng như pipecat: hỏi khi im 200 ms, nhận lượt khi mô hình nói
xong hoặc khi im 3 giây. Logic được thử bằng một mô hình giả; mô hình thật chỉ được thử khi
file ONNX có trên máy, vì `models/` không nằm trong git."""

import numpy as np
import pytest
from numpy.typing import NDArray

from turnwise.config import AcousticOnnxConfig, GateConfig, load_settings
from turnwise.turn.base import TurnDecider
from turnwise.turn.deciders import build
from turnwise.turn.deciders.acoustic_onnx import SCORE_KEY, AcousticOnnxDecider
from turnwise.types import FeatureFrame, TurnOutcome

FRAME_S = 0.02
SAMPLES = 320  # 20 ms ở 16 kHz
LOUD = 0.2


def frames(pattern: str) -> list[FeatureFrame]:
    """Mỗi ký tự là một khung 20 ms: 's' có tiếng, '.' im lặng."""
    rng = np.random.default_rng(0)
    return [
        FeatureFrame(
            index=i,
            start_s=i * FRAME_S,
            duration_s=FRAME_S,
            samples=(rng.standard_normal(SAMPLES) * (LOUD if mark == "s" else 0.0)).astype(
                np.float32
            ),
        )
        for i, mark in enumerate(pattern)
    ]


class FakeModel:
    def __init__(self, *answers: float) -> None:
        self.answers = list(answers)
        self.heard: list[int] = []  # số mẫu mỗi lần được hỏi

    def __call__(self, audio: NDArray[np.float32]) -> float:
        self.heard.append(len(audio))
        return self.answers.pop(0)


@pytest.fixture(scope="module")
def config() -> tuple[AcousticOnnxConfig, GateConfig]:
    turn = load_settings("configs/baseline/acoustic-onnx.yaml").turn
    assert turn.acoustic_onnx is not None and turn.gate is not None
    return turn.acoustic_onnx, turn.gate


def run(model: FakeModel, config: tuple[AcousticOnnxConfig, GateConfig], pattern: str) -> list[str]:
    decider = AcousticOnnxDecider(model, config[1], config[0])
    return ["T" if decider.decide(f).outcome == TurnOutcome.TAKE else "H" for f in frames(pattern)]


def test_b2_fits_the_seam(config: tuple[AcousticOnnxConfig, GateConfig]) -> None:
    assert isinstance(AcousticOnnxDecider(FakeModel(), config[1], config[0]), TurnDecider)


def test_the_model_is_asked_after_200_ms_of_silence_and_takes_when_it_says_done(
    config: tuple[AcousticOnnxConfig, GateConfig],
) -> None:
    model = FakeModel(0.9)
    out = run(model, config, "s" * 10 + "." * 15)
    assert out.index("T") == 10 + 10 - 1  # khung im thứ 10 = 200 ms
    assert len(model.heard) == 1


def test_a_not_done_answer_holds_until_the_3_s_fallback(
    config: tuple[AcousticOnnxConfig, GateConfig],
) -> None:
    model = FakeModel(0.1)
    out = run(model, config, "s" * 10 + "." * 160)
    assert out.index("T") == 10 + 150 - 1  # 3000 ms im lặng
    assert len(model.heard) == 1  # không hỏi lại khi khách vẫn im


def test_speech_after_a_not_done_answer_asks_again_at_the_next_pause(
    config: tuple[AcousticOnnxConfig, GateConfig],
) -> None:
    model = FakeModel(0.1, 0.9)
    out = run(model, config, "s" * 10 + "." * 12 + "s" * 5 + "." * 12)
    assert out.index("T") == 10 + 12 + 5 + 10 - 1
    assert model.heard[1] > model.heard[0]  # lần hai nghe cả phần nói thêm


def test_the_threshold_is_strictly_greater_than(
    config: tuple[AcousticOnnxConfig, GateConfig],
) -> None:
    """inference.py: `1 if probability > 0.5 else 0`."""
    assert "T" not in run(FakeModel(0.5), config, "s" * 5 + "." * 12)


def test_silence_before_any_speech_is_never_a_finished_turn(
    config: tuple[AcousticOnnxConfig, GateConfig],
) -> None:
    model = FakeModel()
    assert "T" not in run(model, config, "." * 200)
    assert model.heard == []


def test_the_score_is_recorded_only_on_the_frame_the_model_ran(
    config: tuple[AcousticOnnxConfig, GateConfig],
) -> None:
    decider = AcousticOnnxDecider(FakeModel(0.3), config[1], config[0])
    decisions = [decider.decide(f) for f in frames("s" * 5 + "." * 12)]
    assert [d.scores for d in decisions if d.scores] == [{SCORE_KEY: 0.3}]


def test_reset_gives_identical_output_for_identical_input(
    config: tuple[AcousticOnnxConfig, GateConfig],
) -> None:
    model = FakeModel(0.9, 0.9)
    decider = AcousticOnnxDecider(model, config[1], config[0])
    given = frames("s" * 10 + "." * 12)
    first = [decider.decide(f).outcome for f in given]
    decider.reset()
    second = [decider.decide(f).outcome for f in given]
    assert first == second and model.heard[0] == model.heard[1]


def test_the_model_hears_at_most_the_pre_speech_before_speech_began(
    config: tuple[AcousticOnnxConfig, GateConfig],
) -> None:
    model = FakeModel(0.9)
    run(model, config, "." * 100 + "s" * 10 + "." * 10)
    pre = config[0].pre_speech_ms * 16
    assert model.heard == [pre + (10 + 10) * SAMPLES]


def test_frames_at_another_rate_are_refused(config: tuple[AcousticOnnxConfig, GateConfig]) -> None:
    decider = AcousticOnnxDecider(FakeModel(), config[1], config[0])
    frame = FeatureFrame(index=0, start_s=0, duration_s=FRAME_S, samples=np.zeros(960, np.float32))
    with pytest.raises(ValueError, match="16000"):
        decider.decide(frame)


def test_the_real_model_runs_through_the_registry() -> None:
    turn = load_settings("configs/baseline/acoustic-onnx.yaml").turn
    assert turn.acoustic_onnx is not None
    if not turn.acoustic_onnx.model_path.exists():
        pytest.skip("smart-turn ONNX not downloaded; models/ is outside git")
    pytest.importorskip("faster_whisper", reason="nhóm `asr` chưa cài")
    decider = build(turn)
    scores = [
        d.scores[SCORE_KEY] for f in frames("s" * 50 + "." * 12) if (d := decider.decide(f)).scores
    ]
    [score] = scores
    assert score is not None and 0.0 <= score <= 1.0
