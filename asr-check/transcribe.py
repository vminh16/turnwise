"""Chép lời bản ghi đã thu, **chỉ để kiểm thử** dữ liệu thu.

    uv run python transcribe.py <export.zip | file.wav> [...]

Dùng để nghe ngược xem một bản ghi thật sự chứa gì (người đọc giọng bot có đọc đúng câu
không, người thu có nói không). Đây **không** phải ASR của sản phẩm, **không** phải B3 của
`SPEC.md` R8, và **không** dùng để gán nhãn thay người. Việc chọn ASR cho các vai đó là quyết
định riêng, ở pha 1.6 và Giai đoạn 2.

Không sửa file nào: file thu giữ nguyên raw (`docs/progress.md` §6.6). Lúc chép lời có bật bộ
lọc tiếng nói có sẵn của `faster-whisper` (`vad_filter=True`), chỉ trong bộ nhớ, và mốc thời gian
in ra vẫn tính theo file gốc. Tắt bộ lọc thì Whisper bịa chữ trên đoạn im lặng: lần chạy đầu
trên một câu thật, nó trả về một câu quảng cáo YouTube không ai nói.

Mỗi đoạn in kèm `avg_logprob` và `no_speech_prob`. Đoạn ngắn, nhỏ tiếng hoặc lặp một từ nhiều
lần là dấu hiệu nên nghe lại bằng tai trước khi tin. Với file export: câu bot chép từ file giọng
bot, bản ghi chép từ **kênh khách** (kênh 0); kênh bot bỏ qua vì đã biết lời.

Mô hình: `Systran/faster-whisper-small`, giấy phép MIT, khoá ở revision dưới đây, tải về
`models/` trong thư mục này (gitignore).
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import yaml
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE / "models" / "faster-whisper-small"
MODEL_REPO = "Systran/faster-whisper-small"
MODEL_REVISION = "536b0662742c02347bc0e980a01041f333bce120"
ROLEPLAY_DIR = HERE.parent / "roleplay"
WHISPER_RATE = 16000


def pcm(data: bytes, channel: int) -> np.ndarray:
    """Một kênh của file WAV, hạ về 16 kHz cho Whisper. Collector lưu 48 kHz (raw)."""
    left, right = decode_audio(io.BytesIO(data), sampling_rate=WHISPER_RATE, split_stereo=True)
    return left if channel == 0 else right


def bot_lines() -> dict[str, str]:
    lines = {}
    for path in sorted(ROLEPLAY_DIR.glob("n[1-5]-*.yaml")):
        script = yaml.safe_load(path.read_text(encoding="utf-8"))
        for step, item in enumerate(script["steps"]):
            lines[f"{script['name']}/{step}"] = " ".join(item["bot"].split())
    return lines


def out(line: str) -> None:
    sys.stdout.write(line + "\n")


def show(model: WhisperModel, label: str, audio: np.ndarray, expected: str | None) -> None:
    segments, _ = model.transcribe(
        audio, language="vi", beam_size=5, vad_filter=True, condition_on_previous_text=False
    )
    out(f"\n== {label}  ({len(audio) / WHISPER_RATE:.2f}s)")
    if expected:
        out(f"   expected: {expected}")
    heard = False
    for segment in segments:
        heard = True
        out(
            f"   [{segment.start:6.2f} - {segment.end:6.2f}] {segment.text.strip()}"
            f"   (avg_logprob {segment.avg_logprob:.2f}, no_speech {segment.no_speech_prob:.2f})"
        )
    if not heard:
        out("   (no speech recognised)")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    if len(sys.argv) < 2:
        sys.stderr.write("usage: transcribe.py <export.zip | file.wav> [...]\n")
        return 2
    if not (MODEL_DIR / "model.bin").exists():
        sys.stderr.write(f"model missing: download {MODEL_REPO}@{MODEL_REVISION}\n")
        return 2
    model = WhisperModel(str(MODEL_DIR), device="cpu", compute_type="int8")
    expected = bot_lines()

    for argument in sys.argv[1:]:
        path = Path(argument)
        if path.suffix == ".wav":
            show(model, path.name, pcm(path.read_bytes(), 0), None)
            continue
        bundle = zipfile.ZipFile(path)
        for name in sorted(bundle.namelist()):
            if name.startswith("prompts/") and name.endswith(".wav"):
                key = name[len("prompts/") : -len(".wav")]
                show(model, f"bot prompt {key}", pcm(bundle.read(name), 0), expected.get(key))
            elif name.startswith("sessions/") and name.endswith(".wav"):
                sidecar = json.loads(bundle.read(name[: -len(".wav")] + ".json"))
                channel = sidecar["layout"]["caller_channel"]
                show(model, f"caller channel {name}", pcm(bundle.read(name), channel), None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
