"""Bảng theo dõi trong terminal lúc cuộc gọi đang chạy (SPEC R10). Chỉ cần đọc được (SPEC §11).

Chỉ đọc: nhận số liệu và quyết định mới nhất, vẽ lại, không trả gì về cho đường ống. Nhận số liệu
dạng `Mapping` thuần để tầng này không phải biết `transport/` tồn tại.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Self

from rich.live import Live
from rich.table import Table

from turnwise.types import TurnDecision


class Dashboard:
    def __init__(self, refresh_every_frames: int) -> None:
        self._every = refresh_every_frames
        self._count = 0
        self._live = Live(Table(), auto_refresh=False)

    def __enter__(self) -> Self:
        self._live.__enter__()
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._live.__exit__(kind, value, traceback)

    def update(self, numbers: Mapping[str, object], decision: TurnDecision) -> None:
        self._count += 1
        if self._count % self._every:
            return
        table = Table(title=f"turnwise - {decision.decider}", show_header=False)
        for key, value in numbers.items():
            table.add_row(key, str(value))
        table.add_row("outcome", decision.outcome.value)
        for name, score in decision.scores.items():
            table.add_row(f"score {name}", "abstain" if score is None else f"{score:.2f}")
        self._live.update(table, refresh=True)
