"""B2 — endpointer âm thanh có sẵn của SPEC R8: `smart-turn` v3.2, trọng số nguyên bản.

Mô hình nghe tối đa 8 giây cuối của lượt khách và trả về xác suất khách đã nói xong. Nó
không tự quyết khi nào được hỏi: pipecat hỏi nó mỗi khi VAD thấy khách im 200 ms, và
vẫn nhận lượt sau 3 giây im dù mô hình nói chưa xong. Adapter này chép đúng cách vận
hành đó, vì một baseline chạy khác cách người ta dùng nó thì không còn là baseline ấy
nữa. Nguồn của từng giá trị nằm trong `configs/baseline/acoustic-onnx.yaml`.

Hai chỗ khác pipecat, cả hai có chủ ý:

- Cổng có tiếng / im lặng là cổng năng lượng của B1 chứ không phải Silero VAD, để B1 và
  B2 khác nhau ở đúng một chỗ: có mô hình hay không.
- Mô hình chạy ngay trong `decide()` ở khung chạm ngưỡng im lặng. Chạy lại một bản thu
  thì không sao; trên đường chạy sống, phần nối dây phải đẩy lời gọi này ra khỏi thread
  tiêu thụ, như pipecat đẩy sang executor, nếu không nó phá ngân sách mỗi khung.

Giống B1, B2 **không bao giờ** trả `BACKCHANNEL`: smart-turn chỉ trả lời "xong chưa".
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from turnwise.config import AcousticOnnxConfig
from turnwise.turn.deciders.silence_threshold import rms_dbfs
from turnwise.types import FeatureFrame, TurnDecision, TurnOutcome

logger = logging.getLogger(__name__)

# Hợp đồng đầu vào của mô hình, không phải tham số để chỉnh: smart-turn học trên đặc trưng
# log-mel của Whisper (`WhisperFeatureExtractor(chunk_length=8)` trong inference.py).
MODEL_RATE_HZ = 16_000
MEL_BANDS = 80
NORMALISE_EPSILON = 1e-7  # `zero_mean_unit_var_norm` của transformers, `do_normalize=True`

SCORE_KEY = "smart_turn"

Predictor = Callable[[NDArray[np.float32]], float]
"""Âm thanh 16 kHz mono của lượt đang xét -> xác suất khách đã nói xong."""


class SmartTurnModel:
    """Phiên ONNX cộng bước trích đặc trưng, cho ra một `Predictor`.

    Đặc trưng lấy từ `faster_whisper.feature_extractor`, cài qua nhóm `asr`. Đã đối chiếu
    với `transformers.WhisperFeatureExtractor` của bản gốc trên bốn đoạn của một bản thu
    thật (3 s, 8 s, 12 s, 0,6 s): lệch tối đa 4,3e-6.
    """

    def __init__(self, config: AcousticOnnxConfig) -> None:
        import onnxruntime as ort
        from faster_whisper.feature_extractor import FeatureExtractor

        if not config.model_path.exists():
            raise FileNotFoundError(
                f"{config.model_path} is missing; see configs/baseline/acoustic-onnx.yaml"
            )
        options = ort.SessionOptions()
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(
            str(config.model_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self._samples = config.window_s * MODEL_RATE_HZ
        self._features = FeatureExtractor(
            feature_size=MEL_BANDS, sampling_rate=MODEL_RATE_HZ, chunk_length=config.window_s
        )

    def features(self, audio: NDArray[np.float32]) -> NDArray[np.float32]:
        """Giữ `window_s` giây cuối, thiếu thì đệm 0 vào đầu, chuẩn hoá, rồi log-mel."""
        if len(audio) >= self._samples:
            window = audio[-self._samples :]
        else:
            window = np.pad(audio, (self._samples - len(audio), 0))
        window = (window - window.mean()) / np.sqrt(window.var() + NORMALISE_EPSILON)
        mel: NDArray[np.float32] = self._features(window.astype(np.float32), padding=0)
        return mel[np.newaxis].astype(np.float32)

    def __call__(self, audio: NDArray[np.float32]) -> float:
        [probability] = self._session.run(None, {"input_features": self.features(audio)})
        return float(probability[0][0])


class AcousticOnnxDecider:
    """Hỏi mô hình mỗi lần khách im đủ lâu; nhận lượt khi nó nói xong hoặc khi im quá lâu."""

    name = "acoustic_onnx"

    _speech_start: int | None
    _silence_ms: int
    _asked: bool
    _taken: bool

    def __init__(
        self, predict: Predictor, silence_floor_dbfs: float, config: AcousticOnnxConfig
    ) -> None:
        self._predict = predict
        self._floor_dbfs = silence_floor_dbfs
        self._config = config
        self._frames: deque[tuple[int, NDArray[np.float32]]] = deque()
        self.reset()

    def decide(self, frame: FeatureFrame) -> TurnDecision:
        scores: dict[str, float | None] = {}
        if not self._taken:
            samples = frame.samples[: len(frame.samples) - frame.padded_samples]
            self._check_rate(frame)
            self._remember(frame, samples)
            if len(samples) and rms_dbfs(samples) > self._floor_dbfs:
                if self._speech_start is None:
                    self._speech_start = frame.index
                self._silence_ms = 0
                self._asked = False
            elif self._speech_start is not None:
                self._silence_ms += round(frame.duration_s * 1000)
                if not self._asked and self._silence_ms >= self._config.trigger_silence_ms:
                    self._asked = True
                    probability = self._predict(self._segment(frame))
                    scores[SCORE_KEY] = probability
                    self._taken = probability > self._config.probability_threshold
                if self._silence_ms >= self._config.fallback_silence_ms:
                    self._taken = True
                if self._taken:
                    logger.debug("take at frame %d (%.3fs)", frame.index, frame.start_s)

        return TurnDecision(
            outcome=TurnOutcome.TAKE if self._taken else TurnOutcome.HOLD,
            decider=self.name,
            frame_index=frame.index,
            at_s=frame.start_s,
            scores=scores,
            final_tone=None,
        )

    def reset(self) -> None:
        self._frames.clear()
        self._speech_start = None
        self._silence_ms = 0
        self._asked = False
        self._taken = False

    def _check_rate(self, frame: FeatureFrame) -> None:
        rate = round(len(frame.samples) / frame.duration_s)
        if rate != MODEL_RATE_HZ:
            raise ValueError(f"smart-turn needs {MODEL_RATE_HZ} Hz frames, got {rate} Hz")

    def _remember(self, frame: FeatureFrame, samples: NDArray[np.float32]) -> None:
        """Giữ vừa đủ khung cho một cửa sổ, cộng phần trước lúc bắt đầu nói."""
        self._frames.append((frame.index, samples.copy()))  # khung có thể trỏ vào ring buffer
        keep_ms = self._config.pre_speech_ms
        if self._speech_start is not None:
            keep_ms += self._config.window_s * 1000
        keep = round(keep_ms / (frame.duration_s * 1000)) + 1
        while len(self._frames) > keep:
            self._frames.popleft()

    def _segment(self, frame: FeatureFrame) -> NDArray[np.float32]:
        """Từ `pre_speech_ms` trước lúc bắt đầu nói tới khung hiện tại."""
        assert self._speech_start is not None
        pre_frames = round(self._config.pre_speech_ms / (frame.duration_s * 1000))
        first = self._speech_start - pre_frames
        return np.concatenate([s for i, s in self._frames if i >= first])
