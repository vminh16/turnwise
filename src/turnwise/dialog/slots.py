"""Rút thông tin từ lời khách đã chép thành chữ. Luật cố định, không mô hình (SPEC §11).

Mỗi hàm trả `None` khi không chắc: SPEC §4.2 cấm đoán trường còn thiếu, và máy trạng thái sẽ hỏi
lại. Chữ vào có thể là chữ số ASR đã viết ("824-615-390") hoặc chữ đọc ("tám hai bốn"), nên cả
hai đều phải hiểu.
"""

from __future__ import annotations

import re
import unicodedata

DIGIT_WORDS = {
    "không": "0", "linh": "0", "lẻ": "0",
    "một": "1", "mốt": "1",
    "hai": "2",
    "ba": "3",
    "bốn": "4", "tư": "4",
    "năm": "5", "lăm": "5",
    "sáu": "6",
    "bảy": "7", "bẩy": "7",
    "tám": "8",
    "chín": "9",
}  # fmt: skip

SUBSCRIBER_DIGITS = 9  # định dạng số thuê bao của NetCo trong mọi kịch bản đóng vai
APPOINTMENT_DIGITS = 6  # mã lịch hẹn: chữ L và sáu chữ số, ví dụ "L 47 20 93"

YES = ("đúng", "vâng", "dạ", "ừ", "được", "đồng ý", "có", "ok", "chuẩn", "phải")
NO = ("không", "sai", "chưa", "thôi", "khỏi", "nhầm")
AGENT = ("nhân viên", "tổng đài viên", "điện thoại viên", "người thật", "gặp người", "tư vấn viên")

INTENTS = {
    "N1": ("mất mạng", "mạng", "internet", "wifi", "không vào được", "chập chờn", "sự cố"),
    "N2": ("cước", "hoá đơn", "hóa đơn", "tiền", "thanh toán"),
    "N3": ("lịch hẹn", "đổi lịch", "dời lịch", "kỹ thuật viên", "hẹn lại"),
    "N4": ("gói", "nâng", "huỷ", "hủy", "đăng ký", "đổi gói"),
}
"""Luồng nào được nhắc tới. Thứ tự quan trọng: "đổi lịch hẹn kỹ thuật viên" là N3, không N1."""

DAYS = {
    "thứ hai": "thứ Hai", "thứ ba": "thứ Ba", "thứ tư": "thứ Tư", "thứ năm": "thứ Năm",
    "thứ sáu": "thứ Sáu", "thứ bảy": "thứ Bảy", "chủ nhật": "Chủ nhật",
    "ngày mai": "ngày mai", "mai": "ngày mai", "hôm nay": "hôm nay", "ngày kia": "ngày kia",
}  # fmt: skip
PERIODS = {"sáng": "buổi sáng", "trưa": "buổi trưa", "chiều": "buổi chiều", "tối": "buổi tối"}


def normalise(text: str) -> str:
    """Chữ thường, dạng Unicode dựng sẵn, bỏ dấu câu. "Huỷ" và "Hủy" thành cùng một chuỗi."""
    text = unicodedata.normalize("NFC", text.lower()).replace("hủy", "huỷ")
    return re.sub(r"[^\w\s]", " ", text)


def _has(text: str, phrases: tuple[str, ...]) -> bool:
    words = f" {normalise(text)} "
    return any(f" {p} " in words for p in phrases)


def digits(text: str) -> str:
    """Mọi chữ số trong câu, theo thứ tự, dù viết bằng số hay bằng chữ."""
    out = []
    for word in normalise(text).split():
        if word.isdigit():
            out.append(word)
        elif word in DIGIT_WORDS:
            out.append(DIGIT_WORDS[word])
    return "".join(out)


def subscriber_id(text: str) -> str | None:
    found = digits(text)
    return found if len(found) == SUBSCRIBER_DIGITS else None


def appointment_code(text: str) -> str | None:
    """Chữ L đọc là "L", "lờ" hoặc "e lờ", rồi sáu chữ số."""
    norm = normalise(text)
    if not re.search(r"\b(l|lờ|e lờ|en lờ)\b", norm):
        return None
    found = digits(re.sub(r"\b(e lờ|en lờ|lờ)\b", " ", norm))
    return f"L{found}" if len(found) == APPOINTMENT_DIGITS else None


def yes_no(text: str) -> bool | None:
    """Có hay không. Không nghe được gì rõ thì `None`: im lặng không phải đồng ý.

    Phủ định thắng: "dạ không", "không phải", "không đúng" đều là không, dù có chữ của phía "có".
    """
    if _has(text, NO):
        return False
    if _has(text, YES):
        return True
    return None


def wants_agent(text: str) -> bool:
    return _has(text, AGENT)


def intent(text: str) -> str | None:
    for flow in ("N3", "N2", "N4", "N1"):
        if _has(text, INTENTS[flow]):
            return flow
    return None


def day(text: str) -> str | None:
    norm = f" {normalise(text)} "
    for key in sorted(DAYS, key=len, reverse=True):
        if f" {key} " in norm:
            return DAYS[key]
    return None


def period(text: str) -> str | None:
    norm = f" {normalise(text)} "
    for key, value in PERIODS.items():
        if f" {key} " in norm:
            return value
    return None


def month(text: str) -> int | None:
    match = re.search(r"tháng\s+(\w+)", normalise(text))
    if not match:
        return None
    word = match.group(1)
    value = int(word) if word.isdigit() else _month_word(word)
    return value if value and 1 <= value <= 12 else None


def _month_word(word: str) -> int | None:
    names = {"giêng": 1, "chạp": 12, "mười": 10, "tư": 4}
    if word in names:
        return names[word]
    digit = DIGIT_WORDS.get(word)
    return int(digit) if digit else None
