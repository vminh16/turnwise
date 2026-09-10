"""CLI phải phân giải được tham số và không chết vì bảng mã console."""

import pytest

from turnwise.agent import build_parser, main


def test_help_does_not_crash() -> None:
    """`turnwise --help` trên console cp1258 từng ném UnicodeEncodeError."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_dev_reports_not_wired_instead_of_importerror() -> None:
    assert main(["dev"]) == 1


def test_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["nope"])
