"""CLI phải phân giải được tham số và không chết vì bảng mã console."""

import pytest

from turnwise.agent import build_parser, main


def test_help_does_not_crash() -> None:
    """`turnwise --help` trên console cp1258 từng ném UnicodeEncodeError."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_dev_runs_the_proposed_system_unless_told_otherwise() -> None:
    """Không gọi `main(["dev"])` ở đây: nó nạp ASR, TTS và mở micro thật."""
    args = build_parser().parse_args(["dev"])
    assert args.config == "configs/proposed/draft.yaml"
    other = build_parser().parse_args(["dev", "--config", "configs/baseline/acoustic-onnx.yaml"])
    assert other.config.endswith("acoustic-onnx.yaml")


def test_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["nope"])
