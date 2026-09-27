"""B1 — baseline ngưỡng im lặng cố định của SPEC R8.

Đây là cách tổng đài hiện hành làm, và là thứ `SPEC.md` §1 lập luận rằng không thể
đúng: *đang nghĩ* và *đã nói xong* giống hệt nhau trên trục biên độ, nên không giá
trị ngưỡng nào tránh được cả ba lỗi cắt lời, chờ quá lâu và không cho ngắt. Baseline
này tồn tại để **chứng minh** mệnh đề đó bằng một đường cong, chứ không phải để thua
cho có.

Vì vậy nó cố tình đơn giản đúng bằng cách cũ:

- Cổng **năng lượng** (`turn/gate.py`, dùng chung cho cả bốn hệ), không phải VAD học máy.
  Một baseline chạy VAD mạng nơ-ron sẽ không còn là baseline của cách cũ nữa, và phép
  so sánh ở R8 mất nghĩa.
- **Không bao giờ** trả `BACKCHANNEL`. B1 không có cách nào phân biệt "dạ" tiếng đệm
  với "Dạ." trọn lượt. Đó là chỗ nó hỏng SPEC R4, và là kết quả cần đo — không phải
  thiếu sót cần vá.
- Không chấm điểm, nên `scores` rỗng; không biết thanh điệu, nên `final_tone` là
  `None`. Bảng ablation không có gì để quy trách nhiệm ở đây, và đó là điều đúng.

Ngưỡng thời gian đến từ `silence_threshold_sweep_ms` trong
`configs/baseline/silence-threshold.yaml`: mỗi giá trị trong dải là **một lần chạy
riêng**, cho một điểm trên đường cong đánh đổi (SPEC §9.3 quy tắc 2). Adapter này giữ
đúng một giá trị; người quét dải là `evaluation/run_baseline.py`.
"""

from __future__ import annotations

import logging

from turnwise.config import GateConfig
from turnwise.turn.gate import is_speech, rms_dbfs
from turnwise.types import FeatureFrame, TurnDecision, TurnOutcome

logger = logging.getLogger(__name__)

__all__ = ["SilenceThresholdDecider", "rms_dbfs"]


class SilenceThresholdDecider:
    """Nhận lượt sau khi im lặng liên tục đủ lâu, kể từ lần cuối nghe thấy tiếng."""

    name = "silence_threshold"

    _silence_ms: int
    _heard_speech: bool
    _taken: bool

    def __init__(self, silence_threshold_ms: int, gate: GateConfig) -> None:
        if silence_threshold_ms <= 0:
            raise ValueError(f"silence_threshold_ms phải dương, nhận {silence_threshold_ms}")
        self._threshold_ms = silence_threshold_ms
        self._gate = gate
        self.reset()

    def decide(self, frame: FeatureFrame) -> TurnDecision:
        """Cộng dồn im lặng, và nhận lượt khi nó chạm ngưỡng.

        Bộ đếm cộng bằng **mili giây nguyên**, không phải giây thực: cộng 0.02 mười
        lần cho 0.19999999999999998, và so sánh với 0.2 sẽ trượt đúng một khung. Một
        khung ở đây là 20ms, ngay trên trục mà cả dự án đang đo.

        Chưa nghe thấy tiếng nào thì im lặng không đủ để nhận lượt: im lặng không phải
        bằng chứng của một lượt đã xong (`.claude/rules/turn.md`).
        """
        if not self._taken:
            if is_speech(frame, self._gate):
                self._heard_speech = True
                self._silence_ms = 0
            else:
                self._silence_ms += round(frame.duration_s * 1000)
                if self._heard_speech and self._silence_ms >= self._threshold_ms:
                    self._taken = True
                    logger.debug(
                        "take at frame %d (%.3fs), silence %dms",
                        frame.index,
                        frame.start_s,
                        self._silence_ms,
                    )

        return TurnDecision(
            outcome=TurnOutcome.TAKE if self._taken else TurnOutcome.HOLD,
            decider=self.name,
            frame_index=frame.index,
            at_s=frame.start_s,
            scores={},
            final_tone=None,
        )

    def reset(self) -> None:
        """Về trạng thái đầu lượt. Trạng thái rò rỉ ở đây làm sai mọi điểm trên đường cong."""
        self._silence_ms = 0
        self._heard_speech = False
        self._taken = False
