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
    assert abs(last - -34.0) < 1.5


def test_the_floor_follows_a_quieter_room() -> None:
    floor = NoiseFloor(window_frames=50, percentile=10)
    for _ in range(50):
        floor.update(noise(-34.0))
    for _ in range(50):
        last = floor.update(noise(-50.0))
    assert abs(last - -50.0) < 1.5
