"""Scorer của hệ đề xuất. Seam **trong**: chỉ `deciders/fused.py` và test của tầng này dùng tới.

Bật một scorer là ghi tên nó vào `turn.scorers` và đặt tham số của nó ở `turn.scorer_settings`;
tắt để làm ablation là xoá tên khỏi danh sách (SPEC §9.3 quy tắc 3).
"""

from __future__ import annotations

from collections.abc import Callable

from turnwise.config import GateConfig, TurnConfig
from turnwise.turn.base import Scorer


def _need[T](value: T | None, what: str) -> T:
    if value is None:
        raise ValueError(f"scorer needs turn.{what} in the config")
    return value


def _silence(turn: TurnConfig, gate: GateConfig) -> Scorer:
    from turnwise.turn.scorers.silence import SilenceScorer

    return SilenceScorer(gate, _need(turn.scorer_settings.silence, "scorer_settings.silence"))


def _smart_turn(turn: TurnConfig, gate: GateConfig) -> Scorer:
    from turnwise.turn.deciders.acoustic_onnx import SmartTurnModel
    from turnwise.turn.scorers.smart_turn import SmartTurnScorer

    config = _need(turn.acoustic_onnx, "acoustic_onnx")
    return SmartTurnScorer(SmartTurnModel(config), gate, config)


def _final_rise(turn: TurnConfig, gate: GateConfig) -> Scorer:
    from turnwise.turn.scorers.final_rise import FinalRiseScorer

    return FinalRiseScorer(
        gate, _need(turn.scorer_settings.final_rise, "scorer_settings.final_rise")
    )


def _short_ipu(turn: TurnConfig, gate: GateConfig) -> Scorer:
    from turnwise.turn.scorers.short_ipu import ShortIpuScorer

    return ShortIpuScorer(gate, _need(turn.scorer_settings.short_ipu, "scorer_settings.short_ipu"))


SCORERS: dict[str, Callable[[TurnConfig, GateConfig], Scorer]] = {
    "silence": _silence,
    "smart_turn": _smart_turn,
    "final_rise": _final_rise,
    "short_ipu": _short_ipu,
}


def build_scorers(turn: TurnConfig) -> list[Scorer]:
    gate = _need(turn.gate, "gate")
    unknown = set(turn.scorers) - set(SCORERS)
    if unknown:
        raise ValueError(f"unknown scorers {sorted(unknown)}; known: {sorted(SCORERS)}")
    return [SCORERS[name](turn, gate) for name in turn.scorers]
