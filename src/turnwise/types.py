"""Kiểu dùng chung giữa các tầng.

Đây là từ vựng mà `audio`, `turn`, `dialog` và `telemetry` cùng nói. Nó cố tình
không chứa hành vi: chỉ có kiểu dữ liệu và bất biến. Tầng nào cần logic thì logic
nằm ở tầng đó.

Hai quyết định định hình cả file này, ghi ở ADR-0003:

1. **Bỏ phiếu trắng là giá trị hạng nhất.** Một scorer không có ý kiến trả về
   `None`, không phải 0.5. Fusion phải phân biệt được "tôi thấy 50/50" với "tôi
   không đủ cơ sở để nói".
2. **Quyết định là giá trị trả về, không phải hiệu ứng lề.** `TurnDecision` mang
   theo mọi thứ cần để tái dựng và phân tích, nên tầng `turn` không cần biết
   `telemetry` tồn tại.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray


class TurnOutcome(StrEnum):
    """Ba trạng thái lượt nói ở SPEC §8."""

    HOLD = "hold"
    """Khách chưa xong. Bot giữ im — kể cả khi đang có khoảng lặng."""

    TAKE = "take"
    """Khách đã xong. Bot được phép nói."""

    BACKCHANNEL = "backchannel"
    """Khách chỉ chêm tiếng đệm. Bot nói tiếp, không dừng, không nhường lượt."""


class Tone(StrEnum):
    """Sáu thanh điệu tiếng Việt, cộng một giá trị cho trường hợp không xác định được.

    Đây là biến độc lập của kết quả khoa học chính ở SPEC §9.1: chênh lệch tỉ lệ lỗi
    giữa các thanh điệu của âm tiết cuối. Không ghi được thanh điệu thì không có kết
    quả đó, nên nó là một trường của `TurnDecision` chứ không phải thứ tính lại sau.

    Định danh viết tiếng Anh theo AGENTS.md; tên tiếng Việt nằm ở chú thích.
    """

    LEVEL = "level"
    """ngang — không dấu."""

    FALLING = "falling"
    """huyền."""

    RISING = "rising"
    """sắc."""

    DIPPING = "dipping"
    """hỏi."""

    BROKEN = "broken"
    """ngã — có đứt thanh môn ở giọng Bắc."""

    DROP = "drop"
    """nặng."""

    UNKNOWN = "unknown"
    """Không xác định được: âm tiết vô thanh, quá ồn, hoặc ASR chưa trả kịp.

    Khác với việc không có âm tiết nào — trường hợp đó `final_tone` để `None`.
    """


@dataclass(frozen=True, slots=True)
class FeatureFrame:
    """Một khung đặc trưng do tầng `audio` phát ra, đã khử tiếng của chính bot.

    Bất biến mà tầng `audio` phải giữ:

    - Khung phát ra đều đặn, cách nhau đúng `duration_s`. Khung bị mất do overrun
      được đếm và báo qua telemetry, không được lặng lẽ bỏ qua — một khoảng trống
      không báo trông giống hệt một khoảng im lặng, và đó chính là tín hiệu mà cả
      hệ thống đang đo.
    - `samples` là mono, float32, đã qua khử vọng. Scorer không bao giờ nhìn thấy
      tiếng bot; SPEC R5 phụ thuộc vào điều đó.
    - `samples` chỉ được đọc. Nó có thể trỏ vào bộ nhớ dùng lại của ring buffer, nên
      ai muốn giữ lại phải tự sao chép.
    """

    index: int
    """Số thứ tự khung từ lúc mở luồng. Liên tục; số nhảy nghĩa là có khung bị mất."""

    start_s: float
    """Mốc thời gian bắt đầu khung, tính từ lúc mở luồng."""

    duration_s: float
    """Độ dài khung. Lấy từ `audio.feature_frame_ms` trong `configs/`."""

    samples: NDArray[np.float32]
    """Mẫu mono đã khử vọng."""

    f0_hz: float | None = None
    """Tần số cơ bản, hoặc `None` khi khung vô thanh hay không ước lượng được.

    Chưa chuẩn hoá theo người nói. Chuẩn hoá là việc của scorer, và bắt buộc phải
    làm trước khi gộp nhiều người nói — gộp F0 thô thì mô hình học ra giới tính chứ
    không học tín hiệu cần học (AGENTS.md, `.claude/rules/turn.md`).
    """


@dataclass(frozen=True, slots=True)
class TurnDecision:
    """Kết luận của một decider cho một khung, kèm đủ dấu vết để phân tích lại.

    Đây là thứ duy nhất tầng `turn` trả ra ngoài. Phần nối dây ghi nó xuống
    `telemetry` ở đúng một chỗ; bản thân tầng `turn` không gọi telemetry.

    Có `scores` ngay trong quyết định là điều kiện cần để dựng bảng ablation ở SPEC
    §9.3 quy tắc 3: không có điểm của từng scorer thì một quyết định sai không quy
    trách nhiệm được cho thành phần nào.
    """

    outcome: TurnOutcome

    decider: str
    """Tên adapter đã sinh ra quyết định này — hệ đề xuất, hay B1/B2/B3 của SPEC R8.

    Ghi lại để mọi dòng telemetry tự nói nó thuộc lần chạy nào, thay vì phải suy ra
    từ thư mục chứa nó.
    """

    frame_index: int
    at_s: float
    """Khung nào và thời điểm nào. Khớp với `FeatureFrame.index` và `.start_s`."""

    scores: Mapping[str, float | None] = field(default_factory=dict)
    """Điểm theo tên scorer. `None` nghĩa là scorer đó bỏ phiếu trắng ở khung này.

    Bỏ phiếu trắng khác hẳn điểm thấp, và cũng khác hẳn việc scorer không chạy: một
    scorer đang tắt để ablation thì không xuất hiện trong ánh xạ này.
    """

    final_tone: Tone | None = None
    """Thanh điệu của âm tiết cuối vừa nghe, hoặc `None` khi chưa có âm tiết nào.

    `Tone.UNKNOWN` nghĩa là có âm tiết nhưng không xác định được thanh điệu.
    """
