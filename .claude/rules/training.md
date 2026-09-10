---
paths:
  - "training/**"
  - "notebooks/**"
---

# Training rules

Offline code. It may import `src/turnwise`; `src/turnwise` must never import it.

## The holdout is locked

`data/holdout/` must not be read here. Not for a sanity check, not for "just looking at one
file", not for early stopping. Only `evaluation/` may read it, and only when producing the final
report. `.github/workflows/holdout-guard.yml` fails the build if this directory references that
path — treat a red build there as a correctness bug, never as a check to route around.

Model selection, early stopping and hyperparameter search use a validation split carved out of
`data/processed/`, never the holdout.

## Reproducibility

- Seed every source of randomness and record the seed in the run's output, not only in config.
- Every run writes: the config used, the git commit, the seed, the dataset manifest checksum.
  A checkpoint whose training config cannot be reconstructed is not a result.
- Checkpoints go to `models/checkpoints/` (gitignored) and are referenced from
  `data/manifests/` by sha256, never committed.
- Data is loaded through the manifests in `data/manifests/`. Do not glob `data/` directly; a
  glob silently changes meaning when files are added.

## Speaker discipline

Splits are by **speaker**, never by utterance. The same speaker appearing in train and
validation makes every number optimistic and the mistake is invisible in the metrics.

Normalise F0 per speaker before pooling, for the same reason as in `turn/`: pooled raw F0
teaches the model gender.

## Scope

- `training/` produces artefacts. It does not report results — that is `evaluation/`.
- Do not train ASR or TTS models. SPEC §11 puts both out of scope.
- Heavy dependencies live in the `research` extra (`uv sync --extra research`). Nothing in
  `training/` may be imported by the runtime path, so torch never reaches the laptop that runs
  the agent.
