"""Reinforcement rate and effective reinforcement rate basic sanity checks."""

import math

import pytest
from contingency import ScheduleBuilder

from experiment_core import ReinforcerStartEvent, Session

ABS_TOL = 1e-9


def _inject_reinforcer(session: Session, timestamp: float, potency: float, rid: int) -> None:
    """Append a synthetic ReinforcerStartEvent + history tuple for rate tests."""
    session.events.append(ReinforcerStartEvent(id=rid, timestamp=timestamp, potency=potency))
    session.reinforcement_history.append((timestamp, rid))


@pytest.mark.unit
def test_rate_zero_before_any_reinforcement() -> None:
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)
    assert session.get_reinforcement_rate(current_time=10.0) == 0.0
    assert session.get_effective_reinforcement_rate(current_time=10.0) == 0.0


@pytest.mark.unit
def test_reinforcement_rate_full_potency() -> None:
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)
    for i, t in enumerate((1.0, 2.0, 3.0), start=1):
        _inject_reinforcer(session, timestamp=t, potency=1.0, rid=i)

    # 3 reinforcers / 5 seconds * 60 = 36 per minute.
    rate = session.get_reinforcement_rate(current_time=5.0)
    assert math.isclose(rate, 36.0, abs_tol=ABS_TOL)

    # With potency 1.0 effective rate equals actual rate.
    effective = session.get_effective_reinforcement_rate(current_time=5.0)
    assert math.isclose(effective, rate, abs_tol=ABS_TOL)


@pytest.mark.unit
def test_effective_rate_is_lower_with_partial_potency() -> None:
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)
    _inject_reinforcer(session, timestamp=1.0, potency=1.0, rid=1)
    _inject_reinforcer(session, timestamp=2.0, potency=0.5, rid=2)
    _inject_reinforcer(session, timestamp=3.0, potency=0.25, rid=3)

    current_time = 5.0
    expected_effective = ((1.0 + 0.5 + 0.25) / current_time) * 60.0
    assert math.isclose(
        session.get_effective_reinforcement_rate(current_time=current_time),
        expected_effective,
        abs_tol=ABS_TOL,
    )
    assert session.get_effective_reinforcement_rate(current_time) < session.get_reinforcement_rate(
        current_time
    )


@pytest.mark.unit
def test_effective_rate_with_window_excludes_outside_events() -> None:
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)
    _inject_reinforcer(session, timestamp=1.0, potency=1.0, rid=1)  # outside window
    _inject_reinforcer(session, timestamp=5.0, potency=1.0, rid=2)  # inside
    _inject_reinforcer(session, timestamp=6.5, potency=0.5, rid=3)  # inside
    _inject_reinforcer(session, timestamp=9.0, potency=1.0, rid=4)  # outside

    current_time = 8.0
    window = 4.0
    expected = ((1.0 + 0.5) / window) * 60.0
    assert math.isclose(
        session.get_effective_reinforcement_rate(current_time=current_time, window=window),
        expected,
        abs_tol=ABS_TOL,
    )
