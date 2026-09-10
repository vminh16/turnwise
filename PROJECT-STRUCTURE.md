# Turnwise — Repository Name and Structure

## Repository name

**`turnwise`**

One word, pronounceable, and it names the domain: turn-taking. The `-wise` suffix reads as *aware of*, which is exactly what the system is. It works unchanged at every level, which is the real test of a repo name:

| Where | Form |
|---|---|
| GitHub | `github.com/vminh16/turnwise` |
| Python package | `turnwise` |
| Module path | `src/turnwise/` |
| CLI | `turnwise dev`, `turnwise sim` |
| Container image | `turnwise:0.1.0` |

Full title for the README: **Turnwise — real-time turn-taking and barge-in for Vietnamese voice agents**

It follows the convention of the field, where production voice repos take short evocative single words rather than descriptions: `pipecat`, `moshi`, `vocode`, `piper`, `whisper`. Avoid a `vi-` prefix or a `-vietnamese` suffix; the README states the language, the name does not need to.

**Runners-up, if `turnwise` is taken:**
- `floorkeeper` — from *holding the floor*, the conversation-analysis term for having the turn. More evocative, less obvious.
- `interject` — names the barge-in half rather than the turn-taking half.

Avoid `cadence` (collides with Uber Cadence) and `duplex` (collides with Google Duplex).

---

## Structure

Modelled on production voice-agent repos — `pipecat-ai/pipecat` and `livekit-examples/agent-starter-python` — with the additions a research project needs.

```
turnwise/
├── .claude/
│   ├── rules/                      # path-scoped; loads only when Claude opens matching files
│   │   ├── audio.md                #   paths: src/turnwise/audio/**  — latency budget, buffer discipline
│   │   ├── turn.md                 #   paths: src/turnwise/turn/**   — scorer contract, abstain semantics
│   │   ├── training.md             #   paths: training/**            — seeds, checkpoints, reproducibility
│   │   └── evaluation.md           #   paths: evaluation/**          — locked holdout, reporting rules
│   ├── skills/                     # realtime-audio, turn-taking, scenario-authoring, experiment-hygiene
│   ├── agents/                     # subagent definitions, e.g. a reviewer that only reads diffs
│   └── settings.json               # permissions, hooks
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # lint + typecheck + unit tests
│   │   ├── sim.yml                 # scenario replay; deterministic, no microphone
│   │   ├── bench.yml               # latency regression gate
│   │   └── holdout-guard.yml       # fails if any training script references data/holdout/
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── configs/
│   ├── default.yaml                # single source of truth for every threshold
│   ├── baseline/
│   │   └── silence-threshold.yaml  # sweeps values; never selects one
│   ├── ablation/                   # one file per component switched off
│   └── deploy/
│       ├── local.yaml
│       └── container.yaml
│
├── scenarios/                      # conversation scripts replayed by `uv run pytest -m scenario`
│   ├── hesitation.yaml             # caller pauses mid-utterance reading an account number
│   ├── backchannel.yaml            # caller says "dạ" while the bot is speaking
│   ├── barge-in.yaml               # caller talks over the bot with real content
│   ├── agent-request.yaml          # "cho tôi gặp nhân viên" at an arbitrary point
│   └── short-answer.yaml           # two-word reply must not incur the full threshold
│
├── data/                           # gitignored except manifests/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   ├── holdout/                    # LOCKED — read only by evaluation/
│   └── manifests/                  # CHECKED IN: jsonl of path + sha256 + speaker + labels
│
├── docs/
│   ├── adr/
│   │   └── 0001-record-architecture-decisions.md
│   ├── runbook/
│   │   ├── collect-data.md
│   │   └── run-evaluation.md
│   └── annotation-guide.md         # label definitions + inter-annotator agreement protocol
│
├── models/                         # gitignored; referenced by checksum in manifests
│   ├── checkpoints/
│   └── exported/
│
├── notebooks/                      # exploration only; never imported by src/
│
├── examples/                       # minimal runnable snippets, one concern each
│   ├── minimal_agent.py
│   └── custom_scorer.py
│
├── scripts/                        # thin CLI wrappers; no logic
│   ├── collect_session.py
│   ├── validate_manifests.py
│   └── check_holdout_isolation.py  # used by holdout-guard.yml
│
├── src/turnwise/
│   ├── __init__.py
│   ├── agent.py                    # THE entrypoint; thin
│   ├── config.py                   # pydantic-settings; the only place YAML/env is read
│   ├── types.py                    # shared dataclasses and protocols
│   ├── audio/
│   │   ├── capture.py
│   │   ├── ring_buffer.py
│   │   ├── features.py
│   │   └── aec.py                  # echo cancellation — required for barge-in
│   ├── turn/
│   │   ├── base.py                 # scorer protocol; abstain is a first-class return value
│   │   ├── scorers/                # one module per signal source
│   │   └── fusion.py
│   ├── dialog/
│   │   ├── machine.py              # the five business flows
│   │   ├── slots.py
│   │   └── backend_stub.py
│   ├── telemetry/
│   │   ├── collector.py
│   │   └── dashboard.py
│   └── transport/
│       ├── webrtc.py
│       └── wiring.py
│
├── training/
│   ├── train.py
│   ├── datamodule.py
│   └── export.py
│
├── evaluation/
│   ├── run_baseline.py             # sweeps thresholds; never selects one
│   ├── run_system.py
│   ├── metrics.py
│   └── figures.py
│
├── reports/                        # gitignored; regenerated by evaluation/run_system.py
│
├── tests/
│   ├── unit/
│   ├── integration/                # layer boundaries: audio → turn → dialog
│   ├── latency/                    # budget assertions; run by `uv run pytest -m latency`
│   ├── scenarios/                  # asserts scenarios/*.yaml produce expected decisions
│   ├── fixtures/                   # tiny wav files, checked in
│   └── conftest.py
│
├── .dockerignore
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── AGENTS.md                       # shared agent guidance
├── CLAUDE.md                       # @AGENTS.md + Claude-specific rules
├── CHANGELOG.md
├── CONTRIBUTING.md
├── Dockerfile
├── LICENSE
├── README.md
├── SECURITY.md
├── SPEC.md
├── pyproject.toml                  # deps, ruff, mypy, pytest config in one file
└── uv.lock                         # committed
```

