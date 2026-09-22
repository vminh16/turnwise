"""Kịch bản đóng vai phải phủ đủ thứ cần đo, và kịch bản sai phải nổ lúc nạp.

Thiếu một hành vi trong kịch bản không làm gì hỏng ngay. Nó chỉ lộ ra sau khi đã thu xong
hai mươi người và phát hiện bộ dữ liệu vàng không có ca nói đè nào ở luồng tra cước.
"""

from collections import Counter
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from evaluation.roleplay import (
    ROLEPLAY_DIR,
    Behaviour,
    Flow,
    final_syllable_tone,
    load,
    load_all,
    load_common,
)
from turnwise.types import Tone

VALID = """
name: fixture
flow: N2
title: fixture
summary: fixture
brief: fixture
persona: fixture
steps:
  - bot: "Cước tháng này gồm: / cước gói ba trăm nghìn đồng."
    reading: amount
    example: "(Nghe và đáp lời)"
    customer: Chêm "dạ".
    behaviours: [backchannel]
"""


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "n2-fixture.yaml"
    path.write_text(body, encoding="utf-8")
    return path


# --- thanh điệu từ chữ viết -------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "tone"),
    [
        ("da", Tone.LEVEL),
        ("dà", Tone.FALLING),
        ("dá", Tone.RISING),
        ("dả", Tone.DIPPING),
        ("dã", Tone.BROKEN),
        ("dạ", Tone.DROP),
        ("Đúng đấy.", Tone.RISING),  # dấu mũ của "â" là dấu nguyên âm, không phải dấu thanh
        ("Được ạ!", Tone.DROP),  # chỉ âm tiết cuối mới tính
        ("Hủy.", Tone.DIPPING),
        ("Huỷ.", Tone.DIPPING),  # hai cách bỏ dấu phải cho cùng một thanh
        ("Số 824", Tone.UNKNOWN),  # chữ số không có thanh cho tới khi biết cách đọc
        ("", Tone.UNKNOWN),
    ],
)
def test_final_syllable_tone_reads_the_last_syllable(text: str, tone: Tone) -> None:
    assert final_syllable_tone(text) == tone


# --- độ phủ của bộ kịch bản đã commit ---------------------------------------------------


def test_every_committed_script_validates() -> None:
    scripts = load_all(ROLEPLAY_DIR)
    assert len(scripts) == 9
    assert len({script.name for script in scripts}) == len(scripts)


def test_every_script_file_is_named_after_its_flow() -> None:
    for script in load_all(ROLEPLAY_DIR):
        assert script.path.stem == script.name
        assert script.name.startswith(script.flow.lower() + "-")


def test_every_business_flow_has_a_script() -> None:
    flows = {script.flow for script in load_all(ROLEPLAY_DIR)}
    assert flows == set(get_args(Flow))


def test_every_behaviour_is_elicited_in_at_least_two_flows() -> None:
    """Một hành vi chỉ có ở một luồng thì lỗi của nó không tách được khỏi luồng đó."""
    flows_by_behaviour: dict[str, set[str]] = {b: set() for b in get_args(Behaviour)}
    for script in load_all(ROLEPLAY_DIR):
        for behaviour in script.behaviours:
            flows_by_behaviour[behaviour].add(script.flow)
    thin = {b: flows for b, flows in flows_by_behaviour.items() if len(flows) < 2}
    assert not thin, f"hành vi chỉ có ở dưới hai luồng: {thin}"


def test_agent_request_happens_mid_flow_while_the_bot_is_reading() -> None:
    """SPEC §4.2: N5 phải chạy được ở bất kỳ điểm nào, kể cả giữa lúc bot đang đọc."""
    mid_flow = [
        step
        for script in load_all(ROLEPLAY_DIR)
        if script.flow != "N5"
        for step in script.steps
        if "agent_request" in step.behaviours and step.reading is not None
    ]
    assert mid_flow


def test_short_answer_suggestions_cover_all_six_tones() -> None:
    """Chỉ số chính tách lỗi theo thanh của âm tiết cuối; thiếu một thanh là thiếu một cột."""
    tones = Counter(
        final_syllable_tone(reply)
        for script in load_all(ROLEPLAY_DIR)
        for step in script.steps
        for reply in step.replies
    )
    assert Tone.UNKNOWN not in tones, "gợi ý trả lời không được kết thúc bằng chữ số"
    missing = set(Tone) - {Tone.UNKNOWN} - set(tones)
    assert not missing, f"thiếu thanh: {missing}; đang có {dict(tones)}"


