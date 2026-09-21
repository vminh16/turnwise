"""Sinh giọng bot cho mọi câu trong roleplay/ rồi nạp vào collector.

    COLLECTOR_ADMIN_TOKEN=... uv run python render_prompts.py [--url http://localhost:8000]

Danh sách câu lấy từ chính collector (`/api/admin/lines`), nên khớp đúng khoá mà người thu
sẽ nghe. Giọng đã chốt: VieNeu-TTS v3 Turbo, preset "Minh Quân Pro", int8, dấu "/" đổi thành
dấu phẩy (cách A: mô hình tự quyết độ dài khoảng nghỉ, giống lúc bot chạy thật).

Mô hình có yếu tố ngẫu nhiên: mỗi lần chạy ra cách đọc hơi khác. Câu nào nghe không ổn thì sinh
lại riêng câu đó bằng `--only <script>/<step>`, không cần sinh lại cả bộ. File sinh ra giữ ở
`prompts/` (gitignore) cùng `manifest.json` ghi giọng, phiên bản và sha256 từng câu.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from importlib.metadata import version
from pathlib import Path

HERE = Path(__file__).parent
os.environ.setdefault("HF_HOME", str(HERE / "models"))

import numpy as np  # noqa: E402
import requests  # noqa: E402
import soundfile as sf  # noqa: E402

VOICE = "Minh Quân Pro"
PRECISION = "int8"
MODEL = "pnnbao-ump/VieNeu-TTS-v3-Turbo"


def clean(text: str) -> str:
    """Dấu "/" là chỗ ngắt hơi cho người đọc; với TTS đổi thành dấu phẩy."""
    out: list[str] = []
    for part in (p.strip() for p in " ".join(text.split()).split("/")):
        if out and out[-1][-1] not in ".,;:?!":
            out[-1] += ","
        out.append(part)
    return " ".join(out)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--only", action="append", help="script/step, lặp lại được")
    args = parser.parse_args()
    headers = {"X-Admin-Token": os.environ["COLLECTOR_ADMIN_TOKEN"]}

    config = requests.get(f"{args.url}/api/admin/config", headers=headers, timeout=10)
    config.raise_for_status()
    lines = requests.get(f"{args.url}/api/admin/lines", headers=headers, timeout=10)
    lines.raise_for_status()
    wanted = [
        line
        for line in lines.json()
        if not args.only or f"{line['script']}/{line['step']}" in args.only
    ]

    from vieneu import Vieneu

    tts = Vieneu(mode="v3turbo", precision=PRECISION)
    if tts.sample_rate != config.json()["sample_rate_hz"]:
        raise SystemExit(f"TTS gives {tts.sample_rate} Hz, collector wants {config.json()}")

    out = HERE / "prompts"
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {}
    manifest.setdefault("lines", {})
    manifest.update(
        voice=VOICE, precision=PRECISION, model=MODEL, vieneu=version("vieneu"),
        sample_rate_hz=tts.sample_rate, watermark=True, pause_marker="comma",
    )
    for line in wanted:
        key = f"{line['script']}/{line['step']}"
        text = clean(line["bot"])
        start = time.perf_counter()
        audio = tts.infer(text, voice=VOICE)
        seconds = time.perf_counter() - start
        peak = float(np.abs(audio).max())
        if peak > 1.0:  # không chuẩn hoá âm lượng; chỉ tránh tràn khi đổi sang PCM16
            audio = audio / peak
        buffer = io.BytesIO()
        sf.write(buffer, audio, tts.sample_rate, format="WAV", subtype="PCM_16")
        data = buffer.getvalue()
        path = out / line["script"] / f"{line['step']}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        response = requests.post(
            f"{args.url}/api/admin/prompts",
            headers=headers,
            data={"script": line["script"], "step": str(line["step"])},
            files={"audio": ("prompt.wav", data, "audio/wav")},
            timeout=60,
        )
        response.raise_for_status()
        manifest["lines"][key] = {
            "text": text, "sha256": hashlib.sha256(data).hexdigest(),
            "seconds": round(len(audio) / tts.sample_rate, 2), "peak": round(peak, 3),
        }
        print(f"{key:<32} {len(audio) / tts.sample_rate:5.2f} s  (sinh {seconds:4.1f} s)  peak {peak:.2f}")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    print(f"{len(wanted)} câu đã nạp vào {args.url}")


if __name__ == "__main__":
    main()
