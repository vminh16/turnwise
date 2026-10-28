---
paths:
  - "evaluation/**"
  - "reports/**"
  - "configs/baseline/**"
---

# Evaluation rules

The only place allowed to read `data/holdout/`, and only when producing the final report. Open
it once. Every intermediate decision uses the validation split instead.

## Two datasets, never pooled

ADR-0007 splits the data by the question it answers:

- **Analysis set** — natural two-person Vietnamese conversation (`docs/research/analysis-corpus.md`).
  The headline metric and the tone- and region-split benchmark of every decider are computed here.
  Label every pause inside each sampled window; never select "interesting" moments. Normalise F0
  per speaker. Report by speaker-clustered statistics (mixed-effects model or bootstrap over
  speakers), not pooled counts.
- **Product test set** — the NetCo role-play calls, `scenarios/`, and the live tests of SPEC §10.
  Behaviour of the assistant: §4.3, R3, R5.

Never pool the two into one number, and never carry a conclusion from one set to the other without
saying so. Each set has its own holdout, split by speaker.

## Reporting rules, from SPEC §9.3

1. **Never report interruption rate without latency, or latency without interruption rate.**
   They trade off. A single number from one axis is not a result; the correct presentation is a
   trade-off curve.
2. **The silence-threshold baseline sweeps, it never selects.** `configs/baseline/` encodes a
   range of values on purpose. Reporting one tuned threshold invites "why not tune it better?";
   sweeping proves no threshold wins, which is the project's central claim.
3. **Ablation is mandatory.** Switch each component off through config and report its individual
   contribution. A component that cannot be switched off from config is a bug in `turn/`.
4. **Latency comes from the live path**, produced by `uv run pytest -m latency`. File-based
   timing omits buffering, TTS startup and network jitter.
5. **The holdout opens exactly once.**

## Three baselines, per SPEC R8 and ADR-0002

- **B1** silence threshold, swept.
- **B2** an existing open-source acoustic endpointer, weights unmodified.
- **B3** an existing open-source semantic endpointer over ASR text, weights unmodified.

All three are adapters in `src/turnwise/turn/deciders/`, alongside the proposed system. This
directory contains no decision path of its own: it selects a decider by config, runs it, and
scores the result. That is what makes "same ASR, TTS and scenarios" structurally true rather than
a promise.

B3's numbers are meaningless without the ASR latency that fed it — report them together.

Model names and versions belong in `docs/adr/`, not in `SPEC.md` and not hardcoded here.

## The headline metric

Error rate split by the lexical tone of the final syllable (SPEC §9.1). Every other number is
context for this one.

It matters because it is directional, not because it sounds academic: errors spread evenly point at
thresholds and dialogue flow, errors concentrated in a few tones name exactly what the adaptation
phase has to fix. A shipped assistant that fails on one tone fails for every caller whose account
number ends in it. It requires the per-decision tone label recorded by `telemetry.collector`,
so an evaluation run against telemetry that lacks tone labels is incomplete, not partial.

## Numbers, not prose

A metric-affecting change carries before/after numbers in the commit body. Baseline values are
measured in Giai đoạn 0 and never filled in from another paper.
