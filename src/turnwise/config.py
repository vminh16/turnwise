"""Nạp cấu hình cho toàn bộ Turnwise.

Đây là nơi **duy nhất** đọc YAML và biến môi trường. Không tầng nào khác được mở
`configs/` hay chạm `os.environ` — AGENTS.md đặt ra ràng buộc đó để mọi hằng số có
đúng một đường đi vào chương trình, và để một lần chạy tái dựng được từ một file.

Ba lớp, ưu tiên tăng dần:

1. `configs/default.yaml` — nguồn sự thật, luôn được nạp.
2. File overlay chọn bằng `TURNWISE_CONFIG` — gộp sâu lên lớp 1, nên một overlay chỉ
   cần ghi những khoá nó đổi (`configs/baseline/silence-threshold.yaml` đổi đúng một
   khoá `turn.decider`, phần `audio` vẫn nguyên).
3. Biến môi trường phẳng liệt kê ở `.env.example`.

Tên biến môi trường cố tình **phẳng** (`TURNWISE_LOG_LEVEL`) chứ không lồng theo dấu
phân cách của pydantic-settings (`TURNWISE_LOGGING__LEVEL`): `.env.example` đã commit
theo dạng phẳng, và người vận hành đọc file đó chứ không đọc file này. Ánh xạ nằm ở
`_ENV_OVERRIDES`, tường minh và đếm được.

Mọi section đặt `extra="forbid"`. Một khoá gõ sai trong YAML phải nổ ngay lúc nạp; nếu
nó bị bỏ qua trong im lặng thì thí nghiệm chạy với giá trị mặc định trong khi người chạy
tin rằng mình đã đổi tham số — sai lệch không để lại dấu vết nào trong số đo.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG_PATH = _ROOT / "configs" / "default.yaml"
"""Lớp nền, luôn nạp trước mọi overlay."""

_ENV_OVERRIDES: dict[str, tuple[str, str]] = {
    "TURNWISE_LOG_LEVEL": ("logging", "level"),
    "TURNWISE_TELEMETRY_DIR": ("telemetry", "dir"),
    "TURNWISE_INPUT_DEVICE": ("audio", "input_device"),
    "TURNWISE_OUTPUT_DEVICE": ("audio", "output_device"),
}
"""Biến môi trường phẳng ở `.env.example` -> khoá lồng trong YAML."""


class _Section(BaseModel):
    """Nền chung: bất biến sau khi nạp, và không nhận khoá lạ."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AudioConfig(_Section):
    """Tham số của tầng `audio`. Xem chú thích trong `configs/default.yaml`."""

    sample_rate_hz: int = Field(gt=0)
    channels: int = Field(gt=0)
    recording_caller_channel: int = Field(ge=0, le=1)
    capture_frame_ms: int = Field(gt=0)
    feature_frame_ms: int = Field(gt=0)
    ring_buffer_ms: int = Field(gt=0)
    noise_window_s: float = Field(gt=0)
    noise_percentile: float = Field(gt=0, lt=100)
    preferred_host_api: str
    input_device: int | str | None = None
    output_device: int | str | None = None

    @model_validator(mode="after")
    def _feature_frame_is_whole_capture_frames(self) -> AudioConfig:
        """Khung đặc trưng gộp từ khung capture, nên phải chia hết.

        Không chia hết thì mỗi khung đặc trưng lệch một phần khung capture, và độ lệch
        đó cộng dồn theo thời gian — mốc thời gian trong telemetry trôi dần mà không có
        gì báo.
        """
        if self.feature_frame_ms % self.capture_frame_ms:
            raise ValueError(
                f"feature_frame_ms={self.feature_frame_ms} không chia hết cho "
                f"capture_frame_ms={self.capture_frame_ms}"
            )
        return self


class EchoCancellationConfig(_Section):
    """SPEC R5 phụ thuộc hoàn toàn vào tầng này."""

    enabled: bool
    noise_suppression: bool
    noise_suppression_level: int
    automatic_gain_control: bool


class LatencyConfig(_Section):
    budget_per_frame_ms: float = Field(gt=0)


class DecisionConfig(_Section):
    """Ngưỡng quyết định. `None` cho tới khi Giai đoạn 0 đo ra số thật.

    Hai khoá bắt buộc có mặt trong YAML, nhưng được phép để `null`: SPEC §9.1 cấm điền
    số đoán, còn xoá hẳn khoá đi thì người đọc config không biết là còn thiếu số.
    """

    take_threshold: float | None
    backchannel_threshold: float | None


