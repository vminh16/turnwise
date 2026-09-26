"""Pha 1.6: bản nháp TextGrid đúng định dạng Praat, và nhãn người gán đọc lại được."""

from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from evaluation import annotation
from turnwise.config import AnnotationConfig, load_settings

RATE = 48_000


@pytest.fixture(scope="module")
def config() -> AnnotationConfig:
    return load_settings().annotation


def signal(*spans: tuple[float, float], seconds: float = 3.0) -> np.ndarray:
    x = np.zeros(int(RATE * seconds), dtype=np.float32)
    rng = np.random.default_rng(0)
    for start, end in spans:
        a, b = int(start * RATE), int(end * RATE)
        x[a:b] = rng.standard_normal(b - a).astype(np.float32) * 0.1  # khoảng -20 dBFS
    return x


def test_short_gaps_merge_and_short_blips_drop(config: AnnotationConfig) -> None:
    """§4.1: lặng dưới 180 ms thuộc về đoạn nói; tiếng dưới 90 ms không phải đoạn nói."""
    x = signal((0.5, 1.0), (1.1, 1.5), (2.0, 2.05))
    assert annotation.ipus(x, RATE, config) == [(0.5, 1.5)]


def test_a_gap_longer_than_the_merge_window_splits(config: AnnotationConfig) -> None:
    x = signal((0.5, 1.0), (1.3, 1.6))
    assert annotation.ipus(x, RATE, config) == [(0.5, 1.0), (1.3, 1.6)]


def test_the_floor_follows_the_recording_noise(config: AnnotationConfig) -> None:
    """Nền ồn -36 dBFS trên một micro kém: ngưỡng cố định -40 sẽ coi cả bản là một đoạn nói."""
    x = (
        signal((1.0, 1.5))
        + np.random.default_rng(1).standard_normal(RATE * 3).astype(np.float32) * 0.015
    )
    assert annotation.ipus(x, RATE, config) == [(1.0, 1.5)]


def test_textgrid_round_trips_including_vietnamese_and_quotes(tmp_path: Path) -> None:
    path = tmp_path / "a.TextGrid"
    annotation.write_textgrid(path, 2.0, {"caller_words": [(0.5, 1.0, 'dạ "vâng"')], "x": []})
    tiers = annotation.read_textgrid(path)
    assert tiers["caller_words"] == [(0.0, 0.5, ""), (0.5, 1.0, 'dạ "vâng"'), (1.0, 2.0, "")]
    assert tiers["x"] == [(0.0, 2.0, "")]


def test_praat_utf16_files_are_read(tmp_path: Path) -> None:
    """Praat lưu file có chữ Việt bằng UTF-16 kèm BOM."""
    path = tmp_path / "a.TextGrid"
    annotation.write_textgrid(path, 1.0, {"caller_act": [(0.1, 0.4, "take")]})
    path.write_bytes(path.read_text("utf-8").encode("utf-16"))
    assert annotation.read_textgrid(path)["caller_act"][1] == (0.1, 0.4, "take")


def labelled(tmp_path: Path, act: str, words: str = "") -> Path:
    path = tmp_path / "a.TextGrid"
    annotation.write_textgrid(
        path,
        2.0,
        {"caller_act": [(0.5, 1.0, act)], "caller_words": [(0.5, 1.0, words)]},
    )
    return path


def test_labels_carry_act_attributes_and_words(tmp_path: Path) -> None:
    [ipu] = annotation.labels(labelled(tmp_path, "hold filled", "để xem nào ờ"))
    assert (ipu.act, ipu.attributes, ipu.words) == ("hold", frozenset({"filled"}), "để xem nào ờ")


def test_an_unlabelled_ipu_reads_as_none(tmp_path: Path) -> None:
    [ipu] = annotation.labels(labelled(tmp_path, "?"))
    assert ipu.act is None


@pytest.mark.parametrize("bad", ["taek", "take agnet"])
def test_a_misspelt_label_is_refused(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ValueError):
        annotation.labels(labelled(tmp_path, bad))


def test_fill_covers_the_whole_file_without_overlaps() -> None:
    out = annotation.fill([(0.5, 1.2, "a"), (1.0, 1.5, "b")], 2.0)
    assert out[0][0] == 0.0 and out[-1][1] == 2.0
    assert all(a[1] == b[0] for a, b in pairwise(out))
