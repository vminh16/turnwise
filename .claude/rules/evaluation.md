---
paths:
  - "evaluation/**"
  - "reports/**"
  - "configs/baseline/**"
---

# Evaluation rules

The only place allowed to read `data/holdout/`, and only when producing the final report. Open
it once. Every intermediate decision uses the validation split instead.

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

All three run on the same ASR, TTS and scenarios as the system, switched by config alone. B3's
numbers are meaningless without the ASR latency that fed it — report them together.

Model names and versions belong in `docs/adr/`, not in `SPEC.md` and not hardcoded here.

## The headline metric

Error rate split by the lexical tone of the final syllable (SPEC §9.1). Every other number is
context for this one. It requires the per-decision tone label recorded by `telemetry.collector`,
so an evaluation run against telemetry that lacks tone labels is incomplete, not partial.

## Numbers, not prose

A metric-affecting change carries before/after numbers in the commit body. Baseline values are
measured in Giai đoạn 0 and never filled in from another paper.
