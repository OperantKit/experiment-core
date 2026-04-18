"""Session lifecycle state-transition tests."""

import pytest

from experiment_core import (
    ReinforcementCountExit,
    Session,
    SessionState,
    TimeLimitExit,
)

from ._fakes import FakeFR


@pytest.mark.unit
def test_session_starts_idle_and_transitions_to_running() -> None:
    session = Session(schedule=FakeFR(target=1))
    assert session.state == SessionState.IDLE
    session.start(timestamp=0.0)
    assert session.state == SessionState.RUNNING


@pytest.mark.unit
def test_fr1_runs_through_running_reinforcing_running() -> None:
    session = Session(schedule=FakeFR(target=1))
    session.start(timestamp=0.0)
    assert session.state == SessionState.RUNNING

    session.update(timestamp=1.0, total_responses=1)
    assert session.state == SessionState.REINFORCING

    session.end_reinforcement(timestamp=1.1)
    assert session.state == SessionState.RUNNING


@pytest.mark.unit
def test_reinforcement_count_exit_triggers_finished() -> None:
    session = Session(
        schedule=FakeFR(target=1),
        exit_condition=ReinforcementCountExit(count=2),
    )
    session.start(timestamp=0.0)

    total = 0
    t = 0.0
    for _ in range(10):
        if session.state == SessionState.FINISHED:
            break
        if session.state == SessionState.REINFORCING:
            t += 0.1
            session.end_reinforcement(timestamp=t)
            continue
        t += 1.0
        total += 1
        session.update(timestamp=t, total_responses=total)

    assert session.state == SessionState.FINISHED
    assert session.reinforcement_count == 2


@pytest.mark.unit
def test_time_limit_exit_triggers_finished() -> None:
    session = Session(
        schedule=FakeFR(target=100),
        exit_condition=TimeLimitExit(limit=1.0),
    )
    session.start(timestamp=0.0)
    # Advance past the limit without satisfying the schedule.
    session.update(timestamp=2.0, total_responses=1)
    assert session.state == SessionState.FINISHED