class AcousticOnnxConfig(_Section):
    """B2: `smart-turn` chạy nguyên trọng số, vận hành như pipecat. Xem
    `configs/baseline/acoustic-onnx.yaml` cho nguồn của từng giá trị."""

    model_path: Path
    probability_threshold: float = Field(gt=0, lt=1)
    trigger_silence_ms: int = Field(gt=0)
    """Im lặng sau tiếng nói bao lâu thì chạy mô hình (VAD `stop_secs` của pipecat)."""

    fallback_silence_ms: int = Field(gt=0)
    """Im lặng bao lâu thì nhận lượt dù mô hình nói chưa xong (`SmartTurnParams.stop_secs`)."""

    pre_speech_ms: int = Field(ge=0)
    window_s: int = Field(gt=0)

    @field_validator("model_path")
    @classmethod
    def _from_repo_root(cls, path: Path) -> Path:
        """Đường dẫn tương đối tính từ gốc repo, không từ thư mục đang đứng."""
        return _resolve(path)


class TurnConfig(_Section):
    decider: Literal["fused", "silence_threshold", "acoustic_onnx", "semantic_onnx"]
    scorers: list[str]
    decision: DecisionConfig
    silence_threshold_sweep_ms: list[int] | None = None
    """Chỉ overlay B1 đặt khoá này. Mỗi giá trị là một lần chạy riêng, cho một điểm
    trên đường cong đánh đổi (SPEC §9.3 quy tắc 2)."""

    silence_floor_dbfs: float | None = None
    """Cũng chỉ overlay B1 đặt. Ngưỡng năng lượng chia có tiếng với im lặng."""

    silence_threshold_ms: int | None = None
    """Ngưỡng im lặng của **một** lần chạy B1.

    Dải quét ở trên liệt kê các giá trị; mỗi lần chạy lấy đúng một giá trị vào đây.
    Có trường này thì một lần chạy được mô tả trọn vẹn bằng cấu hình, và `deciders.build()`
    dựng được adapter mà không cần ai truyền tham số riêng bên cạnh config.
    """

    acoustic_onnx: AcousticOnnxConfig | None = None
    """Chỉ overlay B2 đặt. Cổng im lặng dùng chung `silence_floor_dbfs` với B1."""


class TelemetryConfig(_Section):
    dir: Path
    enabled: bool


class LoggingConfig(_Section):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class AnnotationConfig(_Section):
    """Pha 1.6: bản nháp máy sinh cho người gán nhãn (`docs/annotation-guide.md` §4.1).

    Chỉ `evaluation/annotation.py` dùng; đường chạy chính không đọc section này.
    """

    vad_frame_ms: int = Field(gt=0)
    vad_floor_dbfs: float
    """Ngưỡng thấp nhất. Ngưỡng thật của mỗi bản là max(ngưỡng này, nền ồn + `vad_margin_db`)."""

    vad_margin_db: float = Field(gt=0)
    ipu_merge_ms: int = Field(ge=0)
    ipu_min_ms: int = Field(ge=0)
    asr_model_dir: Path

    @field_validator("asr_model_dir")
    @classmethod
    def _from_repo_root(cls, path: Path) -> Path:
        return _resolve(path)


class Settings(BaseSettings):
    """Toàn bộ cấu hình của một lần chạy, đã gộp đủ ba lớp."""

    model_config = SettingsConfigDict(env_prefix="TURNWISE_", extra="ignore", frozen=True)

    audio: AudioConfig
    echo_cancellation: EchoCancellationConfig
    latency: LatencyConfig
    turn: TurnConfig
    telemetry: TelemetryConfig
    logging: LoggingConfig
    annotation: AnnotationConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} không phải một ánh xạ YAML")
    return parsed


def _merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Gộp sâu overlay lên base. Overlay chỉ ghi đè khoá nó nêu tên."""
    merged = dict(base)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key] = _merge(current, value)
        else:
            merged[key] = value
    return merged


def _environment() -> dict[str, str]:
    """Biến từ `.env` (nếu có), rồi biến của tiến trình đè lên."""
    env = {key: value for key, value in dotenv_values(_ROOT / ".env").items() if value is not None}
    env.update(os.environ)
    return env


def _apply_env_overrides(data: dict[str, Any], env: Mapping[str, str]) -> None:
    for name, (section, key) in _ENV_OVERRIDES.items():
        raw = env.get(name)
        if raw is None:
            continue
        # Chuỗi rỗng nghĩa là "dùng mặc định của hệ điều hành", theo .env.example.
        data.setdefault(section, {})[key] = raw.strip() or None


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else _ROOT / candidate


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Nạp cấu hình: `default.yaml`, rồi overlay, rồi biến môi trường.

    `config_path` để trống thì lấy `TURNWISE_CONFIG`, và trống nữa thì chỉ dùng
    `default.yaml`. Đường dẫn tương đối tính từ gốc repo chứ không từ thư mục hiện
    hành, để một lần chạy cho cùng kết quả bất kể đứng ở đâu khi gõ lệnh.
    """
    env = _environment()
    selected = _resolve(config_path or env.get("TURNWISE_CONFIG") or DEFAULT_CONFIG_PATH)

    data = _read_yaml(DEFAULT_CONFIG_PATH)
    if selected != DEFAULT_CONFIG_PATH:
        data = _merge(data, _read_yaml(selected))
    _apply_env_overrides(data, env)

    return Settings(**data)
