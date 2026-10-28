"""Bộ phân tích: bốc mẫu không ai sắp lại được, cửa sổ tái lập, kết thúc suy đúng (ADR-0007)."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from evaluation import analysis_sample as an
from evaluation import annotation
from turnwise.config import AnalysisSampleConfig, load_settings

RATE = 16_000


def item(item_id: str, region: str = "south", language: str = "vi", restricted: str = "") -> an.Row:
    row = dict.fromkeys(an.CATALOG_COLUMNS, "")
    row.update(source="viet-stories", item_id=item_id, region=region, language=language)
    row["restricted"] = restricted
    return row


@pytest.fixture
def cfg(tmp_path: Path) -> AnalysisSampleConfig:
    base = load_settings().analysis_sample
    return base.model_copy(
        update={
            "audio_dir": tmp_path,
            "window_s": 10.0,
            "skip_head_s": 5.0,
            "skip_tail_s": 2.0,
            "context_s": 1.0,
        }
    )


# --- bốc hội thoại ----------------------------------------------------------------------


def test_only_unrestricted_vietnamese_items_are_ranked() -> None:
    catalog = [item("V1"), item("V2", language="en"), item("V3", restricted="yes")]
    assert [r["item_id"] for r in an.rank(catalog, [], seed=1)] == ["V1"]


def test_adding_items_never_reorders_the_existing_ones() -> None:
    """Thứ hạng chỉ phụ thuộc mã mục, nên bổ sung danh mục không mở cửa cho chọn lại."""
    first = [item(f"V{i}") for i in range(20)]
    before = [r["item_id"] for r in an.rank(first, [], seed=7)]
    after = [
        r["item_id"] for r in an.rank([*first, *(item(f"W{i}") for i in range(20))], [], seed=7)
    ]
    assert [i for i in after if i in before] == before


def test_ranks_count_within_each_region() -> None:
    rows = an.rank([item("N1", "north"), item("S1"), item("N2", "north")], [], seed=1)
    assert sorted((r["region"], r["rank"]) for r in rows) == [
        ("north", "1"),
        ("north", "2"),
        ("south", "1"),
    ]


def test_reranking_keeps_what_annotators_wrote() -> None:
    rows = an.rank([item("V1")], [], seed=1)
    rows[0].update(excluded="music", minutes_spent="42")
    again = an.rank([item("V1")], rows, seed=1)
    assert (again[0]["excluded"], again[0]["minutes_spent"]) == ("music", "42")


def test_an_unknown_region_is_refused() -> None:
    with pytest.raises(ValueError, match="region"):
        an.rank([item("V1", region="hue")], [], seed=1)


def test_an_excluded_item_hands_its_slot_to_the_next_rank() -> None:
    rows = an.rank([item(f"V{i}") for i in range(5)], [], seed=1)
    rows[0]["excluded"] = "music"
    assert [r["item_id"] for r in an.due(rows, 2)] == [rows[1]["item_id"], rows[2]["item_id"]]


# --- bốc cửa sổ -------------------------------------------------------------------------


def test_the_window_is_reproducible_and_inside_the_allowed_span(cfg: AnalysisSampleConfig) -> None:
    key = an.sample_key(1, "viet-stories", "V1")
    window = an.choose_window([100.0], key, cfg)
    assert window == an.choose_window([100.0], key, cfg)
    assert window is not None
    assert window.start >= cfg.skip_head_s + cfg.context_s
    assert window.end <= 100.0 - cfg.skip_tail_s
    assert window.context_start == pytest.approx(window.start - cfg.context_s)


def test_a_conversation_too_short_for_a_window_gets_none(cfg: AnalysisSampleConfig) -> None:
    assert an.choose_window([15.0], "0" * 64, cfg) is None


def test_prepare_writes_a_textgrid_and_never_overwrites_it(cfg: AnalysisSampleConfig) -> None:
    folder = cfg.audio_dir / "viet-stories"
    folder.mkdir()
    x = np.zeros(RATE * 40, dtype=np.float32)
    x[RATE * 10 : RATE * 30] = np.random.default_rng(0).standard_normal(RATE * 20) * 0.1
    sf.write(folder / "V1.wav", x, RATE)
    row = an.rank([item("V1")], [], seed=1)[0]

    assert an.prepare(row, cfg, load_settings().annotation).startswith("wrote")
    grid = annotation.read_textgrid(folder / "V1.TextGrid")
    assert {"window", "draft", "A", "B", "nonspeech"} <= set(grid)
    assert row["audio_file"] == "viet-stories/V1.wav"
    assert an.prepare(row, cfg, load_settings().annotation).startswith("kept")


# --- nhãn -------------------------------------------------------------------------------


def ipu(speaker: str, start: float, end: float, onset: str, words: str = "") -> an.Ipu:
    return an.Ipu(speaker, start, end, onset, frozenset(), words)


def test_parse_reads_onset_attributes_and_words() -> None:
    got = an.parse("A", 0.0, 1.0, "H filled | thì ờ", "t")
    assert (got.onset, got.attributes, got.words) == ("H", frozenset({"filled"}), "thì ờ")


@pytest.mark.parametrize("text", ["take | dạ", "S loud | dạ", "| dạ"])
def test_parse_refuses_typos(text: str) -> None:
    with pytest.raises(ValueError):
        an.parse("A", 0.0, 1.0, text, "t")


def outcomes(*ipus: an.Ipu) -> list[str]:
    return [e.outcome for e in an.endings(list(ipus))]


def test_a_pause_then_the_same_speaker_is_a_hold() -> None:
    assert outcomes(ipu("A", 0, 1, "S"), ipu("A", 2, 3, "H"))[0] == "hold"


def test_the_other_speaker_starting_cleanly_is_a_shift() -> None:
    assert outcomes(ipu("A", 0, 1, "S"), ipu("B", 1.5, 2, "S"))[0] == "shift"


def test_a_backchannel_does_not_take_the_turn() -> None:
    first = an.endings([ipu("A", 0, 1, "S"), ipu("B", 1.2, 1.4, "BC"), ipu("A", 2, 3, "H")])[0]
    assert (first.outcome, first.backchannel) == ("hold", True)


def test_a_pause_interruption_ends_the_ipu_as_interrupted() -> None:
    assert outcomes(ipu("A", 0, 1, "S"), ipu("B", 1.5, 2, "PI"))[0] == "interrupted"


def test_an_overlapping_interruption_belongs_to_the_ipu_it_overlaps() -> None:
    assert outcomes(ipu("A", 0, 2, "S"), ipu("B", 1.5, 3, "I"))[0] == "interrupted"


def test_a_failed_butting_in_leaves_the_turn_with_the_speaker() -> None:
    assert (
        outcomes(ipu("A", 0, 2, "S"), ipu("B", 1.5, 1.8, "BI"), ipu("A", 2.5, 3, "H"))[0] == "hold"
    )


def test_the_last_ipu_of_the_window_is_censored() -> None:
    assert outcomes(ipu("A", 0, 1, "S"))[0] == "censored"


def test_the_final_tone_comes_from_the_words() -> None:
    (end,) = an.endings([ipu("A", 0, 1, "S", "tôi ở huế")])
    assert end.tone == "rising"
