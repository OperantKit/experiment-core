"""Integration tests: drive :class:`Session` with real ``contingency`` schedules.

Verifies that :class:`experiment_core.Session` produces the expected
reinforcement accounting when it drives schedules through
``schedule.step(now, event)``. Uses ``contingency.ScheduleBuilder`` to build
concrete FR / CRF / concurrent schedules.
"""

from __future__ import annotations

import pytest
from contingency import ScheduleBuilder

from experiment_core import ReinforcerStartEvent, Session, SessionState
from experiment_core.exit_condition import ReinforcementCountExit


@pytest.mark.integration
def test_session_drives_real_contingency_fr1() -> None:
    """FR(1): each response triggers a reinforcement."""
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)
    assert session.state == SessionState.RUNNING

    session.update(timestamp=1.0, total_responses=1)
    assert session.state == SessionState.REINFORCING

    session.end_reinforcement(timestamp=1.1)
    assert session.state == SessionState.RUNNING

    session.update(timestamp=2.0, total_responses=2)
    assert session.state == SessionState.REINFORCING


@pytest.mark.integration
def test_session_drives_real_contingency_fr3() -> None:
    """FR(3): reinforcement fires on the third response."""
    session = Session(schedule=ScheduleBuilder.fr(3))
    session.start(timestamp=0.0)

    session.update(timestamp=1.0, total_responses=1)
    assert session.state == SessionState.RUNNING

    session.update(timestamp=2.0, total_responses=2)
    assert session.state == SessionState.RUNNING

    session.update(timestamp=3.0, total_responses=3)
    assert session.state == SessionState.REINFORCING


@pytest.mark.integration
def test_session_drives_real_contingency_crf_exit_condition() -> None:
    """CRF + exit_condition: session finishes at the configured count."""
    session = Session(
        schedule=ScheduleBuilder.crf(),
        exit_condition=ReinforcementCountExit(count=3),
    )
    session.start(timestamp=0.0)

    for i, ts in enumerate((1.0, 2.0, 3.0), start=1):
        session.update(timestamp=ts, total_responses=i)
        assert session.state == SessionState.REINFORCING
        session.end_reinforcement(timestamp=ts + 0.1)

    assert session.state == SessionState.FINISHED
    rein_starts = [e for e in session.events if isinstance(e, ReinforcerStartEvent)]
    assert len(rein_starts) == 3


@pytest.mark.integration
def test_contingency_schedule_not_called_after_end_reinforcement() -> None:
    """Session advances the schedule only through ``step``.

    ``contingency.FR`` does not expose ``next()``; if ``end_reinforcement``
    called it, this test would raise ``AttributeError``.
    """
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)
    session.update(timestamp=1.0, total_responses=1)
    session.end_reinforcement(timestamp=1.1)
    session.update(timestamp=2.0, total_responses=2)
    assert session.state == SessionState.REINFORCING


@pytest.mark.integration
def test_session_drives_contingency_concurrent_fr1_fr2() -> None:
    """contingency.Concurrent({left: FR(1), right: FR(2)}) via handle_response_on."""
    schedule = ScheduleBuilder.concurrent(
        {
            "left": ScheduleBuilder.fr(1),
            "right": ScheduleBuilder.fr(2),
        }
    )
    session = Session(schedule=schedule)
    session.start(timestamp=0.0)

    # One response on operandum 0 (left, FR1) should reinforce.
    session.handle_response_on(operandum=0, timestamp=0.5)
    assert session.state == SessionState.REINFORCING
    start_events = [e for e in session.events if isinstance(e, ReinforcerStartEvent)]
    assert len(start_events) == 1
    assert start_events[0].operandum == 0

    session.end_reinforcement(timestamp=0.6)
    assert session.state == SessionState.RUNNING

    # First response on operandum 1 (right, FR2) should NOT reinforce.
    session.handle_response_on(operandum=1, timestamp=1.0)
    assert session.state == SessionState.RUNNING

    # Second response on operandum 1 reinforces.
    session.handle_response_on(operandum=1, timestamp=1.5)
    assert session.state == SessionState.REINFORCING
    start_events = [e for e in session.events if isinstance(e, ReinforcerStartEvent)]
    assert len(start_events) == 2
    assert start_events[-1].operandum == 1


@pytest.mark.integration
def test_contingency_concurrent_rejects_out_of_range_operandum() -> None:
    schedule = ScheduleBuilder.concurrent(
        {
            "a": ScheduleBuilder.fr(1),
            "b": ScheduleBuilder.fr(1),
        }
    )
    session = Session(schedule=schedule)
    session.start(timestamp=0.0)

    with pytest.raises(IndexError):
        session.handle_response_on(operandum=5, timestamp=1.0)


@pytest.mark.integration
def test_contingency_concurrent_handle_response_on_raises_for_single_component() -> None:
    """handle_response_on is only valid for concurrent schedules."""
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)

    with pytest.raises(ValueError):
        session.handle_response_on(operandum=0, timestamp=1.0)
