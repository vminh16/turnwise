---
paths:
  - "src/turnwise/turn/**"
  - "tests/unit/test_fusion*.py"
---

# Turn layer rules

Consumes feature frames, emits a turn decision: hold, take, or backchannel. It knows nothing
about business flows and nothing about which device produced the audio.

## The scorer contract

Every scorer implements the protocol in `base.py` and obeys three rules:

1. **Abstain is a first-class return value.** A scorer that has no opinion returns "no opinion",
   never a middling score. Fusion must be able to tell "0.5 confidence" apart from "I cannot
   judge this frame". SPEC §8 requires this; it is not a nicety.
2. **State resets between turns.** Every scorer exposes a reset, and fusion calls it on every
   turn boundary. Leaked state corrupts scores without crashing — the most expensive bug class
   in this project. A new scorer needs a test that asserts two identical inputs separated by a
   reset produce identical outputs.
3. **No hidden thresholds.** Every constant comes from `configs/`. A scorer that cannot be
   switched off from config cannot be ablated, and SPEC §9.3 requires ablation.

## Fusion

- Fusion combines scores; it does not compute them. If fusion needs a feature, the feature
  belongs in a scorer or in `audio/`.
- Abstaining scorers are excluded from the combination, not counted as zero.
- If every scorer abstains, fusion returns hold. Silence is not evidence of a finished turn.

## Telemetry

Every decision goes through `telemetry.collector` with a timestamp **and the per-scorer scores
that produced it**, including which scorers abstained. Without the per-scorer breakdown a wrong
decision cannot be attributed, and the ablation table cannot be built.

## F0 and Vietnamese tone

- Normalise F0 per speaker before pooling. Male ~100 Hz, female ~200 Hz; pooled raw values
  teach the model gender, not turn-taking.
- Observed F0 is lexical tone and utterance intonation superimposed. Treat separating them as
  the hypothesis under test (SPEC §7, ADR-0002), not as an established fact. A scorer that
  assumes a falling contour means end-of-turn is importing an English assumption.
- The final-syllable tone of every decision must be recoverable from telemetry, because
  per-tone error rate is the project's headline metric (SPEC §9.1).

## Cost

Inference never runs in the audio callback. This layer is called from the consumer thread, and
its per-frame cost is part of the latency budget checked by `uv run pytest -m latency`.
