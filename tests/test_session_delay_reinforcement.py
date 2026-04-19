"""Delay-of-reinforcement tests. Adapted from v0 with local fakes."""

import math

import pytest
from contingency import ScheduleBuilder

from experiment_core import DelayFunction, ReinforcerStartEvent, Session, SessionState

ABS_TOL = 1e-9


@pytest.mark.unit
def test_potency_with_zero_delay_reinforcement() -> None:
    """Response and reinforcement on the same tick yields potency 1.0."""
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)

    session.update(timestamp=1.0, total_responses=1)

    start_events = [e for e in session.events if isinstance(e, ReinforcerStartEvent)]
    assert len(start_events) == 1
    event = start_events[0]

    expected = DelayFunction().calculate_potency(delay_duration=0.0, is_signaled=False)
    assert math.isclose(event.potency, expected, abs_tol=ABS_TOL)
    assert expected == 1.0
    assert event.timestamp == 1.0
    assert session.state == SessionState.REINFORCING


@pytest.mark.unit
@pytest.mark.parametrize(
    "response_time, reinforcement_start_time, expected_delay",
    [
        (1.0, 1.0, 0.0),
        (1.0, 1.1, 0.1),
        (1.0, 1.5, 0.5),
        (1.0, 2.0, 1.0),
        (1.0, 3.0, 2.0),
    ],
)
def test_potency_with_non_zero_delay_reinforcement(
    response_time: float,
    reinforcement_start_time: float,
    expected_delay: float,
) -> None:
    """A deferred reinforcement tick refines potency from the trigger response."""
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)

    # Satisfying response.
    session.update(timestamp=response_time, total_responses=1)
    # Later tick without new response -> refines pending reinforcement.
    session.update(timestamp=reinforcement_start_time, total_responses=1)

    start_events = [e for e in session.events if isinstance(e, ReinforcerStartEvent)]
    assert len(start_events) == 1
    event = start_events[0]

    expected_potency = DelayFunction().calculate_potency(
        delay_duration=expected_delay, is_signaled=False
    )
    assert math.isclose(event.potency, expected_potency, abs_tol=ABS_TOL)
    assert event.timestamp == reinforcement_start_time
    assert session.state == SessionState.REINFORCING


@pytest.mark.unit
def test_multiple_potency_recordings_with_varying_delays() -> None:
    """Multiple reinforcers with different delays each record correct potency."""
    session = Session(schedule=ScheduleBuilder.fr(1))
    session.start(timestamp=0.0)

    delay_configs = [
        {"response_time": 1.0, "reinforcement_start_time": 1.0, "expected_delay": 0.0},
        {"response_time": 2.0, "reinforcement_start_time": 2.5, "expected_delay": 0.5},
        {"response_time": 3.0, "reinforcement_start_time": 4.0, "expected_delay": 1.0},
    ]

    total_responses = 0
    for config in delay_configs:
        total_responses += 1
        session.update(timestamp=config["response_time"], total_responses=total_responses)
        session.update(
            timestamp=config["reinforcement_start_time"], total_responses=total_responses
        )
        if session.state == SessionState.REINFORCING:
            session.end_reinforcement(timestamp=config["reinforcement_start_time"])

    start_events = [e for e in session.events if isinstance(e, ReinforcerStartEvent)]
    assert len(start_events) == len(delay_configs)

    for event, config in zip(start_events, delay_configs, strict=True):
        expected_potency = DelayFunction().calculate_potency(
            delay_duration=config["expected_delay"], is_signaled=False
        )
        assert math.isclose(event.potency, expected_potency, abs_tol=ABS_TOL)
        assert event.timestamp == config["reinforcement_start_time"]
