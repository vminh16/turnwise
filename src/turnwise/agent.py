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
    subcommands.add_parser("dev", help="Run the agent locally; WebRTC client at localhost:8080.")
    return parser


def run_dev() -> int:
    # Đường ống chưa được nối. Báo rõ còn thiếu gì, để lệnh ghi trong README luôn
    # giải thích được trạng thái thật của repo thay vì văng lỗi import ở chỗ khác.
    logger.error(
        "Not wired up yet. Still missing: src/turnwise/config.py, "
        "src/turnwise/audio/source.py, and an adapter in src/turnwise/turn/deciders/."
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    if args.command == "dev":
        return run_dev()
    # argparse đã chặn mọi giá trị khác; nhánh này chỉ để mypy thấy hàm luôn trả về int.
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
