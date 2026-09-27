"""B1 phải cắm vừa seam `TurnDecider` — phép thử rẻ nhất cho toàn bộ thiết kế tầng turn."""

import numpy as np
import pytest

from turnwise.config import GateConfig, load_settings
from turnwise.turn.base import TurnDecider
from turnwise.turn.deciders.silence_threshold import SilenceThresholdDecider
from turnwise.types import FeatureFrame, TurnOutcome

FRAME_S = 0.02
LOUD = 0.2  # khoảng -14 dBFS
QUIET = 0.0
# Cổng cố định -45 dBFS: khung trong test không mang nền ồn, nên margin không có tác dụng.
GATE = GateConfig(floor_dbfs=-45.0, margin_db=12.0, merge_ms=180)


def frames(pattern: str) -> list[FeatureFrame]:
    """`pattern`: mỗi ký tự là một khung — 's' có tiếng, '.' im lặng."""
    rng = np.random.default_rng(0)
    out = []
    for index, mark in enumerate(pattern):
        amplitude = LOUD if mark == "s" else QUIET
        samples = (rng.standard_normal(320) * amplitude).astype(np.float32)
        out.append(
            FeatureFrame(
                index=index,
                start_s=index * FRAME_S,
                duration_s=FRAME_S,
                samples=samples,
            )
        )
    return out


@pytest.fixture
def baseline() -> tuple[int, GateConfig]:
    turn = load_settings("configs/baseline/silence-threshold.yaml").turn
    assert turn.silence_threshold_sweep_ms is not None
    assert turn.gate is not None
    return turn.silence_threshold_sweep_ms[0], turn.gate


def test_b1_fits_the_seam(baseline: tuple[int, GateConfig]) -> None:
    """Nếu B1 không cắm vừa TurnDecider thì thiết kế sai, và biết bây giờ là rẻ nhất."""
    assert isinstance(SilenceThresholdDecider(*baseline), TurnDecider)


def test_decides_on_every_frame(baseline: tuple[int, GateConfig]) -> None:
    """SPEC R1 đòi ước lượng liên tục; một chuỗi HOLD liền mạch là kết quả đầy đủ."""
    decider = SilenceThresholdDecider(*baseline)
    given = frames("ssss..ssss")
    decisions = [decider.decide(frame) for frame in given]

    assert len(decisions) == len(given)
    for frame, decision in zip(given, decisions, strict=True):
        assert decision.decider == "silence_threshold"
        assert decision.frame_index == frame.index
        assert decision.at_s == frame.start_s
        assert decision.scores == {}
        assert decision.final_tone is None


def test_takes_exactly_when_silence_reaches_the_threshold() -> None:
    """200ms ngưỡng, khung 20ms: nhận lượt ở đúng khung im lặng thứ 10."""
    decider = SilenceThresholdDecider(200, GATE)
    outcomes = [decider.decide(frame).outcome for frame in frames("ss" + "." * 12)]

    assert outcomes[:11] == [TurnOutcome.HOLD] * 11
    assert outcomes[11] is TurnOutcome.TAKE


def test_speech_resets_the_silence_counter() -> None:
    """Ngập ngừng ngắn hơn ngưỡng không được tính là đã xong lượt."""
    decider = SilenceThresholdDecider(200, GATE)
    outcomes = [decider.decide(frame).outcome for frame in frames("ss.....ss.....")]
    assert TurnOutcome.TAKE not in outcomes


def test_silence_alone_is_not_a_finished_turn() -> None:
    """Chưa nghe thấy tiếng nào thì im lặng bao lâu cũng không phải bằng chứng."""
    decider = SilenceThresholdDecider(200, GATE)
    outcomes = [decider.decide(frame).outcome for frame in frames("." * 50)]
    assert set(outcomes) == {TurnOutcome.HOLD}


def test_take_holds_until_reset() -> None:
    decider = SilenceThresholdDecider(200, GATE)
    outcomes = [decider.decide(frame).outcome for frame in frames("ss" + "." * 20)]
    assert outcomes[-1] is TurnOutcome.TAKE
    assert outcomes[11:] == [TurnOutcome.TAKE] * len(outcomes[11:])


def test_reset_leaves_no_state_behind() -> None:
    """Trạng thái rò rỉ làm sai điểm mà không crash — loại lỗi đắt nhất của dự án."""
    decider = SilenceThresholdDecider(200, GATE)
    given = frames("ss" + "." * 12)

    first = [decider.decide(frame).outcome for frame in given]
    decider.reset()
    second = [decider.decide(frame).outcome for frame in given]

    assert first == second


def test_never_reports_a_backchannel() -> None:
    """B1 không phân biệt được tiếng đệm. Nó hỏng R4, và đó là số liệu cần đo."""
    decider = SilenceThresholdDecider(200, GATE)
    outcomes = {decider.decide(frame).outcome for frame in frames("s.s..ss...." * 5)}
    assert TurnOutcome.BACKCHANNEL not in outcomes


def test_a_wider_threshold_takes_later() -> None:
    """Ngưỡng đến từ dải quét trong configs/, không từ hằng số trong code."""
    given = frames("ss" + "." * 60)
    taken_at = []
    for threshold_ms in (200, 600, 1000):
        decider = SilenceThresholdDecider(threshold_ms, GATE)
        outcomes = [decider.decide(frame).outcome for frame in given]
        taken_at.append(outcomes.index(TurnOutcome.TAKE))
    assert taken_at == sorted(taken_at)
    assert len(set(taken_at)) == len(taken_at)


def test_every_swept_threshold_is_usable(baseline: tuple[int, GateConfig]) -> None:
    turn = load_settings("configs/baseline/silence-threshold.yaml").turn
    assert turn.silence_threshold_sweep_ms is not None
    for threshold_ms in turn.silence_threshold_sweep_ms:
        decider = SilenceThresholdDecider(threshold_ms, baseline[1])
        assert isinstance(decider, TurnDecider)


def test_a_non_positive_threshold_is_refused() -> None:
    with pytest.raises(ValueError, match="phải dương"):
        SilenceThresholdDecider(0, GATE)


def test_a_padded_tail_does_not_look_like_silence() -> None:
    """Đệm kéo RMS xuống 15 dB; nếu tính cả đệm thì đuôi phát ngôn thành im lặng giả.

    Khung ở đây chỉ có 10 mẫu thật ở -19 dBFS. Tính cả 310 mẫu đệm cho -34 dBFS, vẫn
    trên ngưỡng -45 nên chưa đủ để lộ lỗi; hạ ngưỡng xuống -25 dBFS làm phép thử sắc
    hơn: tính đúng thì đây là tiếng nói, tính cả đệm thì nó bị coi là im lặng.
    """
    decider = SilenceThresholdDecider(200, GATE.model_copy(update={"floor_dbfs": -25.0}))
    tail = FeatureFrame(
        index=0,
        start_s=0.0,
        duration_s=FRAME_S,
        samples=np.concatenate([np.full(10, 0.11, np.float32), np.zeros(310, np.float32)]),
        padded_samples=310,
    )

    decider.decide(tail)
    silence = frames("." * 20)
    outcomes = [decider.decide(frame).outcome for frame in silence]

    # Khung đuôi phải được tính là tiếng nói, nên bộ đếm im lặng khởi động từ sau nó.
    assert outcomes.index(TurnOutcome.TAKE) == 9
