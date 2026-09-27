"""Nối các tầng thành một cuộc gọi: khung -> decider -> (ASR -> dialog -> TTS) -> loa.

Đây là **chỗ duy nhất** ghi mỗi `TurnDecision` xuống telemetry (`AGENTS.md`, ADR-0003): vòng
lặp gọi `record` đúng một lần cho mỗi khung.

Ba luật vận hành:

- Decider được reset mỗi khi bot bắt đầu hoặc dứt lời, như lúc chấm trên bộ dữ liệu vàng
  (`evaluation/golden.py`), để số đo offline và hành vi sống cùng một định nghĩa lượt.
- Bot đang nói mà decider nhận lượt là **khách ngắt lời** (SPEC R3): dừng bot ngay, báo dialog
  đã đọc tới đâu (R11). `BACKCHANNEL` thì bot nói tiếp (R4).
- ASR, dialog và TTS chạy ở một luồng phụ. Chúng tốn hàng trăm mili-giây; chạy ngay trong vòng
  lặp thì khung dồn lại trong bộ đệm vòng và tràn.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from turnwise.dialog.machine import Dialog, Reply
from turnwise.transport.speech import Asr, Tts
from turnwise.turn.base import TurnDecider
from turnwise.types import FeatureFrame, TurnDecision, TurnOutcome

logger = logging.getLogger(__name__)


class Player(Protocol):
    def play(self, audio: NDArray[np.float32]) -> None: ...

    def stop(self) -> None: ...

    @property
    def speaking(self) -> bool: ...

    @property
    def played_fraction(self) -> float: ...


@dataclass
class CallStats:
    frames: int = 0
    takes: int = 0
    barge_ins: int = 0
    backchannels: int = 0
    reply_ms: list[float] = field(default_factory=list)
    """Từ khung nhận lượt tới lúc tiếng bot được đưa vào bộ phát: ASR + dialog + TTS."""

    transcripts: list[tuple[str, str]] = field(default_factory=list)
    """(lời khách, lời bot) theo thứ tự, cho bảng theo dõi và log."""

    transfer: dict[str, str] | None = None


class Call:
    def __init__(
        self,
        source: Iterable[FeatureFrame],
        decider: TurnDecider,
        dialog: Dialog,
        asr: Asr,
        tts: Tts,
        player: Player,
        record: Callable[[TurnDecision], None],
        max_turn_frames: int,
        on_frame: Callable[[CallStats, TurnDecision], None] | None = None,
    ) -> None:
        self._source = source
        self._decider = decider
        self._dialog = dialog
        self._asr = asr
        self._tts = tts
        self._player = player
        self._record = record
        self._on_frame = on_frame
        self._turn: deque[NDArray[np.float32]] = deque(maxlen=max_turn_frames)
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="respond")
        self.stats = CallStats()

    def run(self) -> CallStats:
        self._say(self._dialog.greet())
        pending: Future[Reply] | None = None
        bot_was: bool | None = None
        ending = False
        try:
            for frame in self._source:
                if frame.bot_speaking != bot_was:
                    self._decider.reset()
                    bot_was = frame.bot_speaking
                decision = self._decider.decide(frame)
                self._record(decision)
                self.stats.frames += 1
                self._turn.append(frame.samples.copy())

                if frame.bot_speaking:
                    if decision.outcome == TurnOutcome.TAKE and not ending:
                        self._barge_in()
                    elif decision.outcome == TurnOutcome.BACKCHANNEL:
                        self.stats.backchannels += 1
                elif decision.outcome == TurnOutcome.TAKE and pending is None and not ending:
                    self.stats.takes += 1
                    audio = np.concatenate(list(self._turn))
                    self._turn.clear()
                    pending = self._worker.submit(self._respond, audio, time.perf_counter())

                if pending is not None and pending.done():
                    reply = pending.result()
                    pending = None
                    ending = reply.end
                if ending and pending is None and not self._player.speaking:
                    break
                if self._on_frame is not None:
                    self._on_frame(self.stats, decision)
        finally:
            self._worker.shutdown(wait=False, cancel_futures=True)
        return self.stats

    def _barge_in(self) -> None:
        fraction = self._player.played_fraction
        self._player.stop()
        self._dialog.interrupted(fraction)
        self.stats.barge_ins += 1
        logger.info("barge-in after %.0f%% of the bot's line", fraction * 100)

    def _respond(self, audio: NDArray[np.float32], taken_at: float) -> Reply:
        heard = self._asr(audio)
        reply = self._dialog.hear(heard)
        self._say(reply)
        self.stats.reply_ms.append((time.perf_counter() - taken_at) * 1000)
        self.stats.transcripts.append((heard, reply.text))
        if reply.transfer is not None:
            self.stats.transfer = reply.transfer
            logger.info("transfer with context %s", reply.transfer)
        return reply

    def _say(self, reply: Reply) -> None:
        self._player.play(self._tts(reply.text))
