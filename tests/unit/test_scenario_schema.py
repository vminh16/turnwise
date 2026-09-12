"""Kịch bản sai phải nổ lúc nạp, vì sai ở đây không crash mà đổi mẫu số."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from evaluation.scenario import SCENARIO_DIR, load, load_all

VALID = """
name: fixture
spec: "SPEC.md §10"
flow: N2
behaviour: fixture
summary: fixture
synthesis:
  speech_dbfs: -14.0
  noise_floor_dbfs: -60.0
segments:
  - {kind: speech, ms: 1000}
  - {kind: silence, ms: 1000}
truth:
  turn_end_ms: 1000
  expected: take
"""


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "s.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_the_committed_scenarios_all_validate() -> None:
    assert len(load_all(SCENARIO_DIR)) == 5


def test_a_take_scenario_without_a_turn_end_is_refused(tmp_path: Path) -> None:
    """Đây là lỗi mà reviewer tìm ra: nó từng lặng lẽ đổi tỉ lệ cắt lời từ 1/4 thành 1/3."""
    body = VALID.replace("turn_end_ms: 1000", "turn_end_ms: null")
    with pytest.raises(ValidationError, match="turn_end_ms"):
        load(write(tmp_path, body))


def test_a_backchannel_scenario_with_a_turn_end_is_refused(tmp_path: Path) -> None:
    body = VALID.replace("expected: take", "expected: backchannel")
    with pytest.raises(ValidationError, match="tiếng đệm"):
        load(write(tmp_path, body))


def test_a_turn_end_past_the_clip_is_refused(tmp_path: Path) -> None:
    body = VALID.replace("turn_end_ms: 1000", "turn_end_ms: 9000")
    with pytest.raises(ValidationError, match="ngoài clip"):
        load(write(tmp_path, body))


def test_a_mistyped_key_is_refused(tmp_path: Path) -> None:
    body = VALID.replace("behaviour:", "behavior:")
    with pytest.raises(ValidationError):
        load(write(tmp_path, body))


def test_an_unknown_segment_kind_is_refused(tmp_path: Path) -> None:
    body = VALID.replace("kind: speech", "kind: music")
    with pytest.raises(ValidationError):
        load(write(tmp_path, body))


def test_a_noise_floor_above_the_speech_level_is_refused(tmp_path: Path) -> None:
    """Sàn ồn cao bằng tiếng nói thì cổng năng lượng vô nghĩa, và không gì báo."""
    body = VALID.replace("noise_floor_dbfs: -60.0", "noise_floor_dbfs: -10.0")
    with pytest.raises(ValidationError, match="sàn ồn"):
        load(write(tmp_path, body))
