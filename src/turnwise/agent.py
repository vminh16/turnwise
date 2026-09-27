"""Điểm vào duy nhất của Turnwise.

File này cố tình mỏng: nó phân giải tham số dòng lệnh rồi giao việc cho các tầng.
Mọi logic thuộc về `audio/`, `turn/`, `dialog/`, `transport/` — xem `AGENTS.md`.

Chuỗi hướng tới người dùng ở đây viết bằng tiếng Anh, không phải tiếng Việt: xem
`force_utf8_stdio` để biết lý do.
"""

from __future__ import annotations

import argparse
import io
import logging
import sys

logger = logging.getLogger(__name__)


def force_utf8_stdio() -> None:
    """Bắt stdout/stderr nói UTF-8, thay chữ không mã hoá được thay vì ném lỗi.

    Console Windows mặc định dùng bảng mã một byte — trên máy Việt Nam thường là
    cp1258 — và không mã hoá nổi phần lớn chữ tiếng Việt có dấu. Một dòng log chứa
    "dạ" sẽ ném UnicodeEncodeError và giết tiến trình. Với một agent xử lý hội thoại
    tiếng Việt, đó không phải trường hợp hiếm mà là đường chạy bình thường.

    `errors="replace"` khiến ký tự không in được biến thành dấu hỏi thay vì làm sập
    agent. Console hiển thị xấu vẫn tốt hơn agent chết giữa cuộc gọi.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="turnwise",
        description="Real-time turn-taking and barge-in for Vietnamese voice agents.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    dev = subcommands.add_parser(
        "dev", help="Run a call on this machine's microphone and speaker (wired headset advised)."
    )
    dev.add_argument(
        "--config",
        default="configs/proposed/draft.yaml",
        help="Overlay that picks the decider (default: the proposed system).",
    )
    return parser


def run_dev(config: str) -> int:
    """Một cuộc gọi trên micro và loa của máy này. Mọi phần nặng được nạp trước khi mở luồng."""
    from datetime import datetime

    from turnwise.audio.source import LiveAudio
    from turnwise.config import load_settings
    from turnwise.dialog.backend_stub import NetCoBackend
    from turnwise.dialog.machine import Dialog
    from turnwise.telemetry.collector import TelemetryCollector
    from turnwise.telemetry.dashboard import Dashboard
    from turnwise.transport.speech import VieneuTts, load_asr
    from turnwise.transport.wiring import Call, CallStats
    from turnwise.turn.deciders import build
    from turnwise.types import TurnDecision

    settings = load_settings(config)
    logger.info("loading decider %s, ASR and TTS", settings.turn.decider)
    decider = build(settings.turn)
    asr = load_asr(settings.speech)
    tts = VieneuTts(settings.speech, settings.audio.sample_rate_hz)
    audio = LiveAudio(settings)
    max_turn_frames = settings.speech.asr_max_turn_s * 1000 // settings.audio.feature_frame_ms
    run_name = datetime.now().strftime("%Y%m%dT%H%M%S")

    with (
        TelemetryCollector(settings.telemetry, decider.name, "live", run_name) as telemetry,
        Dashboard(settings.telemetry.dashboard_refresh_frames) as dashboard,
    ):

        def show(stats: CallStats, decision: TurnDecision) -> None:
            last = stats.transcripts[-1] if stats.transcripts else ("", "")
            dashboard.update(
                {
                    "frames": stats.frames,
                    "turns taken": stats.takes,
                    "barge-ins": stats.barge_ins,
                    "backchannels": stats.backchannels,
                    "last reply ms": round(stats.reply_ms[-1]) if stats.reply_ms else "-",
                    "buffer overruns": audio.overruns,
                    "caller said": last[0],
                    "bot said": last[1],
                },
                decision,
            )

        audio.start()
        try:
            call = Call(
                audio.frames(),
                decider,
                Dialog(NetCoBackend(), settings.dialog),
                asr,
                tts,
                audio,
                telemetry.record,
                max_turn_frames,
                on_frame=show,
            )
            stats = call.run()
        except KeyboardInterrupt:
            logger.info("call stopped by the operator")
            return 0
        finally:
            audio.close()
    logger.info(
        "call over: %d turns taken, %d barge-ins, telemetry in %s",
        stats.takes,
        stats.barge_ins,
        telemetry.path,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    if args.command == "dev":
        return run_dev(args.config)
    # argparse đã chặn mọi giá trị khác; nhánh này chỉ để mypy thấy hàm luôn trả về int.
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
