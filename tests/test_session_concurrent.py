"""Concurrent-schedule routing and bookkeeping."""

import pytest

from experiment_core import ReinforcerStartEvent, Session, SessionState

from ._fakes import FakeConcurrent, FakeFR


@pytest.mark.unit
def test_handle_response_on_routes_to_component() -> None:
    schedule = FakeConcurrent(targets=[2, 3])
    session = Session(schedule=schedule)
    session.start(timestamp=0.0)

    session.handle_response_on(operandum=0, timestamp=0.5)
    session.handle_response_on(operandum=0, timestamp=1.0)

    # schedule.note_response_on was invoked on each handle_response_on call.
    assert schedule.responses_by_operandum == [(0, 0.5), (0, 1.0)]

    # Component 0 has met its target so reinforcement fires.
    assert session.state == SessionState.REINFORCING
    start_events = [e for e in session.events if isinstance(e, ReinforcerStartEvent)]
    assert len(start_events) == 1
    assert start_events[0].operandum == 0


@pytest.mark.unit
def test_per_component_bookkeeping_resets_after_end_reinforcement() -> None:
    schedule = FakeConcurrent(targets=[1, 2])
    session = Session(schedule=schedule)
    session.start(timestamp=0.0)

    session.handle_response_on(operandum=0, timestamp=0.5)
    assert session.state == SessionState.REINFORCING
    session.end_reinforcement(timestamp=0.6)
    assert session.state == SessionState.RUNNING

    # After end_reinforcement the _last_reinforcement_responses_per[0]
    # should track the cumulative component count so that the next
    # reinforcement requires a fresh response on that operandum.
    assert session._last_reinforcement_responses_per[0] == 1

    # Drive operandum 1 to satisfy its target.
    session.handle_response_on(operandum=1, timestamp=1.0)
    session.handle_response_on(operandum=1, timestamp=1.5)
    assert session.state == SessionState.REINFORCING
    start_events = [e for e in session.events if isinstance(e, ReinforcerStartEvent)]
    assert start_events[-1].operandum == 1


@pytest.mark.unit
def test_handle_response_on_non_concurrent_raises_value_error() -> None:
    session = Session(schedule=FakeFR(target=1))
    session.start(timestamp=0.0)
    with pytest.raises(ValueError):
        session.handle_response_on(operandum=0, timestamp=0.1)


@pytest.mark.unit
def test_handle_response_on_out_of_range_raises_index_error() -> None:
    session = Session(schedule=FakeConcurrent(targets=[1, 1]))
    session.start(timestamp=0.0)
    with pytest.raises(IndexError):
        session.handle_response_on(operandum=5, timestamp=0.1)
    with pytest.raises(IndexError):
        session.handle_response_on(operandum=-1, timestamp=0.1)
