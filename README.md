# Turnwise

**Real-time turn-taking and barge-in for Vietnamese voice agents**
*Nhịp nói chuyện — trợ lý giọng nói có xử lý ngắt lời và chuyển lượt cho tổng đài tiếng Việt*

Turnwise predicts when a caller has finished speaking, instead of waiting out a fixed silence
threshold, and lets the caller interrupt the bot mid-sentence. It targets a Vietnamese customer
service call centre, and it is built as a research project: the method is chosen from measurements,
not assumed.

> **Status: scaffolding.** Tooling, conventions and the specification are in place. The pipeline
> itself is not implemented yet. Nothing here has been measured — every number in this repository
> must come from a run, never from another paper.

## Why

A fixed silence threshold cannot work, because *thinking* and *finished* sound identical on the
amplitude axis. Lower the threshold and the bot cuts callers off mid-sentence; raise it and every
short answer costs an extra 700 ms. No single value avoids both. `SPEC.md` §1 states the problem
in full.

Vietnamese adds a twist that English endpointers do not face: F0 already carries lexical tone, so
the falling final pitch that signals end-of-turn in English is not available in the same way.
Whether this changes what an endpointer should listen to is the open question this project tests.

## Getting started

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+. There is no task runner to install.

```bash
uv sync                    # create .venv and install dependencies
uv run pre-commit install  # install git hooks, once per clone
cp .env.example .env       # PowerShell: Copy-Item .env.example .env
```

Common commands:

```bash
uv run pytest                     # test suite
uv run pytest -m latency          # latency budget on the live path
uv run pytest -m scenario         # deterministic scenario replay, no microphone
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Optional dependency groups, installed on demand: `uv sync --extra asr | tts | transport | research`.
The `research` extra pulls torch and is only used offline by `training/` and `evaluation/`.

`data/`, `models/` and `reports/` are not in git and are not created by setup; the code that writes
into them creates them on first use.

On Windows, prefer an audio device on the WASAPI host API; MME and DirectSound add buffering that
will not appear in unit tests but will break the latency budget. List devices with:

```bash
uv run python -c "import sounddevice; print(sounddevice.query_devices())"
```

## Documentation

| File | What it holds |
|---|---|
| `SPEC.md` | The problem, business rules, requirements and acceptance criteria. Read before changing scope. |
| `AGENTS.md` | How to build: commands, layer boundaries, conventions, pitfalls. |
| `PROJECT-STRUCTURE.md` | Repository layout and the reasoning behind it. |
| `docs/roadmap.md` | Phase order and why: what to build first, what blocks what, where the project is most likely to die. |
| `docs/adr/` | Method and architecture decisions, with the alternatives that were rejected. |
| `docs/runbook/` | Operational procedures: data collection, running an evaluation. |

## Architecture

Four layers, one-way dependencies, each ignorant of the layer above it.

```
audio  →  turn  →  dialog
   ↘        ↓        ↙
        telemetry
```

`audio` turns a device stream into feature frames. `turn` scores those frames and decides hold,
take or backchannel — every scorer may answer "no opinion" rather than guess. `dialog` runs the
five business flows. `telemetry` records every decision and never feeds back into the pipeline.

## Data and evaluation

All data is consented role-play. No real customer recordings from any company are used, and NetCo
is a fictional operator invented as business context.

`data/holdout/` is locked: no training or tuning script may read it, and CI enforces this. Results
are reported as a trade-off curve against three baselines (`SPEC.md` R8, `docs/adr/0002`) — an
interruption rate without its latency, or the reverse, is not a result.
