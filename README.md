# experiment-core

:jp: [日本語版 README](README.ja.md)

Experimental orchestration core for operantkit.

## Role

Session lifecycle management, experimental context (Bouton's background stimuli), and renewal paradigms (ABA/AAB/ABC). This package is the runtime orchestrator that turns a declarative `contingency-dsl` program into a live session: it decides when to deliver reinforcers, tracks response events, and manages context-dependent phase transitions.

## Responsibilities

- **Session**: Lifecycle (IDLE → RUNNING → REINFORCING → FINISHED), event log, exit conditions, concurrent (multi-operandum) support, delay-of-reinforcement potency calculation.
- **ExperimentContext**: Bouton-style contextual stimuli that gate or modulate contingencies (background cues, situational sets).
- **Renewal**: ABA/AAB/ABC context-dependent recovery paradigms (Bouton & Bolles, 1979; Bouton, 2004).
- **Virtual clock hook**: Deterministic time source abstraction so simulations need not wait in real time.

## Not responsibilities

- Schedule algorithms themselves (live in `contingency` / `contingency-py`).
- Stimulus metadata (lives in `contingency-dsl-py`).
- Event persistence / JSONL logging (lives in `session-recorder`).
- UI, hardware bridging (live in `experiment-io`, `operantkit-frontend`).

## Architecture

```
                         ┌──────────────────────────┐
                         │     experiment-core      │
                         │  ┌────────────────────┐  │
                         │  │ Session            │  │
                         │  │ ExperimentContext  │  │
                         │  │ Renewal            │  │
                         │  └─────────┬──────────┘  │
                         └────────────┼─────────────┘
                    depends on (via Protocol)
                                      │
                ┌─────────────────────┼──────────────────────┐
                ▼                     ▼                      ▼
    Schedule runtime      contingency-dsl-py AST    stimulus metadata
    (contingency, ext.)   (program → runtime)       (contingency-dsl-py)
```

`experiment_core.Schedule` is an alias of `contingency.Schedule`; this package does not declare its own schedule interface. `Session` drives schedules through `step(now, event)` and `reset()`. Concurrent schedules are `contingency.Concurrent` instances whose `components` keys name the operanda; `Session.handle_response_on(index, timestamp)` maps an integer operandum index to the matching component key.

## Installation

```bash
pip install experiment-core
```

For development:

```bash
mise exec -- python -m venv .venv
mise exec -- .venv/bin/python -m pip install -e '.[dev]'
```

## Development

```bash
.venv/bin/pytest
.venv/bin/pytest --cov=src --cov-report=term-missing
.venv/bin/ruff check src tests
.venv/bin/black src tests
```

## Scope

This package owns:

| Module | Exports |
|---|---|
| `session` | `Session` |
| `context` | `ExperimentContext` |
| `renewal` | `RenewalParadigm`, `ContextualSession`, `RenewalExperiment`, `PhaseRecord`, `PhaseResult`, `renewal_index` |
| `events` | `SessionState`, `ResponseEvent`, `ReinforcerStartEvent`, `ReinforcerEndEvent`, `StateChangeEvent`, `SessionEvent` |
| `exit_condition` | `ExitCondition`, `ReinforcementCountExit`, `TimeLimitExit` |
| `observation` | `Observation` |
| `delay` | `DelayFunction` |
| `protocols` | `Schedule` (alias of `contingency.Schedule`) |
| `clock` | `Clock`, `VirtualClock`, `RealtimeClock` |
| `sink` | `EventSink`, `InMemorySink`, `event_to_dict` |

Explicit non-goals (belong to other packages or the next design round):

- Experiment protocol loader (YAML/JSON → runtime graph) and `ExperimentCore` façade — deferred to a higher-level orchestrator package. The v0 `ExperimentCore` / `ExecutionEnvironmentAdapter` / `DataManager` abstractions are **not ported**; they were scaffolding for a simulator-oriented v0 workflow and do not fit the Protocol-boundary model adopted here.
- Persistence / JSONL logging — `session-recorder` consumes `SessionEvent` via :class:`EventSink`.
- Concrete reinforcement schedules — `contingency-py` (`contingency.ScheduleBuilder`).
- Stimulus / reinforcer metadata — `contingency-dsl-py`.
- Hardware I/O — `experiment-io`.

## References

- Bouton, M. E., & Bolles, R. C. (1979). Contextual control of the extinction of conditioned fear. *Learning and Motivation*, 10(4), 445–466. https://doi.org/10.1016/0023-9690(79)90057-2
- Bouton, M. E. (2004). Context and behavioral processes in extinction. *Learning & Memory*, 11(5), 485–494. https://doi.org/10.1101/lm.78804
- Nevin, J. A. (1992). An integrative model for the study of behavioral momentum. *Journal of the Experimental Analysis of Behavior*, 57(3), 301–316. https://doi.org/10.1901/jeab.1992.57-301
