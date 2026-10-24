# experiment-core

:jp: [日本語版 README](README.ja.md)

experiment-core puts a session around a reinforcement schedule: it starts the session, steps the schedule with each response, holds the session while a reinforcer is being delivered, ends the session when an exit condition is met, and records everything as typed events. It also models experimental contexts and ABA, AAB, and ABC renewal designs. Within [OperantKit](https://github.com/OperantKit) it sits between the schedule engine [contingency-py](https://github.com/OperantKit/contingency-py) and the session drivers and recorders ([session-runner](https://github.com/OperantKit/session-runner), [session-recorder](https://github.com/OperantKit/session-recorder)).

- **Reinforcer delivery takes time.** The session enters a reinforcing state with a start event and leaves it with an end event; responses during delivery do not advance the schedule.
- **Exit conditions** (a number of reinforcers, or a time limit) are checked on every update.
- **Every event is plain data** that can be written to a file, sent to a viewer, or checked in a test.

Notes for AI coding agents are in [AGENTS.md](AGENTS.md).

## Installation

Python 3.11 or newer. experiment-core is not on PyPI yet. Install it and the two packages it needs from GitHub without dependency resolution:

```bash
G=git+https://github.com/OperantKit
pip install --no-deps $G/contingency-dsl-py $G/contingency-py $G/experiment-core
```

`pip check` reports version mismatches between these development builds; they do not affect the example below.

## Example

Compile a [contingency-dsl](https://github.com/OperantKit/contingency-dsl) expression, run it as a session that ends after two reinforcers, and read the event log:

```python
from contingency_dsl import parse
from contingency import from_dsl
from experiment_core import ReinforcementCountExit, Session, SessionState, StateChangeEvent

session = Session(from_dsl(parse("FR 3")), exit_condition=ReinforcementCountExit(count=2))
session.start(0.0)
responses = 0
for t in range(1, 11):  # one response per second
    if session.state is SessionState.REINFORCING:
        session.end_reinforcement(float(t))  # 1-s reinforcer access ends
        continue
    responses += 1
    session.update(float(t), responses)

print(session.state.name, session.reinforcement_count)  # FINISHED 2
print([(type(e).__name__, e.timestamp) for e in session.events if not isinstance(e, StateChangeEvent)])
# [('ReinforcerStartEvent', 3.0), ('ReinforcerEndEvent', 4.0),
#  ('ReinforcerStartEvent', 7.0), ('ReinforcerEndEvent', 8.0)]
```

To send the same events to a file or a live viewer as they happen, drive the session with [session-runner](https://github.com/OperantKit/session-runner).

## What is included

| Module | What it does | Exports |
|---|---|---|
| `session` | The session: states IDLE → RUNNING → REINFORCING → FINISHED, the event log, per-operandum counts under concurrent schedules (`handle_response_on(index, timestamp)`), reinforcement rate, and behavioral momentum as reinforcement rate raised to a sensitivity exponent (Nevin, 1992) | `Session` |
| `delay` | The potency of a delayed reinforcer, `exp(-k * delay)`, with a smaller `k` when the delay is signaled; recorded on each `ReinforcerStartEvent` | `DelayFunction` |
| `exit_condition` | When the session ends | `ExitCondition`, `ReinforcementCountExit`, `TimeLimitExit` |
| `events` | Session states and events | `SessionState`, `ResponseEvent`, `ReinforcerStartEvent`, `ReinforcerEndEvent`, `StateChangeEvent`, `SessionEvent` |
| `sink` | Anything with `emit(event)` receives events; `event_to_dict` gives a JSON-ready dict | `EventSink`, `InMemorySink`, `event_to_dict` |
| `context` | An experimental context: the background stimuli as named feature intensities, compared by cosine similarity | `ExperimentContext` |
| `renewal` | ABA, AAB, and ABC renewal designs (Bouton & Bolles, 1979; Bouton, 2004) | `RenewalParadigm`, `ContextualSession`, `RenewalExperiment`, `PhaseRecord`, `PhaseResult`, `renewal_index` |
| `clock` | A virtual clock for simulations and a real-time clock | `Clock`, `VirtualClock`, `RealtimeClock` |
| `observation` | A snapshot of the session state (response counts, times since the last reinforcer) passed to schedule predicates | `Observation` |
| `protocols` | The schedule interface, an alias of `contingency.Schedule` | `Schedule` |

experiment-core does not implement schedules (they come from contingency-py), write log files (session-recorder), or talk to hardware ([experiment-io](https://github.com/OperantKit/experiment-io)).

## Limitations

- Not on PyPI yet, and the API can still change.
- `renewal_index` and `RenewalExperiment.predict_renewal` are computed from the similarity of the context feature vectors alone: `sim(test, acquisition) - sim(test, extinction)`. They are a model of the design, not a measure computed from response data.
- There is no loader for an experiment protocol written as a file; the session is built in Python.
- The schedule must receive non-decreasing timestamps, and one `Session` serves one subject in one session.

## Development

```bash
git clone https://github.com/OperantKit/experiment-core && cd experiment-core
python -m venv .venv
G=git+https://github.com/OperantKit
.venv/bin/python -m pip install --no-deps $G/contingency-dsl-py $G/contingency-py -e .
.venv/bin/python -m pip install pytest pytest-cov
.venv/bin/pytest
```

## References

- Bouton, M. E. (2004). Context and behavioral processes in extinction. *Learning & Memory*, 11(5), 485–494. https://doi.org/10.1101/lm.78804
- Bouton, M. E., & Bolles, R. C. (1979). Contextual control of the extinction of conditioned fear. *Learning and Motivation*, 10(4), 445–466. https://doi.org/10.1016/0023-9690(79)90057-2
- Nevin, J. A. (1992). An integrative model for the study of behavioral momentum. *Journal of the Experimental Analysis of Behavior*, 57(3), 301–316. https://doi.org/10.1901/jeab.1992.57-301

## License

MIT. See [LICENSE](LICENSE).
