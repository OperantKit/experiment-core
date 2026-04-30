"""Performance regression guards for Session hot paths.

These tests enforce algorithmic-complexity invariants that are easy to
lose silently under refactoring:

* ``Session.update()`` must not scan ``events`` while refining a pending
  reinforcer (previously O(n) per update tick).
* ``get_reinforcement_rate`` / ``get_effective_reinforcement_rate`` must
  locate window bounds via binary search, not linear filtering.

The tests use wall-clock measurements with a generous tolerance: they
fail only if runtime scales super-linearly with history size, which is
what would happen if a linear scan crept back into the hot path.
"""

from __future__ import annotations

import time

import pytest

from experiment_core import ReinforcerStartEvent, Session
from experiment_core.events import SessionState
from experiment_core.protocols import Schedule


class _AlwaysReinforceSchedule:
    """Minimal Schedule: every response reinforces. Avoids contingency deps."""

    def __init__(self) -> None:
        self.reset_called = 0

    def step(self, now, event):  # type: ignore[override]
        class _Outcome:
            reinforced = event is not None

        return _Outcome()

    def reset(self) -> None:  # type: ignore[override]
        self.reset_called += 1


def _populate_reinforcers(session: Session, n: int) -> None:
    """Inject n synthetic ReinforcerStartEvents at t = 1, 2, ..., n."""
    for i in range(1, n + 1):
        ts = float(i)
        evt = ReinforcerStartEvent(id=i, timestamp=ts, potency=1.0)
        session.events.append(evt)
        session.reinforcement_history.append((ts, i))
        session._reinforcer_events.append(evt)
        session._reinforcer_event_timestamps.append(ts)


@pytest.mark.unit
def test_update_refinement_no_linear_events_scan() -> None:
    """`update()` during REINFORCING must not scan self.events backwards.

    Previously the code did `for evt in reversed(self.events): ...` to
    find the pending ReinforcerStartEvent. With N prior events this was
    O(N) per update tick. We now cache the pending event and verify by
    measuring runtime against a large dummy-event tail.
    """
    schedule: Schedule = _AlwaysReinforceSchedule()  # type: ignore[assignment]
    session = Session(schedule=schedule)
    session.start(timestamp=0.0)

    # Trigger a reinforcement to enter REINFORCING state.
    session.update(timestamp=1.0, total_responses=1)
    assert session.state == SessionState.REINFORCING
    assert session._pending_reinforcer_event is not None

    # Pollute self.events with non-reinforcer entries that would dominate
    # a reversed() scan if the old implementation were still in place.
    from experiment_core.events import StateChangeEvent

    for _ in range(200_000):
        session.events.append(
            StateChangeEvent(SessionState.RUNNING, SessionState.RUNNING, 0.0)
        )

    # Refinement ticks: each call must be O(1), not O(len(events)).
    iterations = 500
    t0 = time.perf_counter()
    for i in range(iterations):
        session.update(timestamp=1.0 + i * 0.001, total_responses=1)
    elapsed = time.perf_counter() - t0

    # Generous bound: 500 ticks against 200k tail events. Linear scan
    # would be ~1e8 ops (> 1s easily); O(1) is a few ms on any machine.
    assert elapsed < 0.5, f"update() refinement appears O(n): {elapsed:.3f}s"


@pytest.mark.unit
def test_reinforcement_rate_window_is_sublinear() -> None:
    """`get_reinforcement_rate(..., window=...)` must use bisect, not list comp."""
    schedule: Schedule = _AlwaysReinforceSchedule()  # type: ignore[assignment]
    session = Session(schedule=schedule)
    session.start(timestamp=0.0)

    _populate_reinforcers(session, 100_000)
    current_time = 100_000.0
    window = 60.0  # last minute → ~60 entries of 100k

    iterations = 2_000
    t0 = time.perf_counter()
    for _ in range(iterations):
        rate = session.get_reinforcement_rate(current_time, window=window)
    elapsed = time.perf_counter() - t0

    assert rate > 0.0
    # O(log n) per call: 2000 * log2(100k) ≈ 34k ops. Linear would be
    # 2000 * 100k = 2e8 (seconds). Cap well below the linear regime.
    assert elapsed < 0.5, f"get_reinforcement_rate appears O(n): {elapsed:.3f}s"


@pytest.mark.unit
def test_effective_rate_window_is_sublinear() -> None:
    """`get_effective_reinforcement_rate(..., window=...)` must use bisect."""
    schedule: Schedule = _AlwaysReinforceSchedule()  # type: ignore[assignment]
    session = Session(schedule=schedule)
    session.start(timestamp=0.0)

    _populate_reinforcers(session, 100_000)
    current_time = 100_000.0
    window = 60.0

    iterations = 2_000
    t0 = time.perf_counter()
    for _ in range(iterations):
        rate = session.get_effective_reinforcement_rate(current_time, window=window)
    elapsed = time.perf_counter() - t0

    assert rate > 0.0
    assert elapsed < 0.5, f"get_effective_reinforcement_rate appears O(n): {elapsed:.3f}s"


@pytest.mark.unit
def test_rate_windowed_matches_naive_implementation() -> None:
    """bisect path must agree with the straightforward filter for correctness."""
    schedule: Schedule = _AlwaysReinforceSchedule()  # type: ignore[assignment]
    session = Session(schedule=schedule)
    session.start(timestamp=0.0)

    # Irregular timestamps to exercise bisect boundaries.
    for i, ts in enumerate([0.5, 1.0, 1.0, 2.3, 4.0, 7.1, 9.9, 10.0, 10.0, 12.0], start=1):
        evt = ReinforcerStartEvent(id=i, timestamp=ts, potency=0.5 + (i % 3) * 0.25)
        session.events.append(evt)
        session.reinforcement_history.append((ts, i))
        session._reinforcer_events.append(evt)
        session._reinforcer_event_timestamps.append(ts)

    for current_time, window in [(10.0, 5.0), (10.0, 1.0), (12.0, 2.0), (11.0, 100.0)]:
        # Both rate functions use the same half-open-then-inclusive window
        # [current_time - window, current_time]. Events beyond current_time
        # are excluded (a refined pending reinforcer could sit in the future).
        naive_hist = [
            h for h in session.reinforcement_history
            if current_time - window <= h[0] <= current_time
        ]
        duration = current_time - max(0.0, current_time - window)
        expected_rate = (len(naive_hist) / duration) * 60.0 if naive_hist else 0.0
        assert session.get_reinforcement_rate(current_time, window=window) == pytest.approx(
            expected_rate
        )

        naive_eff = [
            e for e in session._reinforcer_events
            if current_time - window <= e.timestamp <= current_time
        ]
        expected_eff = (
            (sum(e.potency for e in naive_eff) / window) * 60.0 if naive_eff else 0.0
        )
        assert session.get_effective_reinforcement_rate(
            current_time, window=window
        ) == pytest.approx(expected_eff)
