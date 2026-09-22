"""Dựng cuộc gọi mẫu để nghe thử trước buổi thu. CHỈ ĐỂ NGHE, KHÔNG PHẢI DỮ LIỆU.

    uv run python demo_calls.py            # cả chín kịch bản
    uv run python demo_calls.py n2-a-bill-backchannel

Kênh bot là đúng các file đã nạp vào collector (`prompts/`, do `render_prompts.py` sinh). Kênh
khách là một giọng TTS khác đọc lời mẫu trong `demo_calls.yaml`. Nhịp ghép theo đúng cách web thu
chạy: câu bot phát tới hết kể cả khi bị nói đè; câu bot kế tiếp chỉ bắt đầu sau khi khách nói
xong và bấm nút (khoảng một giây). Ra `out/demo/`: wav stereo 48 kHz (trái khách, phải bot, như
nút Nghe ở trang admin) và `index.html` có lời thoại theo thời gian.
"""

from __future__ import annotations

import html
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
os.environ.setdefault("HF_HOME", str(HERE / "models"))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import yaml  # noqa: E402

ROLEPLAY = HERE.parent / "roleplay"
PROMPTS = HERE / "prompts"
OUT = HERE / "out" / "demo"
RATE = 48_000
PRECISION = "int8"
REPLY_GAP_S = 0.5  # khách bắt đầu đáp sau khi bot dứt lời
PRESS_GAP_S = 1.0  # khách nói xong, bấm nút, cộng 100 ms lead của collector
SILENT_TURN_S = 1.5
TAIL_S = 1.5
PAUSE_RMS = 0.01
PAUSE_MIN_S = 0.2


def emit(line: object = "") -> None:
    sys.stdout.write(f"{line}\n")


def pauses(audio: np.ndarray) -> list[float]:
    """Mốc bắt đầu (giây) của các chỗ ngắt hơi trong câu bot, bỏ đầu và cuối câu."""
    frame = RATE // 50
    rms = np.sqrt(np.mean(audio[: len(audio) // frame * frame].reshape(-1, frame) ** 2, axis=1))
    quiet = rms < PAUSE_RMS
    found, run_start = [], None
    for i, q in enumerate(quiet):
        if q and run_start is None:
            run_start = i
        elif not q and run_start is not None:
            if (i - run_start) * 0.02 >= PAUSE_MIN_S and run_start > 0:
                found.append(run_start * 0.02)
            run_start = None
    return found


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    from vieneu import Vieneu

    demos = yaml.safe_load((HERE / "demo_calls.yaml").read_text("utf-8"))
    names = sys.argv[1:] or list(demos)
    tts = Vieneu(mode="v3turbo", precision=PRECISION)
    OUT.mkdir(parents=True, exist_ok=True)
    cache: dict[tuple[str, str], np.ndarray] = {}

    def speak(voice: str, text: str) -> np.ndarray:
        if (voice, text) not in cache:
            cache[(voice, text)] = tts.infer(text, voice=voice).astype(np.float32)
        return cache[(voice, text)]

    def utterance(voice: str, say: str | list) -> np.ndarray:
        parts = say if isinstance(say, list) else [say]
        pieces = [
            np.zeros(int(RATE * p), np.float32) if isinstance(p, (int, float)) else speak(voice, p)
            for p in parts
        ]
        return np.concatenate(pieces)

    pages = []
    for name in names:
        demo = demos[name]
        script = yaml.safe_load((ROLEPLAY / f"{name}.yaml").read_text("utf-8"))
        steps, turns, voice = script["steps"], demo["turns"], demo["voice"]
        if len(turns) != len(steps):
            raise SystemExit(f"{name}: {len(turns)} lượt khách cho {len(steps)} bước bot")
        events: list[tuple[str, float, np.ndarray, str]] = []  # (kênh, giây, âm thanh, lời)
        t = 0.5
        for index, (step, turn) in enumerate(zip(steps, turns, strict=True)):
            bot, _ = sf.read(PROMPTS / name / f"{index}.wav", dtype="float32")
            events.append(("bot", t, bot, " ".join(step["bot"].split()).replace(" / ", ", ")))
            bot_end = t + len(bot) / RATE
            if turn is None:
                t = bot_end + SILENT_TURN_S
                continue
            for at, word in zip(pauses(bot), turn.get("backchannel", []), strict=False):
                events.append(("khách", t + at + 0.05, speak(voice, word), f"({word})"))
            if "say" not in turn:
                t = bot_end + PRESS_GAP_S
                continue
            said = utterance(voice, turn["say"])
            start = t + turn["at"] * len(bot) / RATE if "at" in turn else bot_end + REPLY_GAP_S
            parts = turn["say"] if isinstance(turn["say"], list) else [turn["say"]]
            text = " … ".join(p for p in parts if isinstance(p, str))
            events.append(("khách", start, said, text + ("  [nói đè]" if "at" in turn else "")))
            t = max(bot_end, start + len(said) / RATE) + PRESS_GAP_S
        total = int(RATE * (t + TAIL_S))
        stereo = np.zeros((total, 2), np.float32)
        for channel, start, audio, _ in events:
            col = 0 if channel == "khách" else 1
            i = int(start * RATE)
            stereo[i : i + len(audio), col] += audio[: total - i]
        stereo /= max(1.0, float(np.abs(stereo).max()))
        sf.write(OUT / f"{name}.wav", stereo, RATE, subtype="PCM_16")
        turns_said = sum(e[0] == "khách" for e in events)
        emit(f"{name:<32} {t + TAIL_S:5.1f} s, {turns_said} lượt khách")
        lines = "".join(
            f'<tr class="{c}"><td>{s:5.1f}s</td><td>{"Khách" if c == "khách" else "Bot"}</td>'
            f"<td>{html.escape(x)}</td></tr>"
            for c, s, _, x in sorted(events, key=lambda e: e[1])
        )
        pages.append(
            f"<section><h2>{html.escape(script['title'])}</h2>"
            f'<audio controls preload="none" src="{name}.wav"></audio>'
            f"<table>{lines}</table></section>"
        )
    (OUT / "index.html").write_text(
        '<!doctype html><html lang="vi"><meta charset="utf-8"><title>Cuộc gọi mẫu</title><style>'
        "body{font:15px system-ui;margin:24px auto;max-width:900px;padding:0 16px}"
        "audio{width:100%;margin:6px 0}td{padding:3px 8px;vertical-align:top}"
        "tr.bot td:nth-child(2){color:#2f5d8a}tr.khách td:nth-child(2){color:#8a4b2f}"
        "section{margin-bottom:32px}</style>"
        "<h1>Cuộc gọi mẫu — chỉ để nghe thử</h1><p>Tai trái: khách (giọng TTS đọc lời mẫu). "
        "Tai phải: bot, đúng file đã nạp vào collector. Không phải dữ liệu thu.</p>"
        + "".join(pages)
        + "</html>",
        "utf-8",
    )


if __name__ == "__main__":
    main()
