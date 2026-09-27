"""Lời thoại của bot, và cách viết số thành chữ trước khi đưa cho TTS.

Mọi câu đều viết sẵn (SPEC §11: không sinh câu tự do bằng LLM). R12 đòi bot không vô cảm và
không lặp máy móc, nên câu hay gặp có vài biến thể, chọn theo thứ tự cố định để một cuộc gọi
tái dựng được.

Số viết thành chữ ở đây, không để TTS tự đọc: VieNeu đọc "25/9" thành "hai lăm chín" chứ không
thành ngày (`docs/progress.md` §6.8). Tầng `turn` vì vậy không bao giờ thấy chữ số trong lời bot.
"""

from __future__ import annotations

UNITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

GREETING = "Tổng đài NetCo xin nghe. Quý khách cần hỗ trợ gì ạ?"
ASK_INTENT = "Dạ, quý khách cần báo sự cố mạng, tra cước, đổi lịch hẹn hay đăng ký gói ạ?"
ASK_SUBSCRIBER = "Quý khách cho em xin số thuê bao ạ."
ASK_SUBSCRIBER_AGAIN = "Dạ em chưa nghe rõ, quý khách đọc lại giúp em số thuê bao chín chữ số ạ."
UNKNOWN_SUBSCRIBER = "Dạ em không tìm thấy số thuê bao này. Quý khách đọc lại giúp em ạ."
CONFIRM_SUBSCRIBER = "Em xin nhắc lại số thuê bao: {number}. Đúng không ạ?"
ASK_DESCRIPTION = "Dạ, quý khách mô tả giúp em tình trạng mạng hiện giờ ạ."
ASK_DAY = "Quý khách muốn kỹ thuật viên qua vào ngày nào ạ?"
ASK_PERIOD = "Dạ, buổi sáng hay buổi chiều ạ?"
TICKET_DONE = (
    "Em đã tạo phiếu sự cố {ticket}, kỹ thuật viên sẽ qua {day}, {period}, "
    "và gọi cho quý khách trước ba mươi phút."
)
ASK_MONTH = "Quý khách muốn tra cước tháng nào ạ?"
BILL = "Cước tháng {month} của quý khách gồm: {items}. Tổng cộng {total}."
ASK_CODE = "Quý khách cho em xin mã lịch hẹn trong tin nhắn ạ."
ASK_CODE_AGAIN = "Dạ em chưa nghe rõ mã lịch hẹn. Mã bắt đầu bằng chữ L và sáu chữ số ạ."
CONFIRM_RESCHEDULE = "Em đổi lịch hẹn {code} sang {day}, {period}. Quý khách đồng ý không ạ?"
RESCHEDULED = "Dạ em đã đổi lịch hẹn sang {day}, {period}."
ASK_PLAN = "Quý khách muốn đăng ký gói nào, hay huỷ gói hiện tại ạ?"
TERMS = "Trước khi {action}, em xin đọc điều khoản: {terms}"
CONFIRM_PLAN = "Quý khách đồng ý {action} không ạ?"
PLAN_DONE = "Dạ em đã {action} cho quý khách."
NOT_CHANGED = "Dạ em chưa thay đổi gì."
ANYTHING_ELSE = "Quý khách còn cần hỗ trợ gì thêm không ạ?"
GOODBYE = "Cảm ơn quý khách đã gọi NetCo. Chúc quý khách một ngày tốt lành."
TRANSFER = "Dạ, em chuyển máy cho nhân viên hỗ trợ ngay, quý khách vui lòng giữ máy ạ."
CONTINUE_READING = "Dạ em đọc tiếp: {rest}"

SORRY = ("Dạ xin lỗi, em chưa nghe rõ.", "Dạ em xin lỗi, quý khách nói lại giúp em ạ.")
"""Biến thể chọn theo số lần đã xin lỗi trong cuộc gọi, không theo biến toàn cục: hai cuộc gọi
cùng lời khách phải cho cùng lời bot."""


def digits_aloud(number: str) -> str:
    """ "824615390" -> "tám hai bốn, sáu một năm, ba chín không": nhóm ba cho người nghe kịp."""
    words = [UNITS[int(d)] for d in number if d.isdigit()]
    return ", ".join(" ".join(words[i : i + 3]) for i in range(0, len(words), 3))


def number_aloud(value: int) -> str:
    """Số nguyên không âm dưới một tỉ, đọc kiểu miền Bắc: 365000 -> "ba trăm sáu mươi lăm nghìn"."""
    if value == 0:
        return "không"
    parts = []
    millions, rest = divmod(value, 1_000_000)
    thousands, units = divmod(rest, 1000)
    if millions:
        parts.append(f"{_below_thousand(millions, False)} triệu")
    if thousands:
        parts.append(f"{_below_thousand(thousands, bool(millions))} nghìn")
    if units:
        parts.append(_below_thousand(units, bool(millions or thousands)))
    return " ".join(parts)


def _below_thousand(value: int, padded: bool) -> str:
    hundreds, rest = divmod(value, 100)
    tens, ones = divmod(rest, 10)
    words = []
    if hundreds or padded:
        words.append(f"{UNITS[hundreds]} trăm")
    if tens == 0 and ones and (hundreds or padded):
        words.append("linh")
    if tens == 1:
        words.append("mười")
    elif tens:
        words.append(f"{UNITS[tens]} mươi")
    if ones:
        if ones == 5 and tens:
            words.append("lăm")
        elif ones == 1 and tens > 1:
            words.append("mốt")
        elif ones == 4 and tens > 1:
            words.append("tư")
        else:
            words.append(UNITS[ones])
    return " ".join(words)


def money_aloud(dong: int) -> str:
    return f"{number_aloud(dong)} đồng"
