"""Tests for Clock / VirtualClock / RealtimeClock."""

from __future__ import annotations

import time

import pytest

from experiment_core.clock import Clock, RealtimeClock, VirtualClock


@pytest.mark.unit
def test_virtual_clock_starts_at_zero_by_default() -> None:
    clock = VirtualClock()
    assert clock.now() == 0.0


@pytest.mark.unit
def test_virtual_clock_custom_start() -> None:
    clock = VirtualClock(start=10.5)
    assert clock.now() == 10.5


@pytest.mark.unit
def test_virtual_clock_rejects_negative_start() -> None:
    with pytest.raises(ValueError):
        VirtualClock(start=-1.0)


@pytest.mark.unit
def test_virtual_clock_advance() -> None:
    clock = VirtualClock()
    assert clock.advance(1.0) == 1.0
    assert clock.advance(0.5) == 1.5
    assert clock.now() == 1.5


@pytest.mark.unit
def test_virtual_clock_rejects_negative_advance() -> None:
    clock = VirtualClock()
    with pytest.raises(ValueError):
        clock.advance(-0.1)


@pytest.mark.unit
def test_virtual_clock_set_forward_only() -> None:
    clock = VirtualClock()
    clock.set(5.0)
    assert clock.now() == 5.0
    with pytest.raises(ValueError):
        clock.set(4.9)


@pytest.mark.unit
def test_virtual_clock_reset() -> None:
    clock = VirtualClock()
    clock.advance(10.0)
    clock.reset(start=2.0)
    assert clock.now() == 2.0
    with pytest.raises(ValueError):
        clock.reset(start=-0.5)


@pytest.mark.unit
def test_virtual_clock_satisfies_protocol() -> None:
    clock: Clock = VirtualClock()
    assert isinstance(clock, Clock)


@pytest.mark.unit
def test_realtime_clock_first_call_returns_offset() -> None:
    clock = RealtimeClock(start=100.0)
    first = clock.now()
    assert first == pytest.approx(100.0, abs=1e-3)


@pytest.mark.unit
def test_realtime_clock_advances_with_wall_time() -> None:
    clock = RealtimeClock()
    t0 = clock.now()
    time.sleep(0.01)
    t1 = clock.now()
    assert t1 >= t0
    assert (t1 - t0) >= 0.005


@pytest.mark.unit
def test_realtime_clock_satisfies_protocol() -> None:
    clock: Clock = RealtimeClock()
    assert isinstance(clock, Clock)


@pytest.mark.unit
def test_realtime_clock_reset_rejects_negative_start() -> None:
    clock = RealtimeClock()
    clock.now()
    with pytest.raises(ValueError):
        clock.reset(start=-0.1)


@pytest.mark.unit
def test_realtime_clock_reset_allows_zero_or_positive() -> None:
    clock = RealtimeClock()
    clock.now()
    clock.reset(start=0.0)
    clock.reset(start=5.0)
    assert clock.now() >= 5.0


@pytest.mark.integration
def test_virtual_clock_drives_session_without_wall_time() -> None:
    """VirtualClock + Session can run a schedule without waiting."""
    from contingency import ScheduleBuilder

    from experiment_core import Session, SessionState

    clock = VirtualClock()
    session = Session(schedule=ScheduleBuilder.fr(3))
    session.start(clock.now())

    responses = 0
    for _ in range(3):
        clock.advance(0.1)
        responses += 1
        session.update(clock.now(), responses)

    assert session.state == SessionState.REINFORCING
    session.end_reinforcement(clock.now())
    assert session.reinforcement_count == 1
