"""Nạp và phát lại các kịch bản ở `scenarios/`.

Bộ kịch bản là vòng phản hồi nhanh nhất của dự án: tất định, chạy trong CI, không
cần micro. Mỗi file YAML mô tả một trong năm phép thử ở `SPEC.md` §10.

**Giai đoạn 0 sinh âm thanh tổng hợp**, vì chưa có dữ liệu đóng vai. Tiếng nói là
nhiễu trắng ở mức quy định trong chính file kịch bản, im lặng là sàn ồn thấp hơn
nhiều. Đủ để kiểm tra đường ống, cổng năng lượng của B1 và tính tất định — **không**
đủ để nói bất cứ điều gì về độ chính xác. Giai đoạn 1 thay phần sinh này bằng file
wav thu thật, và phần còn lại của module giữ nguyên.

Âm thanh đi qua đúng `WavFrameSource` mà đường chạy thật dùng, chứ không đi tắt vào
bộ nhớ: nếu bộ phát khung sai, bộ kịch bản phải sai theo — đó là điểm của nó.

Module này nằm ở `evaluation/` chứ không ở `tests/` vì `run_baseline.py` ở pha 0.6
cũng phát lại đúng những kịch bản này. Hai bản sinh tín hiệu riêng cho test và cho
đường cong nghĩa là đường cong đo trên một âm thanh khác với âm thanh đã kiểm.
"""

from __future__ import annotations

import zlib
from pathlib import Path
from typing import Any, Literal

import numpy as np
import soundfile as sf
import yaml
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, model_validator

from turnwise.audio.source import WavFrameSource
from turnwise.config import AudioConfig
from turnwise.telemetry.collector import TelemetryCollector
from turnwise.turn.base import TurnDecider
from turnwise.types import TurnDecision

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios"


class _Node(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Segment(_Node):
    kind: Literal["speech", "silence"]
    ms: int
    note: str = ""


class Truth(_Node):
    """Sự thật nền của kịch bản, dùng để chấm ở pha 0.6."""

    turn_end_ms: int | None
    expected: Literal["take", "hold", "backchannel"]


class Synthesis(_Node):
    speech_dbfs: float
    noise_floor_dbfs: float


class Scenario(_Node):
    """Một kịch bản đã nạp và đã kiểm.

    Kiểm lúc nạp chứ không lúc chấm, vì sai ở đây **không gây lỗi** mà lặng lẽ đổi
    mẫu số: một kịch bản `expected: take` bị gõ nhầm `turn_end_ms: null` sẽ rơi khỏi
    mẫu số của tỉ lệ cắt lời, tỉ lệ đổi từ 1/4 thành 1/3, và không có gì báo.
    """

    name: str
    spec: str
    flow: str
    behaviour: str
    summary: str
    synthesis: Synthesis
    segments: tuple[Segment, ...]
    truth: Truth
    path: Path

    @property
    def speech_dbfs(self) -> float:
        return self.synthesis.speech_dbfs

    @property
    def noise_floor_dbfs(self) -> float:
        return self.synthesis.noise_floor_dbfs

    @property
    def duration_ms(self) -> int:
        return sum(segment.ms for segment in self.segments)

    @model_validator(mode="after")
    def _truth_matches_the_segments(self) -> Scenario:
        if not self.segments:
            raise ValueError(f"{self.name}: kịch bản không có đoạn nào")

        turn_end_ms = self.truth.turn_end_ms
        if self.truth.expected == "take" and turn_end_ms is None:
            raise ValueError(
                f"{self.name}: expected=take thì phải có turn_end_ms, "
                "nếu không kịch bản rơi khỏi mẫu số của tỉ lệ cắt lời"
            )
        if self.truth.expected == "backchannel" and turn_end_ms is not None:
            raise ValueError(f"{self.name}: tiếng đệm không có lượt nào kết thúc")
        if turn_end_ms is not None and not 0 < turn_end_ms <= self.duration_ms:
            raise ValueError(
                f"{self.name}: turn_end_ms={turn_end_ms} nằm ngoài clip dài {self.duration_ms}ms"
            )
        if self.synthesis.noise_floor_dbfs >= self.synthesis.speech_dbfs:
            raise ValueError(f"{self.name}: sàn ồn không được cao bằng mức tiếng nói")
        return self


def load(path: Path) -> Scenario:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Scenario(**raw, path=path)


def load_all(directory: Path = SCENARIO_DIR) -> list[Scenario]:
    """Mọi kịch bản, theo thứ tự tên file — tiền tố số giữ thứ tự khớp SPEC §10."""
    return [load(path) for path in sorted(directory.glob("*.yaml"))]


def synthesize(scenario: Scenario, audio: AudioConfig) -> NDArray[np.float32]:
    """Dựng tín hiệu của kịch bản.

    Hạt giống lấy từ tên kịch bản qua `crc32`, nên cùng một kịch bản cho cùng một
    tín hiệu ở mọi máy và mọi lần chạy. Tất định là điều kiện để so sánh hai lần
    chạy với nhau; một hạt giống ngẫu nhiên biến mọi khác biệt thành nhiễu.
    """
    rng = np.random.default_rng(zlib.crc32(scenario.name.encode("utf-8")))
    blocks = []
    for segment in scenario.segments:
        dbfs = scenario.speech_dbfs if segment.kind == "speech" else scenario.noise_floor_dbfs
        count = audio.sample_rate_hz * segment.ms // 1000
        blocks.append(rng.standard_normal(count) * 10 ** (dbfs / 20))
    return np.concatenate(blocks).clip(-1.0, 1.0).astype(np.float32)


def write_wav(scenario: Scenario, audio: AudioConfig, directory: Path) -> Path:
    """Ghi tín hiệu ra file tạm để phát lại qua đúng nguồn khung của đường chạy thật.

    Không vi phạm lệnh cấm ghi audio ra đĩa: lệnh đó áp cho đường chạy runtime
    (`SPEC.md` §6), còn đây là đường offline và file nằm trong thư mục tạm của test.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{scenario.name}.wav"
    sf.write(path, synthesize(scenario, audio), audio.sample_rate_hz, subtype="PCM_16")
    return path


def replay(
    scenario: Scenario,
    decider: TurnDecider,
    audio: AudioConfig,
    directory: Path,
    collector: TelemetryCollector | None = None,
) -> list[TurnDecision]:
    """Chạy một kịch bản qua một decider, trả về quyết định của từng khung.

    Decider được `reset()` trước khi chạy: trạng thái sót lại từ lần chạy trước làm
    sai điểm mà không crash.
    """
    decider.reset()
    decisions = []
    for frame in WavFrameSource(write_wav(scenario, audio, directory), audio):
        decision = decider.decide(frame)
        if collector is not None:
            collector.record(decision)
        decisions.append(decision)
    return decisions
