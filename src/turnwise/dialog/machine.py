"""Máy trạng thái cho năm luồng nghiệp vụ của SPEC §4.1, theo đúng các quy tắc §4.2.

Nhận chữ khách vừa nói, trả câu bot nói tiếp. Không biết gì về âm thanh hay lượt nói: khi nào
gọi `hear()` là việc của tầng `turn` và phần nối dây (`AGENTS.md`).

Quy tắc §4.2 và chỗ chúng nằm trong code:

- N5 ưu tiên tuyệt đối: `hear()` xét `wants_agent` trước mọi thứ khác, ở mọi trạng thái.
- Chuyển máy kèm ngữ cảnh: `Reply.transfer` mang luồng đang dở và mọi trường đã thu.
- Xác nhận trước khi thay đổi: N3 và N4 chỉ gọi backend sau một câu "có" rõ ràng.
- Ba lần hiểu sai thì chuyển người: `_miss()` đếm theo từng câu hỏi.
- Không đoán trường thiếu: mỗi trường rút bằng `slots`, `None` thì hỏi lại.
- Số thuê bao đọc lại cho khách xác nhận trước khi tra.
- Đọc dài ngắt được và nhớ chỗ (R11): `interrupted()` ghi phần chưa đọc; khách bảo "tiếp" thì
  đọc nốt.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from turnwise.config import DialogConfig
from turnwise.dialog import slots, templates
from turnwise.dialog.backend_stub import PLANS, TERMS, NetCoBackend

FLOW_NAMES = {
    "N1": "báo sự cố mất mạng",
    "N2": "tra cứu cước",
    "N3": "đổi lịch hẹn kỹ thuật viên",
    "N4": "đăng ký hoặc huỷ gói",
}


@dataclass(frozen=True)
class Reply:
    text: str
    interruptible: bool = False
    """Đoạn đọc dài (cước, điều khoản): khách được ngắt, và bot phải nhớ đã đọc tới đâu."""

    transfer: dict[str, str] | None = None
    """Có giá trị thì chuyển máy; đây là ngữ cảnh điện thoại viên nhận được (R9)."""

    end: bool = False


@dataclass
class Dialog:
    backend: NetCoBackend
    config: DialogConfig
    flow: str | None = None
    fields: dict[str, str] = field(default_factory=dict)
    expect: str = "intent"
    misses: Counter[str] = field(default_factory=Counter)
    _unread: str = ""
    _last_read: str = ""
    _sorry: int = 0

    def greet(self) -> Reply:
        return Reply(templates.GREETING)

    def interrupted(self, spoken_fraction: float) -> None:
        """Bot bị ngắt khi đang đọc câu vừa rồi; ghi phần chưa đọc, cắt ở ranh giới dấu phẩy."""
        text = self._last_read
        if not text:
            return
        cut = int(len(text) * max(0.0, min(1.0, spoken_fraction)))
        comma = text.rfind(",", 0, cut)
        self._unread = text[comma + 1 :].strip() if comma >= 0 else text

    def hear(self, text: str) -> Reply:
        if slots.wants_agent(text):
            return self._transfer("khách yêu cầu gặp nhân viên")
        if self._unread and slots.normalise(text).strip() in (
            "tiếp",
            "đọc tiếp",
            "tiếp đi",
            "ừ tiếp",
        ):
            rest, self._unread = self._unread, ""
            return self._read(templates.CONTINUE_READING.format(rest=rest))
        self._unread = ""
        handler = getattr(self, f"_on_{self.expect}")
        reply: Reply = handler(text)
        return reply

    def context(self) -> dict[str, str]:
        return {
            "flow": FLOW_NAMES.get(self.flow or "", "chưa rõ"),
            "step": self.expect,
            **self.fields,
        }

    # --- khung chung -------------------------------------------------------------------

    def _ask(self, expect: str, text: str) -> Reply:
        self.expect = expect
        return Reply(text)

    def _read(self, text: str) -> Reply:
        self._last_read = text
        return Reply(text, interruptible=True)

    def _miss(self, again: str) -> Reply:
        self.misses[self.expect] += 1
        if self.misses[self.expect] >= self.config.max_retries:
            return self._transfer(f"hỏi lại {self.expect} {self.misses[self.expect]} lần")
        sorry = templates.SORRY[self._sorry % len(templates.SORRY)]
        self._sorry += 1
        return Reply(f"{sorry} {again}")

    def _transfer(self, reason: str) -> Reply:
        context = {**self.context(), "reason": reason}
        self.expect = "transferred"
        return Reply(templates.TRANSFER, transfer=context, end=True)

    def _finish_flow(self, done_text: str) -> Reply:
        self.flow, self.fields = None, {}
        self.expect = "anything_else"
        return Reply(f"{done_text} {templates.ANYTHING_ELSE}")

    # --- mở đầu và kết thúc ------------------------------------------------------------

    def _on_intent(self, text: str) -> Reply:
        flow = slots.intent(text)
        if flow is None:
            return self._miss(templates.ASK_INTENT)
        self.flow = flow
        if flow == "N3":
            return self._ask("code", templates.ASK_CODE)
        return self._ask("subscriber", templates.ASK_SUBSCRIBER)

    def _on_anything_else(self, text: str) -> Reply:
        flow = slots.intent(text)
        if flow is not None:
            return self._on_intent(text)
        if slots.yes_no(text) is True:
            return self._ask("intent", templates.ASK_INTENT)
        self.expect = "done"
        return Reply(templates.GOODBYE, end=True)

    def _on_done(self, text: str) -> Reply:
        return Reply(templates.GOODBYE, end=True)

    def _on_transferred(self, text: str) -> Reply:
        return Reply(templates.TRANSFER, transfer=self.context(), end=True)

    # --- số thuê bao (N1, N2, N4) ------------------------------------------------------

    def _on_subscriber(self, text: str) -> Reply:
        number = slots.subscriber_id(text)
        if number is None:
            return self._miss(templates.ASK_SUBSCRIBER_AGAIN)
        if self.backend.account(number) is None:
            return self._miss(templates.UNKNOWN_SUBSCRIBER)
        self.fields["subscriber_id"] = number
        text_out = templates.CONFIRM_SUBSCRIBER.format(number=templates.digits_aloud(number))
        return self._ask("confirm_subscriber", text_out)

    def _on_confirm_subscriber(self, text: str) -> Reply:
        answer = slots.yes_no(text)
        if answer is None:
            return self._miss(
                templates.CONFIRM_SUBSCRIBER.format(
                    number=templates.digits_aloud(self.fields["subscriber_id"])
                )
            )
        if not answer:
            self.fields.pop("subscriber_id", None)
            return self._ask("subscriber", templates.ASK_SUBSCRIBER)
        return {
            "N1": lambda: self._ask("description", templates.ASK_DESCRIPTION),
            "N2": lambda: self._ask("month", templates.ASK_MONTH),
            "N4": lambda: self._ask("plan", templates.ASK_PLAN),
        }[self.flow or "N1"]()

    # --- N1 -----------------------------------------------------------------------------

    def _on_description(self, text: str) -> Reply:
        if not text.strip():
            return self._miss(templates.ASK_DESCRIPTION)
        self.fields["description"] = text.strip()
        return self._ask("day", templates.ASK_DAY)

    def _on_day(self, text: str) -> Reply:
        day = slots.day(text)
        if day is None:
            return self._miss(templates.ASK_DAY)
        self.fields["day"] = day
        period = slots.period(text)
        if period is not None:
            return self._on_period(text)
        return self._ask("period", templates.ASK_PERIOD)

    def _on_period(self, text: str) -> Reply:
        period = slots.period(text)
        if period is None:
            return self._miss(templates.ASK_PERIOD)
        self.fields["period"] = period
        if self.flow == "N3":
            return self._ask(
                "confirm_reschedule",
                templates.CONFIRM_RESCHEDULE.format(
                    code=templates.digits_aloud(self.fields["code"][1:]),
                    day=self.fields["day"],
                    period=period,
                ),
            )
        ticket = self.backend.open_outage_ticket(
            self.fields["subscriber_id"],
            self.fields.get("description", ""),
            f"{self.fields['day']} {period}",
        )
        return self._finish_flow(
            templates.TICKET_DONE.format(
                ticket=templates.digits_aloud(ticket[2:]), day=self.fields["day"], period=period
            )
        )

    # --- N2 -----------------------------------------------------------------------------

    def _on_month(self, text: str) -> Reply:
        month = slots.month(text)
        if month is None:
            return self._miss(templates.ASK_MONTH)
        items = self.backend.bill(self.fields["subscriber_id"], month) or []
        spoken = ", ".join(f"{name} {templates.money_aloud(amount)}" for name, amount in items)
        total = templates.money_aloud(sum(amount for _, amount in items))
        reply = self._read(
            templates.BILL.format(month=templates.number_aloud(month), items=spoken, total=total)
        )
        self.flow, self.fields = None, {}
        self.expect = "anything_else"
        return Reply(f"{reply.text} {templates.ANYTHING_ELSE}", interruptible=True)

    # --- N3 -----------------------------------------------------------------------------

    def _on_code(self, text: str) -> Reply:
        code = slots.appointment_code(text)
        if code is None or code not in self.backend.appointments:
            return self._miss(templates.ASK_CODE_AGAIN)
        self.fields["code"] = code
        return self._ask("day", templates.ASK_DAY)

    def _on_confirm_reschedule(self, text: str) -> Reply:
        answer = slots.yes_no(text)
        if answer is None:
            return self._miss(
                templates.CONFIRM_RESCHEDULE.format(
                    code=templates.digits_aloud(self.fields["code"][1:]),
                    day=self.fields["day"],
                    period=self.fields["period"],
                )
            )
        if not answer:
            return self._finish_flow(templates.NOT_CHANGED)
        self.backend.reschedule(self.fields["code"], self.fields["day"], self.fields["period"])
        return self._finish_flow(
            templates.RESCHEDULED.format(day=self.fields["day"], period=self.fields["period"])
        )

    # --- N4 -----------------------------------------------------------------------------

    def _on_plan(self, text: str) -> Reply:
        norm = slots.normalise(text)
        if "huỷ" in norm:
            self.fields["action"] = "huỷ gói"
        else:
            number = next((key for key in PLANS if key in slots.digits(text) or key in norm), None)
            if number is None and "ba trăm" in norm:
                number = "300"
            if number is None:
                return self._miss(templates.ASK_PLAN)
            self.fields["plan"] = PLANS[number]
            self.fields["action"] = f"đăng ký {PLANS[number]}"
        reply = self._read(templates.TERMS.format(action=self.fields["action"], terms=TERMS))
        self.expect = "confirm_plan"
        return Reply(
            f"{reply.text} {templates.CONFIRM_PLAN.format(action=self.fields['action'])}",
            interruptible=True,
        )

    def _on_confirm_plan(self, text: str) -> Reply:
        answer = slots.yes_no(text)
        if answer is None:
            return self._miss(templates.CONFIRM_PLAN.format(action=self.fields["action"]))
        if not answer:
            return self._finish_flow(templates.NOT_CHANGED)
        subscriber = self.fields["subscriber_id"]
        if "plan" in self.fields:
            self.backend.change_plan(subscriber, self.fields["plan"])
        else:
            self.backend.cancel_plan(subscriber)
        return self._finish_flow(templates.PLAN_DONE.format(action=self.fields["action"]))
