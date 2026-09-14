"""Nạp và kiểm các kịch bản đóng vai ở `roleplay/`, dùng để thu bộ dữ liệu vàng.

Khác `scenarios/`: bộ kia là tín hiệu tổng hợp để CI phát lại; bộ này là **kịch bản cho
người thật** nói chuyện với bot trong buổi thu ở Giai đoạn 1. Dữ liệu thu được là dữ
liệu **đánh giá**, không phải dữ liệu huấn luyện (`docs/progress.md`, Giai đoạn 1).

Lời bot viết đủ từng chữ, vì bot được đóng bằng các câu thu sẵn và người điều khiển bấm
phát (Wizard-of-Oz): chưa có `dialog/` và chưa chốt giọng TTS. Lời khách **không** viết
sẵn, chỉ có chỉ dẫn hành vi — người đọc thuộc lòng thì mất đúng thứ cần đo: ngập ngừng,
tiếng đệm, nói đè tự nhiên. Ngoại lệ duy nhất là câu trả lời ngắn, có danh sách gợi ý để
phủ đủ sáu thanh ở âm tiết cuối.

Module ở `evaluation/` vì mục đích của dữ liệu là đánh giá, và để công cụ thu ở pha 1.4
chỉ còn là một lớp CLI mỏng trong `scripts/`.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from turnwise.types import Tone

ROLEPLAY_DIR = Path(__file__).resolve().parents[1] / "roleplay"

Flow = Literal["N1", "N2", "N3", "N4", "N5"]

# Sáu hành vi phải thu, lấy từ SPEC §4.3 và §10. `long_answer` có mặt vì phép thử §10.5
# là một phép so sánh: câu ngắn không được chậm hơn câu dài, nên phải thu cả hai.
Behaviour = Literal[
    "hesitation",
    "backchannel",
    "barge_in",
    "agent_request",
    "short_answer",
    "long_answer",
]

# Hai hành vi này là nói đè: chỉ tồn tại khi bot đang nói một đoạn đủ dài để chen vào.
OVERLAP: frozenset[str] = frozenset({"backchannel", "barge_in"})

# Dấu thanh sau khi tách NFD. Dấu mũ, dấu trăng và dấu móc là dấu nguyên âm, không phải
# dấu thanh, nên cố ý không có ở đây.
_TONE_MARKS = {
    "̀": Tone.FALLING,
    "́": Tone.RISING,
    "̉": Tone.DIPPING,
    "̃": Tone.BROKEN,
    "̣": Tone.DROP,
}


def final_syllable_tone(text: str) -> Tone:
    """Thanh của âm tiết cuối, đọc từ chữ viết.

    Trả `Tone.UNKNOWN` khi âm tiết cuối không phải chữ (ví dụ chữ số), vì "8" đọc là
    "tám" hay "tám mươi" tuỳ ngữ cảnh.
    """
    words = [word.strip(".,!?…:;\"'()") for word in text.split()]
    words = [word for word in words if word]
    if not words or not any(char.isalpha() for char in words[-1]):
        return Tone.UNKNOWN
    for char in unicodedata.normalize("NFD", words[-1]):
        if char in _TONE_MARKS:
            return _TONE_MARKS[char]
    return Tone.LEVEL


class _Node(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Step(_Node):
    """Một lượt bot nói, và điều người đóng vai khách được dặn làm quanh lượt đó."""

    bot: str
    reading: Literal["number", "amount", "address", "terms"] | None = None
    customer: str
    behaviours: tuple[Behaviour, ...] = ()
    replies: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _behaviours_fit_the_step(self) -> Step:
        if len(set(self.behaviours)) != len(self.behaviours):
            raise ValueError(f"hành vi lặp lại trong một bước: {self.behaviours}")
        overlap = OVERLAP.intersection(self.behaviours)
        if overlap and self.reading is None:
            raise ValueError(
                f"{sorted(overlap)} là nói đè, cần bot đang đọc một đoạn dài; "
                "đặt `reading` cho bước này"
            )
        if {"short_answer", "long_answer"} <= set(self.behaviours):
            raise ValueError("một bước không thể vừa là câu trả lời ngắn vừa là câu dài")
        if "short_answer" in self.behaviours and not self.replies:
            raise ValueError("short_answer cần `replies` gợi ý để phủ đủ thanh điệu")
        if self.replies and "short_answer" not in self.behaviours:
            raise ValueError("`replies` chỉ dành cho bước short_answer")
        return self


class Script(_Node):
    """Một kịch bản đóng vai đã nạp và đã kiểm.

    Kiểm lúc nạp, cùng lý do như `evaluation/scenario.py`: một kịch bản gõ sai không
    làm hỏng gì ngay, nó lặng lẽ làm buổi thu thiếu đúng hành vi cần đo, và chỉ phát
    hiện ra khi đã thu xong.
    """

    name: str
    flow: Flow
    title: str
    summary: str
    persona: str
    props: dict[str, str] = {}
    steps: tuple[Step, ...]
    path: Path

    @field_validator("steps")
    @classmethod
    def _has_steps(cls, steps: tuple[Step, ...]) -> tuple[Step, ...]:
        if not steps:
            raise ValueError("kịch bản không có bước nào")
        return steps

    @property
    def behaviours(self) -> set[str]:
        return {behaviour for step in self.steps for behaviour in step.behaviours}


class CommonPrompts(_Node):
    """Các câu bot dùng chung cho mọi kịch bản, để người điều khiển xử lý chỗ lệch kịch bản."""

    prompts: dict[str, str]
    path: Path


def load(path: Path) -> Script:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Script(**raw, path=path)


def load_all(directory: Path = ROLEPLAY_DIR) -> list[Script]:
    """Mọi kịch bản, theo thứ tự tên file; tiền tố `nX-` giữ thứ tự khớp SPEC §4.1."""
    return [load(path) for path in sorted(directory.glob("n[1-5]-*.yaml"))]


def load_common(directory: Path = ROLEPLAY_DIR) -> CommonPrompts:
    path = directory / "common.yaml"
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CommonPrompts(**raw, path=path)
