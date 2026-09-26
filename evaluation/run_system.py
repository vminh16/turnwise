"""Chạy một decider trên bộ dữ liệu vàng và ghi phán quyết cho từng đoạn nói đã gán nhãn.

    uv run python -m evaluation.run_system configs/baseline/silence-threshold.yaml
    uv run python -m evaluation.run_system configs/baseline/acoustic-onnx.yaml --during-bot
    uv run python -m evaluation.run_system configs/proposed/draft.yaml --ablation

Decider chọn bằng cấu hình (`.claude/rules/evaluation.md`): thư mục này không có đường quyết định
nào của riêng nó. Cấu hình B1 có dải quét thì mỗi giá trị là một lần chạy, một điểm trên đường
cong (SPEC §9.3 quy tắc 2).

Mặc định chạy tập `dev`. Holdout chỉ mở bằng `--final-report`, đúng một lần, khi làm báo cáo cuối.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from evaluation import dataset, golden
from turnwise.config import TurnConfig, load_settings
from turnwise.turn.deciders import build

REPORTS = Path(__file__).resolve().parent.parent / "reports" / "golden"


def runs(turn: TurnConfig, ablation: bool = False) -> list[tuple[str, TurnConfig]]:
    """Một cấu hình thành các lần chạy.

    B1 quét dải. Hệ đề xuất với `ablation` chạy thêm một lần cho mỗi scorer bị tắt. Mọi decider
    khác chạy một lần.
    """
    if turn.decider == "silence_threshold" and turn.silence_threshold_sweep_ms:
        return [
            (f"{turn.decider}-{ms}ms", turn.model_copy(update={"silence_threshold_ms": ms}))
            for ms in turn.silence_threshold_sweep_ms
        ]
    out: list[tuple[str, TurnConfig]] = [(turn.decider, turn)]
    if ablation and turn.decider == "fused" and len(turn.scorers) > 1:
        out += [
            (
                f"fused-without-{name}",
                turn.model_copy(update={"scorers": [s for s in turn.scorers if s != name]}),
            )
            for name in turn.scorers
        ]
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evaluation.run_system")
    parser.add_argument("config", type=Path)
    parser.add_argument("--during-bot", action="store_true", help="also score barge-in")
    parser.add_argument("--final-report", action="store_true", help="score the locked split")
    parser.add_argument("--ablation", action="store_true", help="also run with each scorer off")
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    split = dataset.LOCKED if args.final_report else dataset.DEV
    recordings = dataset.recordings(split)
    for name, turn in runs(settings.turn, args.ablation):
        verdicts = golden.run(build(turn), recordings, settings.audio, args.during_bot)
        path = golden.write(verdicts, REPORTS / split / f"{name}.csv")
        report = {"run": name, "split": split, "csv": path.as_posix(), **golden.summary(verdicts)}
        sys.stdout.write(json.dumps(report, ensure_ascii=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
