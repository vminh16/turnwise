---
paths:
  - "src/turnwise/audio/**"
  - "tests/latency/**"
---

# Audio layer rules

This layer knows nothing about conversation. It turns a device stream into evenly spaced
feature frames, and nothing else.

## The callback is sacred

The `sounddevice` callback runs on a real-time thread owned by PortAudio. Inside it:

- Push frames into the ring buffer. That is the whole job.
- No inference, no allocation, no logging, no locks, no file I/O, no `numpy` operations that
  allocate. Preallocate every array at construction time.
- No exceptions. An exception in the callback kills the stream silently on some backends.

Everything else runs on a consumer thread reading from the ring buffer.

## Buffer discipline

- The ring buffer is fixed-size and preallocated. It never grows.
- Overrun is a real condition, not an assertion: count it, report it through
  `telemetry.collector`, and keep running. A dropped frame is better than a stalled stream.
- Frame size and sample rate come from `configs/`, never from a literal in this directory.

## Latency budget

- Any change here requires `uv run pytest -m latency` to pass before it is done.
- The budget is per frame and lives in `configs/default.yaml`. Do not relax the budget to make
  a test pass. If the budget is wrong, that is an ADR, not an edit.
- Timing measured by reading a wav file is not latency. Only the live path counts.

## Echo cancellation

- AEC runs through `aec_audio_processing.AudioProcessor`. It needs both the near-end (mic) and
  far-end (what the bot is about to play) streams, aligned in time.
- If the bot stops speaking the instant it starts, the bug is here, not in the turn scorers.
  Check AEC before debugging any model. SPEC R5 depends entirely on this layer.
- Never write audio to disk on the runtime path, not even for debugging. Use the ring buffer
  and telemetry counters instead.

## Windows notes

- Prefer a WASAPI device. MME and DirectSound add tens of milliseconds of buffering that will
  not show up in any unit test but will show up in the latency budget.
- List devices with:
  `uv run python -c "import sounddevice; print(sounddevice.query_devices())"`
