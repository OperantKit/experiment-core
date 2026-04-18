"""Tests for event dataclasses and the :data:`SessionEvent` union."""

import typing

import pytest

from experiment_core import (
    ReinforcerEndEvent,
    ReinforcerStartEvent,
    ResponseEvent,
    SessionEvent,
    SessionState,
    StateChangeEvent,
)


@pytest.mark.unit
def test_response_event_fields() -> None:
    e = ResponseEvent(id=1, timestamp=0.5)
    assert e.id == 1
    assert e.timestamp == 0.5


@pytest.mark.unit
def test_reinforcer_start_event_defaults() -> None:
    e = ReinforcerStartEvent(id=1, timestamp=1.0)
    assert e.operandum is None
    assert e.potency == 1.0


@pytest.mark.unit
def test_reinforcer_start_event_with_operandum_and_potency() -> None:
    e = ReinforcerStartEvent(id=2, timestamp=2.0, operandum=1, potency=0.5)
    assert e.operandum == 1
    assert e.potency == 0.5


@pytest.mark.unit
def test_reinforcer_end_event_default_operandum() -> None:
    e = ReinforcerEndEvent(id=1, timestamp=2.0)
    assert e.operandum is None


@pytest.mark.unit
def test_state_change_event_fields() -> None:
    e = StateChangeEvent(from_state=SessionState.IDLE, to_state=SessionState.RUNNING, timestamp=0.0)
    assert e.from_state == SessionState.IDLE
    assert e.to_state == SessionState.RUNNING
    assert e.timestamp == 0.0


@pytest.mark.unit
def test_session_event_union_carries_all_four_types() -> None:
    args = typing.get_args(SessionEvent)
    assert set(args) == {
        ResponseEvent,
        ReinforcerStartEvent,
        ReinforcerEndEvent,
        StateChangeEvent,
    }


@pytest.mark.unit
def test_session_state_enum_values() -> None:
    assert SessionState.IDLE.value == 0
    assert SessionState.RUNNING.value == 1
    assert SessionState.REINFORCING.value == 2
    assert SessionState.PAUSED.value == 3
    assert SessionState.FINISHED.value == 4
