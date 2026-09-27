"""Backend giả của NetCo — công ty giả định (`docs/roadmap.md` GĐ 4). Không dữ liệu thật nào.

Dữ liệu khớp thẻ đạo cụ của kịch bản đóng vai (`roleplay/*.yaml`), để một người đã thu âm gọi
vào bot và đọc đúng số trên thẻ thì bot tra ra đúng khách.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Account:
    subscriber_id: str
    plan: str
    bills: dict[int, list[tuple[str, int]]] = field(default_factory=dict)
    """Tháng -> các khoản (tên khoản, số đồng)."""


@dataclass
class Appointment:
    code: str
    subscriber_id: str
    day: str
    period: str
    address: str


PLANS = {"100": "Gói Tốc Độ 100", "200": "Gói Tốc Độ 200", "300": "Gói Tốc Độ 300"}

TERMS = (
    "Gói mới áp dụng từ kỳ cước sau, cam kết sử dụng tối thiểu sáu tháng, "
    "huỷ trước hạn thì phí huỷ bằng một tháng cước."
)


class NetCoBackend:
    def __init__(self) -> None:
        self.accounts = {
            a.subscriber_id: a
            for a in (
                Account("824615390", "Gói Tốc Độ 100"),
                Account("307942186", "Gói Tốc Độ 100"),
                Account(
                    "519083274",
                    "Gói Tốc Độ 200",
                    {8: [("cước gói", 300_000), ("truyền hình bổ sung", 65_000), ("thuế", 36_500)]},
                ),
                Account("662190537", "Gói Tốc Độ 200", {8: [("cước gói", 300_000)]}),
                Account("248630915", "Gói Tốc Độ 100"),
                Account("731458062", "Gói Tốc Độ 200"),
            )
        }
        self.appointments = {
            "L472093": Appointment("L472093", "824615390", "thứ Ba", "buổi sáng", "số 12 Lê Lợi"),
            "L813605": Appointment("L813605", "307942186", "thứ Tư", "buổi chiều", "số 5 Hàng Bài"),
        }
        self.tickets: list[dict[str, str]] = []
        self.log: list[str] = []
        """Mọi thao tác ghi dữ liệu, để kiểm quy tắc "xác nhận trước khi thay đổi" (SPEC §4.2)."""

    def account(self, subscriber_id: str) -> Account | None:
        return self.accounts.get(subscriber_id)

    def bill(self, subscriber_id: str, month: int) -> list[tuple[str, int]] | None:
        account = self.accounts.get(subscriber_id)
        return None if account is None else account.bills.get(month, [("cước gói", 300_000)])

    def open_outage_ticket(self, subscriber_id: str, description: str, slot: str) -> str:
        number = f"SC{len(self.tickets) + 1:04d}"
        self.tickets.append(
            {"id": number, "subscriber": subscriber_id, "note": description, "slot": slot}
        )
        self.log.append(f"ticket {number}")
        return number

    def reschedule(self, code: str, day: str, period: str) -> None:
        appointment = self.appointments[code]
        appointment.day, appointment.period = day, period
        self.log.append(f"reschedule {code} {day} {period}")

    def change_plan(self, subscriber_id: str, plan: str) -> None:
        self.accounts[subscriber_id].plan = plan
        self.log.append(f"plan {subscriber_id} {plan}")

    def cancel_plan(self, subscriber_id: str) -> None:
        self.accounts[subscriber_id].plan = ""
        self.log.append(f"cancel {subscriber_id}")
