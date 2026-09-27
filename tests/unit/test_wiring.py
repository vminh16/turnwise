"""Nối dây một cuộc gọi, thử bằng đồ giả: không micro, không mô hình."""

import time
from collections.abc import Iterator

import numpy as np
from numpy.typing import NDArray

from turnwise.config import load_settings
from turnwise.dialog.backend_stub import NetCoBackend
from turnwise.dialog.machine import Dialog
from turnwise.transport.wiring import Call
from turnwise.types import FeatureFrame, TurnDecision, TurnOutcome


class FakePlayer:
    def __init__(self) -> None:
        self.played: list[int] = []
        self.stops = 0

    def play(self, audio: NDArray[np.float32]) -> None:
        self.played.append(len(audio))

    def stop(self) -> None:
        self.stops += 1

    @property
    def speaking(self) -> bool:
        return False

    @property
    def played_fraction(self) -> float:
        return 0.5


class ScriptedDecider:
    """Nhận lượt ở đúng các khung chỉ định; đếm số lần bị reset."""

    name = "scripted"

    def __init__(self, take_at: set[int]) -> None:
        self.take_at, self.resets = take_at, 0

    def decide(self, frame: FeatureFrame) -> TurnDecision:
        outcome = TurnOutcome.TAKE if frame.index in self.take_at else TurnOutcome.HOLD
        return TurnDecision(outcome, self.name, frame.index, frame.start_s)

    def reset(self) -> None:
        self.resets += 1


def frames(pattern: str) -> Iterator[FeatureFrame]:
    """'b' bot đang nói, '.' bot im. Chậm 1 ms mỗi khung để luồng phụ kịp trả lời."""
    for i, mark in enumerate(pattern):
        time.sleep(0.001)
        yield FeatureFrame(i, i * 0.02, 0.02, np.zeros(320, np.float32), bot_speaking=mark == "b")


def call(pattern: str, take_at: set[int], heard: list[str]) -> tuple[Call, FakePlayer, list[int]]:
    player = FakePlayer()
    recorded: list[int] = []
    said = iter(heard)
    c = Call(
        frames(pattern),
        ScriptedDecider(take_at),
        Dialog(NetCoBackend(), load_settings().dialog),
        asr=lambda audio: next(said),
        tts=lambda text: np.zeros(len(text), np.float32),
        player=player,
        record=lambda d: recorded.append(d.frame_index),
        max_turn_frames=100,
    )
    return c, player, recorded


def test_the_bot_greets_first_and_every_frame_is_recorded_once() -> None:
    c, player, recorded = call("." * 20, set(), [])
    c.run()
    assert len(player.played) == 1
    assert recorded == list(range(20))


def test_a_take_while_the_bot_is_silent_gets_a_reply() -> None:
    c, player, _ = call("." * 60, {5}, ["Tôi muốn tra cước"])
    stats = c.run()
    assert stats.takes == 1 and len(player.played) == 2
    assert stats.transcripts[0][0] == "Tôi muốn tra cước" and stats.reply_ms


def test_a_take_while_the_bot_speaks_is_a_barge_in() -> None:
    c, player, _ = call("b" * 10 + "." * 10, {4}, [])
    stats = c.run()
    assert stats.barge_ins == 1 and player.stops == 1 and stats.takes == 0


def test_the_decider_is_reset_whenever_the_bot_starts_or_stops() -> None:
    decider = ScriptedDecider(set())
    player = FakePlayer()
    Call(
        frames("..bbb..bb."),
        decider,
        Dialog(NetCoBackend(), load_settings().dialog),
        asr=lambda audio: "",
        tts=lambda text: np.zeros(1, np.float32),
        player=player,
        record=lambda d: None,
        max_turn_frames=10,
    ).run()
    assert decider.resets == 5  # khung đầu, rồi bốn lần đổi


def test_asking_for_an_agent_ends_the_call_with_context() -> None:
    c, _, _ = call("." * 200, {5}, ["cho tôi gặp nhân viên"])
    stats = c.run()
    assert stats.transfer is not None and stats.frames < 200