def test_da_is_elicited_as_a_complete_answer_not_only_as_a_backchannel() -> None:
    """SPEC §2: "dạ" chêm vào là tiếng đệm, "Dạ." đứng một mình sau câu hỏi là một lượt trọn.

    Cùng chuỗi âm, hai chức năng ngược nhau — đó là ca khó nhất của R4. Bộ dữ liệu chỉ có
    "dạ" kiểu tiếng đệm thì không đo được bộ phân biệt nào cả.
    """
    flows = {
        script.flow
        for script in load_all(ROLEPLAY_DIR)
        for step in script.steps
        if "Dạ." in step.replies
    }
    assert len(flows) >= 2, f'"Dạ." trọn lượt chỉ có ở {flows}'


def test_backchannel_examples_describe_the_task_and_never_supply_words() -> None:
    """Đưa sẵn "ừ, vâng" thì người thu chêm nhiều hơn bình thường; chỉ tả việc cần làm."""
    for script in load_all(ROLEPLAY_DIR):
        for step in script.steps:
            if "backchannel" in step.behaviours:
                assert step.example.startswith("(") and step.example.endswith(")"), step.example


def test_examples_never_give_away_what_the_caller_must_look_up() -> None:
    """Số và mã trên thẻ phải tự tìm; câu mẫu chứa sẵn thì mất ngập ngừng thật."""
    for script in load_all(ROLEPLAY_DIR):
        secrets = [value.replace(" ", "") for value in script.props.values()]
        for step in script.steps:
            flat = step.example.replace(" ", "")
            assert not any(value in flat for value in secrets), step.example


def test_every_call_is_closed_by_the_bot() -> None:
    """Không tổng đài nào cúp máy ngay sau một câu hỏi.

    Web thu tự phục vụ chỉ phát các bước trong kịch bản, nên lời chào kết thúc hay lời chuyển
    máy phải là bước cuối của chính kịch bản. Thiếu nó thì cuộc gọi cụt, và mất luôn lượt khách
    chào lại — thường ngắn và hay chồng lên lời bot.
    """
    for script in load_all(ROLEPLAY_DIR):
        last = " ".join(script.steps[-1].bot.split())
        assert not last.endswith("?"), f"{script.name} kết thúc bằng câu hỏi: {last}"
        if "agent_request" in script.behaviours:
            assert "chuyển máy" in last, f"{script.name} đòi gặp nhân viên nhưng không chuyển máy"
        else:
            assert "Cảm ơn quý khách" in last, f"{script.name} không chào kết thúc: {last}"


def test_common_prompts_cover_what_the_operator_needs_off_script() -> None:
    prompts = load_common(ROLEPLAY_DIR).prompts
    assert {"repeat", "sorry_stop", "transfer", "goodbye"} <= set(prompts)


# --- kịch bản sai phải nổ lúc nạp -------------------------------------------------------


def test_the_fixture_itself_is_valid(tmp_path: Path) -> None:
    assert load(write(tmp_path, VALID)).behaviours == {"backchannel"}


def test_overlap_without_a_bot_reading_is_refused(tmp_path: Path) -> None:
    """Tiếng đệm cần bot đang nói một đoạn dài; không có đoạn đọc thì không có chỗ chêm."""
    body = VALID.replace("    reading: amount\n", "")
    with pytest.raises(ValidationError, match="reading"):
        load(write(tmp_path, body))


def test_a_bot_reading_without_pause_marks_is_refused(tmp_path: Path) -> None:
    """Đoạn đọc liền một hơi không để chỗ tự nhiên nào cho tiếng đệm."""
    body = VALID.replace("gồm: / cước", "gồm cước")
    with pytest.raises(ValidationError, match="ngắt"):
        load(write(tmp_path, body))


def test_a_short_answer_without_suggested_replies_is_refused(tmp_path: Path) -> None:
    body = VALID.replace("[backchannel]", "[short_answer]")
    with pytest.raises(ValidationError, match="replies"):
        load(write(tmp_path, body))


def test_replies_on_a_step_that_is_not_a_short_answer_are_refused(tmp_path: Path) -> None:
    body = VALID.replace("[backchannel]", '[backchannel]\n    replies: ["Vâng."]')
    with pytest.raises(ValidationError, match="replies"):
        load(write(tmp_path, body))


def test_an_unknown_behaviour_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load(write(tmp_path, VALID.replace("[backchannel]", "[interruption]")))


def test_an_unknown_key_is_refused(tmp_path: Path) -> None:
    """Gõ nhầm `behaviour:` thay vì `behaviours:` không được lặng lẽ thành một bước trống."""
    with pytest.raises(ValidationError):
        load(write(tmp_path, VALID.replace("behaviours:", "behaviour:")))


def test_a_script_without_steps_is_refused(tmp_path: Path) -> None:
    body = VALID.split("steps:")[0] + "steps: []\n"
    with pytest.raises(ValidationError, match="bước"):
        load(write(tmp_path, body))