## What the real repos taught, and what changed because of it

**`scenarios/` — the most valuable addition.** LiveKit's starter ships `lk agent simulate --scenarios scenarios.yaml`. For a turn-taking project this is not a convenience, it is the primary test surface: the five demo cases in `SPEC.md` §10 become five YAML files that run deterministically in CI. You stop needing a microphone to know whether a change broke barge-in.

**`AGENTS.md` alongside `CLAUDE.md`.** Both pipecat and the LiveKit starter carry `AGENTS.md`, `CLAUDE.md`, and in LiveKit's case `GEMINI.md`. Claude Code reads `CLAUDE.md`, not `AGENTS.md`, so put shared guidance in `AGENTS.md` and start `CLAUDE.md` with `@AGENTS.md` followed by the Claude-specific parts. One source of truth, no drift between tools.

**`Dockerfile` and `.dockerignore`.** The LiveKit starter ships both. A voice agent that only runs on the author's laptop is not finished, and containerising early forces the dependency list to stay honest.

**`uv run` instead of a task runner.** Both real repos use Task or Make, but either one is a separate binary every contributor must install before the repo works at all. `uv` is already required for dependencies, and `uv run <cmd>` executes inside the project venv on every platform — including Windows, where Make's tab semantics and Task's Go binary are both friction. The command list lives in `AGENTS.md`; pytest markers (`latency`, `scenario`) carry the grouping that a task runner would otherwise provide.

**`examples/`.** Pipecat keeps one. Minimal runnable snippets, one concern each, are the cheapest documentation that cannot go stale — CI runs them.

**`.claude/skills/` checked in.** Both repos version their agent skills with the code. Conventions travel with the branch that changes them.

**`data/test/` renamed to `data/holdout/`.** `tests/` and `data/test/` in the same repo invite the exact confusion the lock is meant to prevent. `holdout` says what it is.

**`metrics/` renamed to `telemetry/`.** `metrics/` collided with `evaluation/metrics.py`. Runtime event collection and offline scoring are different jobs and should not share a name.

## Design decisions worth defending

**`src/` layout.** Without it, Python imports the working directory and tests silently pass against uninstalled code. With it, tests exercise what ships.

**Manifests checked in, data not.** JSONL with path, sha256, speaker id, and labels. The dataset stays out of git; reproducibility does not.

**Holdout isolation enforced by CI, not discipline.** `holdout-guard.yml` runs `check_holdout_isolation.py`, which scans training and tuning scripts for references to that path and fails the build. A rule in a document gets forgotten; a red build does not.

**`configs/baseline/` sweeps rather than selects.** The baseline is a curve, not a point. Encoding that in the layout makes the correct experiment the path of least resistance.

**`tests/latency/` separate from `tests/unit/`.** Latency assertions are slow and machine-dependent. Splitting them keeps the default `uv run pytest` fast and `uv run pytest -m latency` honest.

**`scripts/` holds no logic.** Every script is a thin argparse wrapper around something importable from `src/`. Logic in scripts cannot be tested.

**`docs/adr/`.** Method choices get recorded with context and trade-offs. Six weeks on, nobody remembers why an approach was rejected, and without a record it gets re-litigated.

## Scaffold

```bash
mkdir -p turnwise/{.claude/{rules,skills,agents},.github/{workflows,ISSUE_TEMPLATE}} \
         turnwise/configs/{baseline,ablation,deploy} \
         turnwise/{scenarios,notebooks,examples,scripts,reports} \
         turnwise/data/{raw,interim,processed,holdout,manifests} \
         turnwise/docs/{adr,runbook} \
         turnwise/models/{checkpoints,exported} \
         turnwise/src/turnwise/{audio,turn/scorers,dialog,telemetry,transport} \
         turnwise/{training,evaluation} \
         turnwise/tests/{unit,integration,latency,scenarios,fixtures}

cd turnwise && git init && uv init --lib --name turnwise
printf 'data/\n!data/manifests/\nmodels/\nreports/\n.venv/\n__pycache__/\n*.egg-info/\n' > .gitignore
```
