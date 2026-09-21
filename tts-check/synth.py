"""Nghe thử và đo VieNeu-TTS v3 Turbo trên máy này. Chỉ để kiểm thử, không nối vào src/.

Chạy: `uv run python synth.py voices` để xem giọng preset,
      `uv run python synth.py bench --voice <tên> [--voice <tên> ...]` để sinh và đo.

Mô hình tải vào `models/` (gitignore). File nghe thử ghi vào `out/`: bản 48 kHz gốc và bản
16 kHz mono, đúng định dạng collector nhận cho giọng bot.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
os.environ.setdefault("HF_HOME", str(HERE / "models"))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import soxr  # noqa: E402

# Câu lấy nguyên từ roleplay/, dấu "/" (chỗ ngắt hơi cho người đọc) đổi thành dấu phẩy.
# Câu cuối cố ý viết bằng chữ số, như slot lúc chạy thật ở Giai đoạn 4, để thử bộ chuẩn hoá.
SENTENCES = {
    "1-so-thue-bao": "Em xin đọc lại: tám hai bốn / sáu một năm / ba chín không. Đúng không ạ?",
    "2-dieu-khoan": (
        "Em xin đọc điều khoản huỷ Gói Gia Đình. / Thuê bao đang trong thời gian cam kết mười hai "
        "tháng, / đã sử dụng bảy tháng. / Nếu huỷ trước hạn, / quý khách thanh toán phí huỷ bằng "
        "năm tháng cước còn lại, / tổng cộng một triệu hai trăm năm mươi nghìn đồng. / Modem cần "
        "hoàn trả trong vòng mười lăm ngày."
    ),
    "3-chu-so": (
        "Cước tháng 8 của quý khách là 344.000 đồng, hạn thanh toán ngày 25/9. "
        "Số thuê bao 0824615390."
    ),
}


def clean(text: str) -> str:
    out = []
    for part in (p.strip() for p in text.split("/")):
        if out and out[-1][-1] not in ".,;:?!":
            out[-1] += ","
        out.append(part)
    return " ".join(out)


def load(precision: str):  # type: ignore[no-untyped-def]
    from vieneu import Vieneu

    start = time.perf_counter()
    tts = Vieneu(mode="v3turbo", precision=precision)
    return tts, time.perf_counter() - start


def voices() -> None:
    tts, seconds = load("fp32")
    print(f"loaded in {seconds:.1f} s")
    for item in tts.list_preset_voices():
        print(item)


def bench(names: list[str], precisions: list[str], repeats: int) -> None:
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    for precision in precisions:
        tts, load_s = load(precision)
        print(f"\n== {precision}: load {load_s:.1f} s")
        tts.infer("Xin chào.", voice=names[0])  # warm-up, không tính
        for name in names:
            for key, raw in SENTENCES.items():
                text = clean(raw)
                compute, ttfa = [], []
                for _ in range(repeats):
                    start = time.perf_counter()
                    audio = tts.infer(text, voice=name)
                    compute.append(time.perf_counter() - start)
                    start = time.perf_counter()
                    first = None
                    for chunk in tts.infer_stream(text, voice=name):
                        if first is None and len(chunk):
                            first = time.perf_counter() - start
                    ttfa.append(first or float("nan"))
                seconds = len(audio) / tts.sample_rate
                rtf = float(np.median(compute)) / seconds
                print(
                    f"{name:>12} {key:<14} audio {seconds:5.2f} s  compute {np.median(compute):5.2f} s"
                    f"  RTF {rtf:4.2f}  TTFA {1000 * np.median(ttfa):4.0f} ms"
                )
                stem = f"{precision}-{name}-{key}"
                sf.write(out / f"{stem}-48k.wav", audio, tts.sample_rate, subtype="PCM_16")
                mono16 = soxr.resample(audio.astype(np.float32), tts.sample_rate, 16000)
                sf.write(out / f"{stem}-16k.wav", mono16, 16000, subtype="PCM_16")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("voices")
    run = sub.add_parser("bench")
    run.add_argument("--voice", action="append", required=True)
    run.add_argument("--precision", action="append", default=None)
    run.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.command == "voices":
        voices()
    else:
        bench(args.voice, args.precision or ["fp32", "int8"], args.repeats)


if __name__ == "__main__":
    main()
