"""Vẽ đường cong đánh đổi của một dải quét baseline.

Một hình, hai trục, mỗi trục một chỉ số đối kháng: độ trễ đáp nằm ngang, tỉ lệ cắt
lời nằm dọc, mỗi điểm là **một ngưỡng**. Đó là cách trình bày mà `SPEC.md` §9.3 quy
tắc 1 yêu cầu — không phải hai biểu đồ cạnh nhau, và tuyệt đối không phải một biểu đồ
hai trục dọc, vì hai thang khác nhau chồng lên nhau tạo ra quan hệ mà dữ liệu không có.

Hình này mang theo cảnh báo in ngay trên nó. Ảnh đi xa hơn ngữ cảnh sinh ra nó: ai đó
sẽ dán nó vào slide, và lúc đó dòng chữ "file-based, synthetic audio" là thứ duy nhất
ngăn con số bị đọc như độ trễ thật.

Chữ trong hình viết tiếng Anh — font mặc định của matplotlib không có đủ chữ có dấu,
và chữ thiếu glyph in ra thành ô vuông.

`matplotlib` nằm trong extra `research` (`uv sync --extra research`), không thuộc
đường chạy runtime.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # không cần cửa sổ; chạy được trong CI

import matplotlib.pyplot as plt

from evaluation.metrics import CurvePoint

SERIES = "#2f6f9f"
"""Điểm mà bot có đáp trong mọi kịch bản."""

MISSED = "#c2521a"
"""Điểm mà có kịch bản bot không đáp gì. Kèm hình dấu X và nhãn, không chỉ màu."""

INK = "#1c1c1c"
MUTED = "#6b6b6b"
SURFACE = "#fcfcfb"


def plot_tradeoff(points: Sequence[CurvePoint], path: Path, title: str) -> Path:
    """Vẽ và ghi hình. Điểm nào thiếu một trong hai trục thì bỏ, không vẽ nửa vời."""
    plotted = [
        (point, point.median_response_latency_ms, point.interruption_rate * 100)
        for point in points
        if point.median_response_latency_ms is not None
    ]
    if not plotted:
        raise ValueError("không có điểm nào mang đủ cả hai trục")

    figure, axes = plt.subplots(figsize=(8.0, 5.0), dpi=150)
    figure.patch.set_facecolor(SURFACE)
    axes.set_facecolor(SURFACE)

    interruptions = [interruption for _, _, interruption in plotted]
    axes.plot(
        [latency for _, latency, _ in plotted],
        interruptions,
        color=SERIES,
        linewidth=2.0,
        zorder=2,
    )

    for point, latency, interruption in plotted:
        missed = point.no_response > 0
        axes.scatter(
            latency,
            interruption,
            s=90 if missed else 60,
            marker="X" if missed else "o",
            color=MISSED if missed else SERIES,
            edgecolor=SURFACE,
            linewidth=2.0,
            zorder=3,
        )
        axes.annotate(
            f"{point.threshold_ms}ms",
            (latency, interruption),
            textcoords="offset points",
            xytext=(0, 12),
            ha="center",
            fontsize=8,
            color=MUTED,
        )

    # Hình dấu cộng chú giải mang danh tính, không phải màu: đọc được cả khi in đen
    # trắng và cả với người mù màu. Số kịch bản không đáp nằm ở cột `no_response`
    # trong CSV — nhồi nó lên hình làm ba nhãn đè lên nhau.
    axes.scatter([], [], s=60, marker="o", color=SERIES, label="every scenario answered")
    axes.scatter([], [], s=90, marker="X", color=MISSED, label="some scenarios unanswered")
    legend = axes.legend(frameon=False, fontsize=9, loc="center right")
    for text in legend.get_texts():
        text.set_color(MUTED)

    axes.set_xlabel("Median reply latency (ms, file-based)", color=INK, fontsize=10)
    axes.set_ylabel("Interruption rate (%)", color=INK, fontsize=10)
    axes.set_title(title, color=INK, fontsize=12, loc="left", pad=18)
    axes.set_ylim(-6, max(interruptions) + 14)
    axes.grid(True, color="#e4e4e0", linewidth=0.8, zorder=1)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color("#d0d0cc")
    axes.tick_params(colors=MUTED, labelsize=9)

    figure.text(
        0.01,
        0.015,
        "Synthetic phase-0 audio, timing measured from files. Not reportable latency "
        "(SPEC 9.3 rule 4 requires the live path).",
        fontsize=7.5,
        color=MUTED,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout(rect=(0, 0.04, 1, 1))
    figure.savefig(path, facecolor=SURFACE)
    plt.close(figure)
    return path
