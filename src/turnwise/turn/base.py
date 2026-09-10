"""Hợp đồng của tầng `turn`: một seam ngoài, một seam trong.

`TurnDecider` là seam **ngoài** (ADR-0003). Hệ đề xuất và ba baseline của SPEC R8 đều
là adapter ở đây, chọn bằng `turn.decider` trong `configs/`. Đó là điều làm cho câu
"cùng ASR, TTS và kịch bản" ở R8 đúng theo cấu trúc chứ không phải theo lời hứa.

`Scorer` là seam **trong**, chỉ adapter `fused` và test của chính tầng này dùng tới.
Không gì ngoài `turn/` được import nó.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from turnwise.types import FeatureFrame, TurnDecision


class Prediction(StrEnum):
    """Câu hỏi mà một scorer trả lời.

    Tồn tại vì hai hành vi ở SPEC không cùng một trục. R1 hỏi *khách nói xong chưa*;
    R4 hỏi *cái vừa nghe có phải chỉ là tiếng đệm không*. Một con số không mang được
    cả hai nghĩa, và nếu fusion gộp chung thì "sắp xong" sẽ triệt tiêu "đây là tiếng
    đệm" mà không ai thấy. Fusion gộp riêng từng nhóm, và mỗi nhóm có ngưỡng riêng
    trong `configs/`.
    """

    END_OF_TURN = "end_of_turn"
    """Khách đã kết thúc lượt tại khung này."""

    BACKCHANNEL = "backchannel"
    """Cái vừa nghe là tiếng đệm — "dạ", "vâng", "ừ" — không phải hành vi giành lượt."""


@runtime_checkable
class Scorer(Protocol):
    """Một nguồn tín hiệu, chấm điểm cho đúng một câu hỏi.

    Ba ràng buộc, và cả ba đều có lý do đắt giá:

    1. **Bỏ phiếu trắng là giá trị trả về, không phải điểm giữa.** Trả `None` khi
       không đủ cơ sở. Trả 0.5 để tỏ ra trung lập là nói dối fusion: nó không phân
       biệt được "tôi thấy 50/50" với "tôi không biết", và một scorer im lặng sẽ kéo
       kết quả về giữa ở mọi khung.

    2. **`reset()` phải xoá sạch trạng thái giữa hai lượt.** Trạng thái rò rỉ làm sai
       điểm mà không hề crash — loại lỗi tốn hàng giờ mà không để lại dấu vết. Mỗi
       scorer cần một test khẳng định: cùng đầu vào, cách nhau một `reset()`, cho ra
       cùng đầu ra.

    3. **Không hằng số trong code.** Mọi ngưỡng, cửa sổ, hệ số đều đến từ `configs/`.
       Một scorer không tắt được từ config thì không ablation được, mà SPEC §9.3 quy
       tắc 3 bắt buộc ablation.
    """

    name: str
    """Khoá của scorer này trong `TurnDecision.scores`. Phải ổn định: bảng ablation
    và mọi phân tích telemetry cũ đều tra theo tên này."""

    predicts: Prediction
    """Câu hỏi mà `score()` trả lời. Fusion gộp theo nhóm này."""

    def score(self, frame: FeatureFrame) -> float | None:
        """Xác suất trong [0, 1] rằng điều `predicts` mô tả là đúng ở khung này.

        Trả `None` để bỏ phiếu trắng.

        Được gọi mỗi khung trên thread tiêu thụ, **không bao giờ** trong callback
        audio. Chi phí mỗi lần gọi nằm trong ngân sách `latency.budget_per_frame_ms`,
        kiểm tra bằng `uv run pytest -m latency`.
        """
        ...

    def reset(self) -> None:
        """Xoá mọi trạng thái tích luỹ. Fusion gọi ở mỗi ranh giới lượt."""
        ...


@runtime_checkable
class TurnDecider(Protocol):
    """Một hệ hoàn chỉnh biến khung đặc trưng thành quyết định lượt nói.

    Bốn adapter cùng nằm sau interface này: hệ đề xuất và B1, B2, B3 của SPEC R8.
    Chúng có thể tốn kém lúc khởi tạo — B2 và B3 nạp mô hình ONNX — nhưng `decide()`
    phải vừa ngân sách mỗi khung. Nạp mô hình trong `decide()` là hỏng phép đo độ trễ.

    Decider không gọi telemetry. Nó trả về `TurnDecision`, và phần nối dây ghi lại ở
    đúng một chỗ (ADR-0003).
    """

    name: str
    """Tên ghi vào `TurnDecision.decider`, để mỗi dòng telemetry tự nói nó thuộc lần
    chạy nào."""

    def decide(self, frame: FeatureFrame) -> TurnDecision:
        """Ước lượng lại trạng thái lượt nói sau khi có thêm một khung.

        Trả về ở **mọi** khung, không chỉ khi có gì đổi. SPEC R1 yêu cầu ước lượng
        liên tục chứ không phải chờ hết một ngưỡng, nên một chuỗi `HOLD` liền mạch là
        kết quả hợp lệ và đầy đủ thông tin — đó chính là bằng chứng hệ thống đang
        theo dõi, không phải đang đếm ngược.

        `TurnOutcome.HOLD` là mặc định đúng khi chưa đủ cơ sở: nhận lượt sai thì cắt
        lời khách, còn giữ im thêm một khung thì chỉ tốn 20ms.
        """
        ...

    def reset(self) -> None:
        """Trả về trạng thái đầu lượt, gồm cả `reset()` của mọi scorer bên trong."""
        ...
