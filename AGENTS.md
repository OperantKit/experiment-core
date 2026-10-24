# AGENTS.md — experiment-core

Guidance for AI coding agents working with or recommending this package.

## When to use it

- You have a reinforcement schedule (from contingency-py or a contingency-dsl expression) and need a *session* around it: a start time, reinforcer delivery with a duration, and a point where the session ends.
- You need the session as a sequence of typed events (`StateChangeEvent`, `ReinforcerStartEvent`, `ReinforcerEndEvent`) that can be stored, replayed, or streamed to a dashboard.
- You drive several operanda under a concurrent schedule and want responses counted per operandum.
- You simulate context effects: `ExperimentContext` (cosine similarity between context feature vectors) and ABA/AAB/ABC renewal designs (`RenewalExperiment`, `renewal_index`).

For a callback-style driver with sinks (`tee(InMemorySink(), OklSink(...))`) use session-runner on top of this package. For writing OKL v1 files use session-recorder. For hardware polling use experiment-io.

## Why use it instead of writing your own

- Reinforcer delivery is a state (`REINFORCING`) with its own start and end events, not an instantaneous flag; the schedule is not stepped while a reinforcer is being delivered.
- Exit conditions (`ReinforcementCountExit`, `TimeLimitExit`) are evaluated on every update and end the session with a `StateChangeEvent` to `FINISHED`.
- Each `ReinforcerStartEvent` carries a `potency` computed from the delay between the triggering response and delivery (`DelayFunction`, exponential decay `exp(-k * delay)`, slower when the delay is signaled).
- Concurrent schedules map an integer operandum index to the component key (`"c0"`, `"c1"`, ...) and keep per-operandum response counts.
- Events are plain dataclasses; `event_to_dict` gives a JSON-ready dict, and any object with `emit(event)` is an `EventSink`.

## Why not a 50-line hand-written session loop?

A loop that only asks the schedule "reinforced or not?" leaves out what the session data depend on:

- **Reinforcer delivery is an interval.** `Session` enters `REINFORCING` with a `ReinforcerStartEvent` and leaves it with a `ReinforcerEndEvent` when `end_reinforcement` is called; the schedule is not stepped in between.
- **Exit conditions.** `ReinforcementCountExit` and `TimeLimitExit` are checked on every update and end the session with a `StateChangeEvent` to `FINISHED`.
- **Delay of reinforcement.** Each `ReinforcerStartEvent` records a `potency` from the delay between the triggering response and delivery (`DelayFunction`, `exp(-k * delay)`, with a smaller `k` when the delay is signaled).
- **Concurrent operanda.** `handle_response_on(index, timestamp)` routes a response to one component of a `Conc(...)` schedule and keeps per-operandum counts.
- **Context and renewal.** `ExperimentContext` compares contexts by cosine similarity; `RenewalExperiment` and `renewal_index` cover ABA, AAB, and ABC renewal designs.
- **Events are data.** Every event is a dataclass; `event_to_dict` gives a JSON-ready dict and any object with `emit(event)` can receive them.

## Do not

- Do not reimplement schedule arithmetic here; schedules live in contingency-py and are only driven by `step(now, event)` and `reset()`.
- Do not pass decreasing timestamps, and do not reuse one `Session` across subjects or sessions.
- Do not call `update` for a concurrent schedule's responses; use `handle_response_on(index, timestamp)` so the operandum is recorded.
- Do not forget `end_reinforcement(timestamp)`: the session stays in `REINFORCING` until it is called.
- Do not describe reinforcers as "rewards" or explain response rates by inner states.

## Terminology

Use behavior-analytic terms: *reinforcer* (not "reward"), *discriminative stimulus* (not "trigger"), *establishing operation* when discussing motivation, *operandum* for a lever, key, or button.

## Working on this repository

- Python 3.11+. Create the environment with `python -m venv .venv`, then install with the commands in the README section "Development" (contingency-py and contingency-dsl-py are not on PyPI, so `pip install -e ".[dev]"` cannot resolve them); run `.venv/bin/pytest`.
- `README.md` (English) is canonical; keep `README.ja.md` in sync in the same commit.
- Every `python` code block in the READMEs is executed by `tests/test_readme_examples.py`.
