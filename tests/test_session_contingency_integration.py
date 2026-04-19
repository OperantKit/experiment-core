"""Integration tests: drive :class:`Session` with real ``contingency`` schedules.

Verifies that the SCOPE-aligned dispatch path (``schedule.step(now, event)``)
produces the same reinforcement accounting as the legacy
``is_satisfied`` path. Uses ``contingency.ScheduleBuilder`` to build
concrete FR / VR / CRF schedules and drives them through
:class:`experiment_core.Session`.
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
    """The legacy ``schedule.next()`` call is skipped for contingency schedules.

    ``contingency.FR`` does not expose ``next()``; if experiment-core
    mis-dispatches this would raise ``AttributeError``.
    """
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)
    session.update(timestamp=1.0, total_responses=1)
    session.end_reinforcement(timestamp=1.1)
    session.update(timestamp=2.0, total_responses=2)
    assert session.state == SessionState.REINFORCING
