"""Hộp đen của một lần chạy: mỗi `TurnDecision` thành đúng một dòng JSONL.

Tầng này **chỉ nhận**. Nó không bao giờ nói ngược vào đường ống — `SPEC.md` §8 gọi
đó là "read-only, never feeds back", và lý do rất thực dụng: nếu telemetry tác động
ngược được thì thứ đang đo thay đổi theo chính phép đo.

Nó cũng **không tính gì cả**. Không tỉ lệ, không trung bình, không làm trơn. Nó chép
lại. Mọi phép tính là việc của `evaluation/`, đọc từ file — nên tính sai thì tính lại,
không phải chạy lại cuộc gọi.

Người ghi là phần nối dây, không phải tầng `turn`. Decider trả về một giá trị rồi
thôi (ADR-0003). Cách ngược lại — mỗi scorer tự gọi collector — đã được cân nhắc và
loại: *"một scorer quên gọi thì bảng ablation thiếu một cột mà không có gì báo lỗi."*

GHI CHÚ, chưa xử lý: ADR-0003 viết *"đúng một chỗ — phần nối dây ở `transport/` — ghi
giá trị đó xuống `telemetry.collector`"*. Giai đoạn 0 chưa có `transport/`, nên người
gọi ở đây là bộ chạy kịch bản và `evaluation/run_baseline.py`. Tinh thần của ADR vẫn
giữ — một chỗ ghi cho mỗi đường chạy, không phải mỗi scorer tự ghi — nhưng câu chữ
"ở `transport/`" sẽ cần sửa khi đường chạy sống xuất hiện ở Giai đoạn 4.
"""

from __future__ import annotations

import json
import logging
from types import TracebackType
from typing import IO, Any, Self

from turnwise.config import TelemetryConfig
from turnwise.types import TurnDecision

logger = logging.getLogger(__name__)

SUFFIX = ".jsonl"


class TelemetryCollector:
    """Ghi quyết định của một lần chạy xuống `<telemetry.dir>/<phần tên>.jsonl`.

    Tên chia theo thư mục phân cấp để một dải quét tìm lại được bằng mắt:

        TelemetryCollector(config, "silence_threshold", "200ms")
        -> reports/telemetry/silence_threshold/200ms.jsonl

    Collector cố tình **không tự đặt tên**: nó không biết lần chạy này dùng ngưỡng
    nào, mà đúng cái tên mới là thứ phân biệt 11 file của một dải quét.
    """

    def __init__(self, config: TelemetryConfig, *name: str) -> None:
        if not name:
            raise ValueError("cần ít nhất một phần tên cho file telemetry")
        for part in name:
            if not part or "/" in part or "\\" in part or part in {".", ".."}:
                raise ValueError(f"phần tên không hợp lệ: {part!r}")

        self.enabled = config.enabled
        self.path = config.dir.joinpath(*name).with_suffix(SUFFIX)
        self._file: IO[str] | None = None

        if not self.enabled:
            logger.debug("telemetry tắt; không mở %s", self.path)
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        # buffering=1: xả từng dòng. 50 dòng mỗi giây là không đáng kể, còn đệm lại
        # sẽ mất đúng phần đuôi — mà đuôi là chỗ có sự cố cần xem.
        self._file = self.path.open("w", encoding="utf-8", buffering=1, newline="\n")

    def record(self, decision: TurnDecision) -> None:
        """Chép một quyết định thành một dòng.

        Dict dựng tường minh chứ không qua `dataclasses.asdict`: khoá và thứ tự cố
        định, nên `types.py` đổi thì file cũ vẫn đọc được bằng cùng một cách. Mốc thời
        gian là `at_s` của chính luồng audio, không phải giờ treo tường — giờ treo
        tường làm hai lần chạy lại cùng một kịch bản khác nhau, mà tính tất định đó
        chính là thứ làm bộ kịch bản so sánh được.
        """
        if self._file is None:
            return

        row: dict[str, Any] = {
            "outcome": decision.outcome,
            "decider": decision.decider,
            "frame_index": decision.frame_index,
            "at_s": decision.at_s,
            "scores": dict(decision.scores),
            "final_tone": decision.final_tone,
        }
        # ensure_ascii=False: payload telemetry được phép chứa tiếng Việt (AGENTS.md).
        self._file.write(json.dumps(row, ensure_ascii=False) + "\n")

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
            logger.debug("đã đóng %s", self.path)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
