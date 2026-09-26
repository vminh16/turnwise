"""Công tắc của SPEC R8: chọn adapter bằng cấu hình, không bằng sửa code.

`.claude/rules/evaluation.md` nói rõ vì sao công tắc này quan trọng hơn nó trông có
vẻ: *"it selects a decider by config… That is what makes 'same ASR, TTS and scenarios'
structurally true rather than a promise."* Một `import` thẳng tên lớp trong
`evaluation/` biến câu đó thành lời hứa suông, vì không có gì ngăn hai baseline chạy
trên hai đường khác nhau.

Một lần chạy được mô tả **trọn vẹn bằng `TurnConfig`**. Quét dải nghĩa là dựng nhiều
`TurnConfig`, không phải truyền tham số phụ vòng qua cấu hình.
"""

from __future__ import annotations

from collections.abc import Callable

from turnwise.config import TurnConfig
from turnwise.turn.base import TurnDecider
from turnwise.turn.deciders.acoustic_onnx import AcousticOnnxDecider, SmartTurnModel
from turnwise.turn.deciders.fused import FusedDecider
from turnwise.turn.deciders.silence_threshold import SilenceThresholdDecider


def _build_silence_threshold(turn: TurnConfig) -> TurnDecider:
    if turn.silence_threshold_ms is None or turn.silence_floor_dbfs is None:
        raise ValueError(
            "B1 cần turn.silence_threshold_ms và turn.silence_floor_dbfs; "
            "xem configs/baseline/silence-threshold.yaml"
        )
    return SilenceThresholdDecider(turn.silence_threshold_ms, turn.silence_floor_dbfs)


def _build_acoustic_onnx(turn: TurnConfig) -> TurnDecider:
    if turn.acoustic_onnx is None or turn.silence_floor_dbfs is None:
        raise ValueError(
            "B2 cần turn.acoustic_onnx và turn.silence_floor_dbfs; "
            "xem configs/baseline/acoustic-onnx.yaml"
        )
    model = SmartTurnModel(turn.acoustic_onnx)
    return AcousticOnnxDecider(model, turn.silence_floor_dbfs, turn.acoustic_onnx)


def _build_fused(turn: TurnConfig) -> TurnDecider:
    from turnwise.turn.scorers import build_scorers

    take, backchannel = turn.decision.take_threshold, turn.decision.backchannel_threshold
    if take is None or backchannel is None:
        raise ValueError(
            "fused cần turn.decision.take_threshold và backchannel_threshold; "
            "xem configs/proposed/draft.yaml"
        )
    return FusedDecider(build_scorers(turn), take, backchannel)


def _build_semantic_onnx(turn: TurnConfig) -> TurnDecider:
    if turn.semantic_onnx is None or turn.silence_floor_dbfs is None:
        raise ValueError(
            "B3 cần turn.semantic_onnx và turn.silence_floor_dbfs; "
            "xem configs/baseline/semantic-onnx.yaml"
        )
    from turnwise.turn.deciders.semantic_onnx import build_semantic

    return build_semantic(turn.semantic_onnx, turn.silence_floor_dbfs)


BUILDERS: dict[str, Callable[[TurnConfig], TurnDecider]] = {
    "silence_threshold": _build_silence_threshold,
    "acoustic_onnx": _build_acoustic_onnx,
    "fused": _build_fused,
    "semantic_onnx": _build_semantic_onnx,
}
"""Tên trong `turn.decider` -> hàm dựng: ba baseline của SPEC R8 và hệ đề xuất."""


def build(turn: TurnConfig) -> TurnDecider:
    """Dựng adapter mà `turn.decider` nêu tên."""
    builder = BUILDERS.get(turn.decider)
    if builder is None:
        raise NotImplementedError(
            f"adapter {turn.decider!r} chưa được cài đặt; có sẵn: {sorted(BUILDERS)}"
        )
    return builder(turn)
