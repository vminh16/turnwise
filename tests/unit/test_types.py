"""Bất biến của từ vựng dùng chung — đặc biệt là chỗ dễ mất nhất: bỏ phiếu trắng."""

import numpy as np
import pytest

from turnwise.types import FeatureFrame, Tone, TurnDecision, TurnOutcome


def test_six_vietnamese_tones_plus_unknown() -> None:
    assert len(Tone) == 7


def test_abstain_is_distinguishable_from_a_middling_score() -> None:
    """Cốt lõi của SPEC §8: 'không kết luận' không được lẫn với 0.5."""
    decision = TurnDecision(
        outcome=TurnOutcome.HOLD,
        decider="fused",
        frame_index=0,
        at_s=0.0,
        scores={"undecided": None, "on_the_fence": 0.5},
    )
    assert decision.scores["undecided"] is None
    assert decision.scores["on_the_fence"] == 0.5


def test_a_disabled_scorer_is_absent_not_none() -> None:
    """Tắt để ablation khác với bỏ phiếu trắng; ánh xạ phải phân biệt được."""
    decision = TurnDecision(
        outcome=TurnOutcome.HOLD, decider="fused", frame_index=0, at_s=0.0, scores={"a": None}
    )
    assert "a" in decision.scores
    assert "switched_off" not in decision.scores


def test_decisions_are_immutable() -> None:
    """Telemetry chỉ đọc; một bản ghi bị sửa sau khi tạo là không tái dựng được."""
    decision = TurnDecision(outcome=TurnOutcome.HOLD, decider="b1", frame_index=1, at_s=0.02)
    with pytest.raises(AttributeError):
        decision.outcome = TurnOutcome.TAKE  # type: ignore[misc]


def test_frame_defaults_to_no_pitch_estimate() -> None:
    """Khung vô thanh là bình thường, không phải lỗi."""
    frame = FeatureFrame(
        index=0, start_s=0.0, duration_s=0.02, samples=np.zeros(320, dtype=np.float32)
    )
    assert frame.f0_hz is None
