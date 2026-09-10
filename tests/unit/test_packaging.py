"""Kiểm tra gói cài đặt được và bố cục src/ đúng — bắt lỗi đóng gói trước khi bắt lỗi logic."""

import importlib


def test_package_imports() -> None:
    importlib.import_module("turnwise")


def test_package_is_installed_not_shadowed_by_cwd() -> None:
    """src/ layout tồn tại để test chạy trên code đã cài, không phải thư mục làm việc."""
    turnwise = importlib.import_module("turnwise")
    assert turnwise.__file__ is not None
    assert "src" in turnwise.__file__.replace("\\", "/").split("/")
