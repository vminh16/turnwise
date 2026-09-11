"""Quét B1 qua cả dải ngưỡng của SPEC R8, sinh đường cong đánh đổi.

    uv run python evaluation/run_baseline.py

Mỗi giá trị trong `turn.silence_threshold_sweep_ms` là **một lần chạy độc lập** trên
cả năm kịch bản, cho một điểm trên đường cong. Đó là quy tắc 2 của `SPEC.md` §9.3:
baseline quét cả dải, không chọn một điểm. Báo cáo một ngưỡng đã tinh chỉnh mời gọi
câu hỏi "sao không chỉnh tốt hơn?"; quét cả dải chứng minh không ngưỡng nào thắng —
luận điểm trung tâm ở §1.

Kết quả ra hai chỗ:

- `reports/baseline/silence-threshold.csv` — đường cong, cả hai trục trong một file.
- `reports/telemetry/silence_threshold/<ngưỡng>ms/<kịch bản>.jsonl` — mọi quyết định
  của từng khung, để một điểm bất thường truy ngược được về đúng khung sinh ra nó.

Độ trễ ở đây tính trên file. `SPEC.md` §9.3 quy tắc 4 đòi số đo trên hệ chạy trực
tiếp, nên đây **chưa phải** số báo cáo được — xem đầu `metrics.py`.
"""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

# `uv run python evaluation/run_baseline.py` (lệnh ghi trong AGENTS.md) đặt thư mục
# evaluation/ lên sys.path chứ không phải gốc repo, nên `import evaluation.*` hỏng.
# Thêm gốc repo vào trước khi import phần còn lại; chạy bằng `-m` thì dòng này vô hại.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.metrics import CurvePoint, score, summarise, write_curve
from evaluation.scenario import load_all, replay
from turnwise.config import load_settings
from turnwise.telemetry.collector import TelemetryCollector
from turnwise.turn.deciders.silence_threshold import SilenceThresholdDecider

logger = logging.getLogger(__name__)

BASELINE_CONFIG = "configs/baseline/silence-threshold.yaml"
CURVE_PATH = Path("reports/baseline/silence-threshold.csv")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")

    settings = load_settings(BASELINE_CONFIG)
    sweep = settings.turn.silence_threshold_sweep_ms
    floor_dbfs = settings.turn.silence_floor_dbfs
    if sweep is None or floor_dbfs is None:
        raise SystemExit(f"{BASELINE_CONFIG} has no sweep or no energy floor")

    scenarios = load_all()
    logger.info("sweeping %d thresholds over %d scenarios", len(sweep), len(scenarios))

    points: list[CurvePoint] = []
    with tempfile.TemporaryDirectory(prefix="turnwise-baseline-") as workspace:
        # Audio tổng hợp là dữ liệu trung gian: sinh lại được từ kịch bản, nên nó
        # sống trong thư mục tạm chứ không nằm lại trong reports/.
        directory = Path(workspace)
        for threshold_ms in sweep:
            decider = SilenceThresholdDecider(threshold_ms, floor_dbfs)
            scores = []
            for scenario in scenarios:
                with TelemetryCollector(
                    settings.telemetry,
                    decider.name,
                    f"{threshold_ms}ms",
                    scenario.name,
                ) as collector:
                    decisions = replay(
                        scenario, decider, settings.audio, directory, collector=collector
                    )
                scores.append(score(decisions, scenario))

            point = summarise(threshold_ms, scores)
            points.append(point)
            # Chuỗi hướng tới người dùng viết tiếng Anh: console Windows tiếng Việt
            # mặc định cp1258 và không in nổi chữ có dấu (AGENTS.md).
            logger.info(
                "%4dms: interruptions %.0f%%, median reply %s ms, "
                "backchannel taken as turn %s, no reply in %d scenarios",
                point.threshold_ms,
                point.interruption_rate * 100,
                point.median_response_latency_ms,
                point.backchannel_error_rate,
                point.no_response,
            )

    write_curve(points, CURVE_PATH)
    logger.info("curve of %d points -> %s", len(points), CURVE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
