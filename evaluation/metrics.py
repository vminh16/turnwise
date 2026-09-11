"""Chấm một lần chạy: cắt lời, độ trễ đáp, tiếng đệm nhận nhầm.

Quy tắc 1 của `SPEC.md` §9.3 định hình cả file này: **không bao giờ báo tỉ lệ cắt lời
mà thiếu độ trễ, và ngược lại**. Hai chỉ số đối kháng — hạ ngưỡng thì đáp nhanh hơn
nhưng cắt lời nhiều hơn — nên một con số đơn lẻ không phải kết quả. Vì vậy `CurvePoint`
mang cả hai trục trong cùng một kiểu, và không có đường nào xuất một trục mà thiếu
trục kia.

BA GIỚI HẠN CỦA GIAI ĐOẠN 0, phải đọc trước khi trích bất kỳ con số nào ở đây:

1. **Độ trễ tính trên file, không phải độ trễ thật.** `SPEC.md` §9.3 quy tắc 4 đòi số
   đo trên hệ chạy trực tiếp; cách tính ở đây bỏ qua đệm audio, thời gian TTS khởi
   động và jitter mạng. Mọi nhãn trong báo cáo phải ghi rõ `file-based`. Số thật là
   việc của Giai đoạn 4.
2. **Âm thanh là tổng hợp.** Năm kịch bản hiện sinh bằng nhiễu trắng, nên các con số
   nói về *đường ống* chứ không nói về độ chính xác trên tiếng Việt thật.
3. **Chưa có chỉ số theo thanh điệu** — kết quả khoa học chính ở §9.1. Nó cần nhãn
   thanh điệu của âm tiết cuối, mà tín hiệu tổng hợp không có âm tiết nào. Giai đoạn 1
   mở khoá chỉ số đó, không phải giai đoạn này.

Thư mục này không chứa đường ra quyết định nào: nó chọn decider bằng cấu hình, chạy,
rồi chấm (`.claude/rules/evaluation.md`).
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from evaluation.scenario import Scenario
from turnwise.types import TurnDecision, TurnOutcome


@dataclass(frozen=True, slots=True)
class RunScore:
    """Kết quả của một decider trên một kịch bản."""

    scenario: str
    expected: str
    turn_end_ms: int | None
    take_at_ms: int | None
    """Thời điểm quyết định TAKE đầu tiên, hoặc `None` nếu decider không bao giờ nhận lượt."""

    interrupted: bool
    """Nhận lượt *trước* khi khách nói xong — bot sẽ chen ngang (SPEC §9.1 chỉ số 1)."""

    response_latency_ms: int | None
    """Khách dứt lời tới lúc bot được phép nói. `None` khi bot cắt lời hoặc không đáp."""

    backchannel_mistaken: bool
    """Tiếng đệm bị nhận thành giành lượt (SPEC §9.1 chỉ số 3)."""


@dataclass(frozen=True, slots=True)
class CurvePoint:
    """Một điểm trên đường cong đánh đổi. Luôn mang **cả hai** trục."""

    threshold_ms: int
    scenarios: int
    interruption_rate: float
    median_response_latency_ms: float | None
    p90_response_latency_ms: float | None
    backchannel_error_rate: float | None
    no_response: int
    """Số kịch bản mà decider không bao giờ nhận lượt — khách nói xong rồi vẫn chờ."""


def score(decisions: Sequence[TurnDecision], scenario: Scenario) -> RunScore:
    """Chấm một lần phát lại.

    Chỉ tính quyết định TAKE **đầu tiên**: đó là lúc bot mở miệng. Các khung TAKE sau
    đó là cùng một sự kiện kéo dài, không phải nhiều lần nhận lượt.
    """
    first_take = next((d for d in decisions if d.outcome is TurnOutcome.TAKE), None)
    take_at_ms = round(first_take.at_s * 1000) if first_take is not None else None
    turn_end_ms = scenario.truth.turn_end_ms

    interrupted = False
    latency_ms: int | None = None
    if turn_end_ms is not None and take_at_ms is not None:
        if take_at_ms < turn_end_ms:
            interrupted = True
        else:
            latency_ms = take_at_ms - turn_end_ms

    return RunScore(
        scenario=scenario.name,
        expected=scenario.truth.expected,
        turn_end_ms=turn_end_ms,
        take_at_ms=take_at_ms,
        interrupted=interrupted,
        response_latency_ms=latency_ms,
        backchannel_mistaken=scenario.truth.expected == "backchannel" and take_at_ms is not None,
    )


def summarise(threshold_ms: int, scores: Sequence[RunScore]) -> CurvePoint:
    """Gộp các kịch bản thành một điểm trên đường cong.

    Tỉ lệ cắt lời tính trên các kịch bản mà khách **thật sự có** kết thúc lượt; kịch
    bản tiếng đệm không có lượt nào để cắt, nên nó vào chỉ số riêng của nó. Trộn hai
    mẫu số lại sẽ làm loãng cả hai.
    """
    turn_scores = [s for s in scores if s.turn_end_ms is not None]
    backchannel_scores = [s for s in scores if s.expected == "backchannel"]
    latencies = [s.response_latency_ms for s in turn_scores if s.response_latency_ms is not None]

    return CurvePoint(
        threshold_ms=threshold_ms,
        scenarios=len(scores),
        interruption_rate=_rate(sum(s.interrupted for s in turn_scores), len(turn_scores)) or 0.0,
        median_response_latency_ms=float(np.median(latencies)) if latencies else None,
        p90_response_latency_ms=float(np.percentile(latencies, 90)) if latencies else None,
        backchannel_error_rate=_rate(
            sum(s.backchannel_mistaken for s in backchannel_scores), len(backchannel_scores)
        ),
        no_response=sum(s.take_at_ms is None for s in turn_scores),
    )


def _rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


def write_curve(points: Sequence[CurvePoint], path: Path) -> Path:
    """Ghi đường cong ra CSV. Mọi cột của `CurvePoint` đều ra, không cắt bớt.

    Cắt bớt cột là cách dễ nhất để vô tình báo một trục mà thiếu trục kia, và §9.3
    quy tắc 1 tồn tại chính để chặn điều đó.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(point) for point in points]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
