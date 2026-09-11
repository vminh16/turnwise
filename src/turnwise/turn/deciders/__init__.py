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
from turnwise.turn.deciders.silence_threshold import SilenceThresholdDecider


def _build_silence_threshold(turn: TurnConfig) -> TurnDecider:
    if turn.silence_threshold_ms is None or turn.silence_floor_dbfs is None:
        raise ValueError(
            "B1 cần turn.silence_threshold_ms và turn.silence_floor_dbfs; "
            "xem configs/baseline/silence-threshold.yaml"
        )
    return SilenceThresholdDecider(turn.silence_threshold_ms, turn.silence_floor_dbfs)


BUILDERS: dict[str, Callable[[TurnConfig], TurnDecider]] = {
    "silence_threshold": _build_silence_threshold,
}
"""Tên trong `turn.decider` -> hàm dựng. `fused`, `acoustic_onnx`, `semantic_onnx`
chưa có mặt ở đây vì chúng chưa tồn tại (Giai đoạn 2)."""


def build(turn: TurnConfig) -> TurnDecider:
    """Dựng adapter mà `turn.decider` nêu tên."""
    builder = BUILDERS.get(turn.decider)
    if builder is None:
        raise NotImplementedError(
            f"adapter {turn.decider!r} chưa được cài đặt; có sẵn: {sorted(BUILDERS)}"
        )
    return builder(turn)
