"""Không có file telemetry thì một lần chạy hỏng không phân tích lại được."""

import ast
import json
from pathlib import Path

import pytest

from turnwise.config import TelemetryConfig
from turnwise.telemetry.collector import TelemetryCollector
from turnwise.types import Tone, TurnDecision, TurnOutcome

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "turnwise"


def decision(index: int, **overrides: object) -> TurnDecision:
    fields: dict[str, object] = {
        "outcome": TurnOutcome.HOLD,
        "decider": "silence_threshold",
        "frame_index": index,
        "at_s": index * 0.02,
    }
    fields.update(overrides)
    return TurnDecision(**fields)  # type: ignore[arg-type]


@pytest.fixture
def config(tmp_path: Path) -> TelemetryConfig:
    return TelemetryConfig(dir=tmp_path, enabled=True)


def test_one_decision_is_one_line(config: TelemetryConfig) -> None:
    with TelemetryCollector(config, "silence_threshold", "200ms") as collector:
        for index in range(5):
            collector.record(decision(index))

    lines = collector.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    assert [json.loads(line)["frame_index"] for line in lines] == list(range(5))


def test_the_name_becomes_a_directory_path(config: TelemetryConfig) -> None:
    """Một dải quét 11 ngưỡng phải tìm lại được bằng mắt."""
    with TelemetryCollector(config, "silence_threshold", "200ms") as collector:
        collector.record(decision(0))

    assert collector.path == config.dir / "silence_threshold" / "200ms.jsonl"
    assert collector.path.is_file()


def test_a_row_carries_everything_needed_to_reconstruct_it(config: TelemetryConfig) -> None:
    with TelemetryCollector(config, "run") as collector:
        collector.record(
            decision(
                7,
                outcome=TurnOutcome.BACKCHANNEL,
                scores={"tone": 0.8, "semantic": None},
                final_tone=Tone.DROP,
            )
        )

    row = json.loads(collector.path.read_text(encoding="utf-8"))
    assert row == {
        "outcome": "backchannel",
        "decider": "silence_threshold",
        "frame_index": 7,
        "at_s": 0.14,
        "scores": {"tone": 0.8, "semantic": None},
        "final_tone": "drop",
    }


def test_an_abstaining_scorer_stays_distinguishable_from_a_low_score(
    config: TelemetryConfig,
) -> None:
    """Bỏ phiếu trắng là `null`, không phải 0.0 — bảng ablation phụ thuộc vào chỗ này."""
    with TelemetryCollector(config, "run") as collector:
        collector.record(decision(0, scores={"a": None, "b": 0.0}))

    assert json.loads(collector.path.read_text(encoding="utf-8"))["scores"] == {
        "a": None,
        "b": 0.0,
    }


def test_disabled_telemetry_writes_nothing(tmp_path: Path) -> None:
    config = TelemetryConfig(dir=tmp_path, enabled=False)
    with TelemetryCollector(config, "silence_threshold", "200ms") as collector:
        collector.record(decision(0))

    assert not collector.path.exists()
    assert list(tmp_path.iterdir()) == []


def test_rows_survive_a_crash_before_close(config: TelemetryConfig) -> None:
    """Xả từng dòng: tiến trình chết giữa chừng thì phần đã ghi vẫn đọc được."""
    collector = TelemetryCollector(config, "run")
    for index in range(3):
        collector.record(decision(index))

    assert len(collector.path.read_text(encoding="utf-8").splitlines()) == 3


def test_recording_after_close_is_a_no_op(config: TelemetryConfig) -> None:
    collector = TelemetryCollector(config, "run")
    collector.record(decision(0))
    collector.close()
    collector.record(decision(1))

    assert len(collector.path.read_text(encoding="utf-8").splitlines()) == 1


@pytest.mark.parametrize("name", [(), ("",), ("a/b",), ("..",)])
def test_a_bad_name_is_refused(config: TelemetryConfig, name: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        TelemetryCollector(config, *name)


def imported_modules(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_the_turn_layer_does_not_know_telemetry_exists() -> None:
    """ADR-0003 và SPEC §8: telemetry chỉ đọc, và `turn` không được gọi nó.

    Kiểm trên câu lệnh import chứ không trên chuỗi: `turn/base.py` có nhắc telemetry
    trong docstring để giải thích vì sao nó *không* gọi, và đó là điều nên có.
    """
    offenders = sorted(
        path.relative_to(PACKAGE).as_posix()
        for path in (PACKAGE / "turn").rglob("*.py")
        if any(name.startswith("turnwise.telemetry") for name in imported_modules(path))
    )
    assert not offenders, offenders
