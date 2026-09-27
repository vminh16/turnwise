"""B3: ASR rồi Namo, vận hành như B2. Logic hỏi-khi-im đã thử ở test_acoustic_onnx; ở đây chỉ
thử phần riêng của B3. Mô hình thật chỉ thử khi đã tải về, vì `models/` không nằm trong git."""

import numpy as np
import pytest
from numpy.typing import NDArray

from turnwise.config import load_settings
from turnwise.turn.base import TurnDecider
from turnwise.turn.deciders import build
from turnwise.turn.deciders.semantic_onnx import (
    SCORE_KEY,
    SemanticOnnxDecider,
    semantic_predictor,
)
from turnwise.types import FeatureFrame, TurnOutcome

TURN = load_settings("configs/baseline/semantic-onnx.yaml").turn
assert TURN.semantic_onnx is not None and TURN.gate is not None
CONFIG, FLOOR = TURN.semantic_onnx, TURN.gate


def frames(pattern: str) -> list[FeatureFrame]:
    rng = np.random.default_rng(0)
    return [
        FeatureFrame(
            i,
            i * 0.02,
            0.02,
            (rng.standard_normal(320) * (0.2 if m == "s" else 0.0)).astype(np.float32),
        )
        for i, m in enumerate(pattern)
    ]


def test_b3_fits_the_seam() -> None:
    assert isinstance(SemanticOnnxDecider(lambda a: 0.0, FLOOR, CONFIG), TurnDecider)


def test_no_words_means_not_finished() -> None:
    predict = semantic_predictor(lambda audio: "", lambda text: 1.0)
    assert predict(np.zeros(160, np.float32)) == 0.0


def test_the_transcript_reaches_the_classifier() -> None:
    seen: list[str] = []

    def classify(text: str) -> float:
        seen.append(text)
        return 0.9

    predict = semantic_predictor(lambda audio: "sáng mai", classify)
    assert predict(np.zeros(160, np.float32)) == 0.9 and seen == ["sáng mai"]


def test_decisions_carry_the_namo_score_and_timings_are_recorded() -> None:
    def predict(audio: NDArray[np.float32]) -> float:
        return 0.8

    decider = SemanticOnnxDecider(predict, FLOOR, CONFIG)
    decisions = [decider.decide(f) for f in frames("s" * 10 + "." * 12)]
    assert [dict(d.scores) for d in decisions if d.scores] == [{SCORE_KEY: 0.8}]
    assert decisions[-1].outcome == TurnOutcome.TAKE
    assert len(decider.predict_ms) == 1


def test_the_real_model_runs_through_the_registry() -> None:
    if not (CONFIG.model_dir / "model_quant.onnx").exists():
        pytest.skip("Namo ONNX not downloaded; models/ is outside git")
    if not (CONFIG.asr_model_dir / "model.bin").exists():
        pytest.skip("faster-whisper model not downloaded")
    decider = build(TURN)
    assert decider.name == "semantic_onnx"
