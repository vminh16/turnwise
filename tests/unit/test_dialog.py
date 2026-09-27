"""Năm luồng nghiệp vụ và các quy tắc của SPEC §4.2, chạy bằng lời khách viết sẵn."""

import pytest

from turnwise.config import load_settings
from turnwise.dialog import slots, templates
from turnwise.dialog.backend_stub import NetCoBackend
from turnwise.dialog.machine import Dialog, Reply


@pytest.fixture
def dialog() -> Dialog:
    return Dialog(NetCoBackend(), load_settings().dialog)


def talk(dialog: Dialog, *said: str) -> list[Reply]:
    return [dialog.hear(s) for s in said]


# --- đọc thông tin từ lời khách --------------------------------------------------------


@pytest.mark.parametrize(
    ("said", "number"),
    [
        ("tám hai bốn, sáu một năm, ba chín không", "824615390"),
        ("Số thuê bao là 824-615-390", "824615390"),
        ("6, 6, 2, 19, 0, 5, 3, 7", "662190537"),  # ASR gộp "một chín" thành 19
        ("tám hai bốn", None),
    ],
)
def test_subscriber_numbers_are_read_from_words_or_digits(said: str, number: str | None) -> None:
    assert slots.subscriber_id(said) == number


def test_appointment_codes_accept_the_spoken_letter() -> None:
    assert slots.appointment_code("mã là lờ bốn bảy, hai không, chín ba") == "L472093"
    assert slots.appointment_code("L 47 20 93") == "L472093"


@pytest.mark.parametrize(
    ("said", "answer"),
    [
        ("Đúng rồi.", True),
        ("Dạ.", True),
        ("Không phải.", False),
        ("dạ không", False),
        ("ừm để xem", None),
        ("", None),
    ],
)
def test_silence_and_mixed_answers_are_not_consent(said: str, answer: bool | None) -> None:
    assert slots.yes_no(said) is answer


def test_numbers_are_spoken_as_words_for_the_tts() -> None:
    assert templates.digits_aloud("824615390") == "tám hai bốn, sáu một năm, ba chín không"
    assert templates.money_aloud(365_000) == "ba trăm sáu mươi lăm nghìn đồng"
    assert templates.money_aloud(36_500) == "ba mươi sáu nghìn năm trăm đồng"
    assert templates.number_aloud(105) == "một trăm linh năm"


# --- luồng trọn vẹn --------------------------------------------------------------------


def test_n1_outage_opens_a_ticket(dialog: Dialog) -> None:
    replies = talk(
        dialog,
        "Mạng nhà tôi mất từ sáng",
        "tám hai bốn sáu một năm ba chín không",
        "Đúng rồi",
        "Đèn internet nháy đỏ",
        "Sáng mai",
    )
    assert dialog.backend.tickets and "ngày mai" in replies[-1].text
    assert dialog.expect == "anything_else"


def test_n2_reads_the_bill_as_an_interruptible_passage(dialog: Dialog) -> None:
    replies = talk(dialog, "Tôi muốn tra cước", "519 083 274", "Đúng", "Tháng tám")
    assert replies[-1].interruptible
    assert "truyền hình bổ sung sáu mươi lăm nghìn đồng" in replies[-1].text


def test_n3_changes_nothing_without_a_clear_yes(dialog: Dialog) -> None:
    talk(dialog, "Tôi muốn đổi lịch hẹn", "L 47 20 93", "Thứ năm", "Buổi chiều")
    assert dialog.backend.log == []
    talk(dialog, "")  # im lặng không phải đồng ý
    assert dialog.backend.log == []
    talk(dialog, "Đồng ý")
    assert dialog.backend.appointments["L472093"].day == "thứ Năm"


def test_n4_reads_terms_before_asking_to_confirm(dialog: Dialog) -> None:
    replies = talk(dialog, "Tôi muốn nâng gói", "248630915", "Đúng", "Gói ba trăm")
    assert "điều khoản" in replies[-1].text and replies[-1].interruptible
    talk(dialog, "Dạ đồng ý")
    assert dialog.backend.accounts["248630915"].plan == "Gói Tốc Độ 300"


def test_the_call_ends_with_a_goodbye(dialog: Dialog) -> None:
    replies = talk(dialog, "Tôi muốn tra cước", "519083274", "Đúng", "Tháng tám", "Không")
    assert replies[-1].end and replies[-1].text == templates.GOODBYE


# --- quy tắc §4.2 ----------------------------------------------------------------------


@pytest.mark.parametrize("step", range(4))
def test_asking_for_an_agent_transfers_at_any_point_with_context(dialog: Dialog, step: int) -> None:
    before = ["Tôi muốn tra cước", "519 083 274", "Đúng", "Tháng tám"][:step]
    talk(dialog, *before)
    reply = dialog.hear("Thôi cho tôi gặp nhân viên")
    assert reply.transfer is not None and reply.end
    if step >= 2:
        assert reply.transfer["subscriber_id"] == "519083274"


def test_three_misses_on_the_same_question_transfer(dialog: Dialog) -> None:
    replies = talk(dialog, "Tôi muốn tra cước", "à ừm", "để tôi xem", "không nhớ")
    assert replies[-1].transfer is not None
    assert "subscriber" in replies[-1].transfer["reason"]


def test_an_interrupted_passage_resumes_where_it_stopped(dialog: Dialog) -> None:
    talk(dialog, "Tôi muốn tra cước", "519 083 274", "Đúng", "Tháng tám")
    dialog.interrupted(0.5)
    reply = dialog.hear("tiếp")
    assert reply.text.startswith("Dạ em đọc tiếp") and "Tổng cộng" in reply.text
