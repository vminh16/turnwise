"""Công tắc R8: đổi adapter bằng cấu hình, không bằng sửa code."""

import numpy as np
import pytest

from turnwise.config import TurnConfig, load_settings
from turnwise.turn.base import TurnDecider
from turnwise.turn.deciders import BUILDERS, build
from turnwise.turn.deciders.silence_threshold import SilenceThresholdDecider
from turnwise.types import FeatureFrame, TurnOutcome


def baseline_turn(threshold_ms: int = 500) -> TurnConfig:
    turn = load_settings("configs/baseline/silence-threshold.yaml").turn
    return turn.model_copy(update={"silence_threshold_ms": threshold_ms})


def test_config_picks_the_adapter() -> None:
    decider = build(baseline_turn())
    assert isinstance(decider, SilenceThresholdDecider)
    assert isinstance(decider, TurnDecider)
    assert decider.name == "silence_threshold"


def test_the_threshold_comes_from_the_config_it_was_built_from() -> None:
    """Một điểm trên đường cong = một cấu hình trọn vẹn, không phải một tham số rời.

    Kiểm qua hành vi chứ không qua thuộc tính riêng: ngưỡng hẹp phải nhận lượt sớm hơn.
    """
    silence = [
        FeatureFrame(index=i, start_s=i * 0.02, duration_s=0.02, samples=np.zeros(320, np.float32))
        for i in range(100)
    ]
    speech = FeatureFrame(
        index=0, start_s=0.0, duration_s=0.02, samples=np.full(320, 0.2, np.float32)
    )

    taken_at = []
    for threshold_ms in (200, 1200):
        decider = build(baseline_turn(threshold_ms))
        decider.decide(speech)
        outcomes = [decider.decide(frame).outcome for frame in silence]
        taken_at.append(outcomes.index(TurnOutcome.TAKE))

    assert taken_at == [9, 59]


def test_an_adapter_that_does_not_exist_yet_says_so() -> None:
    """B2 và B3 là Giai đoạn 2; tới lúc đó lỗi phải nói rõ, không phải KeyError trần."""
    turn = baseline_turn().model_copy(update={"decider": "acoustic_onnx"})
    with pytest.raises(NotImplementedError, match="acoustic_onnx"):
        build(turn)


def test_b1_without_its_keys_is_refused() -> None:
    turn = baseline_turn().model_copy(update={"silence_threshold_ms": None})
    with pytest.raises(ValueError, match="silence_threshold_ms"):
        build(turn)


def test_every_builder_name_is_a_valid_config_value() -> None:
    """Tên trong registry phải là giá trị `turn.decider` nhận được, nếu không công tắc lệch."""
    turn = baseline_turn()
    for name in BUILDERS:
        assert turn.model_copy(update={"decider": name}).decider == name
