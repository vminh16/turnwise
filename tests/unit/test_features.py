"""Nền ồn do tầng audio ước lượng: theo kịp micro, và không bị một tràng nói kéo lên."""

import numpy as np

from turnwise.audio.features import DIGITAL_SILENCE_DBFS, NoiseFloor, level_dbfs


def noise(dbfs: float, n: int = 320) -> np.ndarray:
    rng = np.random.default_rng(0)
    return (rng.standard_normal(n) * 10 ** (dbfs / 20)).astype(np.float32)


def test_digital_silence_is_a_number_not_minus_infinity() -> None:
    assert level_dbfs(np.zeros(320, np.float32)) == DIGITAL_SILENCE_DBFS


def test_the_floor_is_the_quiet_part_even_while_speech_dominates() -> None:
    floor = NoiseFloor(window_frames=100, percentile=10)
    for i in range(100):
        last = floor.update(noise(-34.0) if i % 5 == 0 else noise(-10.0))
    assert last is not None and abs(last - -34.0) < 1.5


def test_the_floor_follows_a_quieter_room() -> None:
    floor = NoiseFloor(window_frames=50, percentile=10)
    for _ in range(50):
        floor.update(noise(-34.0))
    for _ in range(50):
        last = floor.update(noise(-50.0))
    assert last is not None and abs(last - -50.0) < 1.5


def test_nothing_is_reported_before_a_whole_window() -> None:
    """Một kênh mở ra bằng tiếng nói không được lấy tiếng nói làm nền ồn."""
    floor = NoiseFloor(window_frames=10, percentile=10)
    early = [floor.update(noise(-14.0)) for _ in range(9)]
    assert early == [None] * 9 and floor.update(noise(-14.0)) is not None
