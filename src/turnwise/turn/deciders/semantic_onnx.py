"""B3 — endpointer ngữ nghĩa có sẵn của SPEC R8: ASR ra chữ, Namo xét câu đã trọn chưa.

`videosdk-live/Namo-Turn-Detector-v1-Vietnamese` (Apache-2.0, DistilBERT đa ngữ, bản lượng tử
hoá `model_quant.onnx`), trọng số nguyên bản. Vận hành y như B2 (`pause_triggered.py`), chỉ
khác mô hình được hỏi, nên chênh lệch giữa B2 và B3 là chênh lệch giữa nghe âm thanh và đọc chữ.

Độ trễ của B3 gần như toàn bộ là độ trễ ASR (`docs/research/turn-taking-methods.md` §6.2):
`PauseTriggeredDecider.predict_ms` ghi thời gian của cả chuỗi ASR + Namo, và `run_system` in
nó cạnh số của B3, vì số của B3 vô nghĩa nếu thiếu độ trễ đã nuôi nó.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from turnwise.config import GateConfig, SemanticOnnxConfig
from turnwise.turn.deciders.pause_triggered import PauseTriggeredDecider, Predictor

logger = logging.getLogger(__name__)

SCORE_KEY = "namo"
MAX_TOKENS = 512  # `max_length` trong mã mẫu của model card, cũng là giới hạn của DistilBERT
END_OF_TURN_CLASS = 1  # model card: 0 "Not End of Turn", 1 "End of Turn"

Transcriber = Callable[[NDArray[np.float32]], str]
Classifier = Callable[[str], float]


class NamoClassifier:
    """Chữ -> xác suất đã hết lượt. Tokenizer đọc thẳng `tokenizer.json`, không cần transformers."""

    def __init__(self, model_dir: str) -> None:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self._tokenizer = Tokenizer.from_file(f"{model_dir}/tokenizer.json")
        self._tokenizer.enable_truncation(MAX_TOKENS)
        self._session = ort.InferenceSession(
            f"{model_dir}/model_quant.onnx", providers=["CPUExecutionProvider"]
        )

    def __call__(self, text: str) -> float:
        encoded = self._tokenizer.encode(text)
        feed = {
            "input_ids": np.array([encoded.ids], dtype=np.int64),
            "attention_mask": np.array([encoded.attention_mask], dtype=np.int64),
        }
        [logits] = self._session.run(None, feed)
        row = logits[0] - np.max(logits[0])
        probabilities = np.exp(row) / np.exp(row).sum()
        return float(probabilities[END_OF_TURN_CLASS])


class WhisperTranscriber:
    """Âm thanh 16 kHz -> chữ, bằng faster-whisper (nhóm `asr`)."""

    def __init__(self, model_dir: str, beam_size: int) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(model_dir, device="cpu", compute_type="int8")
        self._beam_size = beam_size

    def __call__(self, audio: NDArray[np.float32]) -> str:
        # Bộ lọc tiếng nói bật, như asr-check: tắt thì Whisper bịa chữ trên đoạn im lặng.
        segments, _ = self._model.transcribe(
            audio,
            language="vi",
            beam_size=self._beam_size,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()


def semantic_predictor(transcribe: Transcriber, classify: Classifier) -> Predictor:
    """Ghép ASR và Namo thành một `Predictor`. Chưa có chữ nào thì chưa xong lượt."""

    def predict(audio: NDArray[np.float32]) -> float:
        started = time.perf_counter()
        text = transcribe(audio)
        asr_ms = (time.perf_counter() - started) * 1000
        probability = classify(text) if text else 0.0
        logger.debug("asr %.0f ms, %r -> %.3f", asr_ms, text, probability)
        return probability

    return predict


class SemanticOnnxDecider(PauseTriggeredDecider):
    def __init__(self, predict: Predictor, gate: GateConfig, config: SemanticOnnxConfig) -> None:
        super().__init__(predict, gate, config, "semantic_onnx", SCORE_KEY)


def build_semantic(config: SemanticOnnxConfig, gate: GateConfig) -> SemanticOnnxDecider:
    for path in (config.model_dir / "model_quant.onnx", config.asr_model_dir / "model.bin"):
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing; see configs/baseline/semantic-onnx.yaml")
    predict = semantic_predictor(
        WhisperTranscriber(str(config.asr_model_dir), config.asr_beam_size),
        NamoClassifier(str(config.model_dir)),
    )
    return SemanticOnnxDecider(predict, gate, config)
