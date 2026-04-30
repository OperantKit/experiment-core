"""Tests for event dataclasses and the :data:`SessionEvent` union."""

import typing
from datetime import UTC, datetime

import pytest

from experiment_core import (
    ComponentChangeEvent,
    ReinforcerEndEvent,
    ReinforcerStartEvent,
    ResponseEvent,
    SessionEvent,
    SessionMeta,
    SessionState,
    StateChangeEvent,
)


@pytest.mark.unit
def test_response_event_fields() -> None:
    e = ResponseEvent(id=1, timestamp=0.5)
    assert e.id == 1
    assert e.timestamp == 0.5


@pytest.mark.unit
def test_response_event_default_operandum_is_none() -> None:
    e = ResponseEvent(id=1, timestamp=0.5)
    assert e.operandum is None


@pytest.mark.unit
def test_response_event_with_explicit_operandum() -> None:
    e = ResponseEvent(id=2, timestamp=1.0, operandum=1)
    assert e.operandum == 1


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
def test_component_change_event_fields() -> None:
    e = ComponentChangeEvent(from_component="ICI", to_component="C1", timestamp=60.014)
    assert e.from_component == "ICI"
    assert e.to_component == "C1"
    assert e.timestamp == 60.014


@pytest.mark.unit
def test_component_change_event_session_start_uses_empty_from() -> None:
    """Empty ``from_component`` is the canonical session-start convention."""
    e = ComponentChangeEvent(from_component="", to_component="C1", timestamp=0.0)
    assert e.from_component == ""
    assert e.to_component == "C1"


@pytest.mark.unit
def test_session_event_union_carries_all_five_types() -> None:
    args = typing.get_args(SessionEvent)
    assert set(args) == {
        ResponseEvent,
        ReinforcerStartEvent,
        ReinforcerEndEvent,
        StateChangeEvent,
        ComponentChangeEvent,
    }


@pytest.mark.unit
def test_session_state_enum_values() -> None:
    assert SessionState.IDLE.value == 0
    assert SessionState.RUNNING.value == 1
    assert SessionState.REINFORCING.value == 2
    assert SessionState.PAUSED.value == 3
    assert SessionState.FINISHED.value == 4


# --- SessionMeta -----------------------------------------------------


@pytest.mark.unit
def test_session_meta_minimum_construction() -> None:
    m = SessionMeta(timestamp=0.0, clock_type="VirtualClock", session_name="demo")
    assert m.timestamp == 0.0
    assert m.clock_type == "VirtualClock"
    assert m.session_name == "demo"


@pytest.mark.unit
def test_session_meta_optional_identity_fields_default_to_none() -> None:
    m = SessionMeta(timestamp=0.0, clock_type="VirtualClock", session_name="demo")
    assert m.subject_id is None
    assert m.replication_index is None
    assert m.experiment_name is None
    assert m.protocol_id is None
    assert m.task_file_hash is None
    assert m.wall_clock_start is None


@pytest.mark.unit
def test_session_meta_notes_default_is_empty_list() -> None:
    m = SessionMeta(timestamp=0.0, clock_type="VirtualClock", session_name="demo")
    assert m.notes == []
    assert isinstance(m.notes, list)


@pytest.mark.unit
def test_session_meta_metadata_default_is_empty_dict() -> None:
    m = SessionMeta(timestamp=0.0, clock_type="VirtualClock", session_name="demo")
    assert m.metadata == {}
    assert isinstance(m.metadata, dict)


@pytest.mark.unit
def test_session_meta_metadata_is_per_instance() -> None:
    """Default-factory dict must not be shared between instances."""
    a = SessionMeta(timestamp=0.0, clock_type="V", session_name="a")
    b = SessionMeta(timestamp=0.0, clock_type="V", session_name="b")
    a.metadata["k"] = 1
    assert b.metadata == {}


@pytest.mark.unit
def test_session_meta_full_construction() -> None:
    start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=UTC)
    m = SessionMeta(
        timestamp=0.0,
        clock_type="RealtimeClock",
        session_name="example-session",
        subject_id="rat-001",
        replication_index=1,
        experiment_name="FR baseline",
        protocol_id="fr3",
        task_file_hash="abc123",
        wall_clock_start=start,
        notes=["operator note one"],
        metadata={
            "schedule": {"spec_dsl": "FR3", "parameters": {"n": 3}},
            "operandum_labels": {0: "lever_a", 1: "lever_b"},
        },
    )
    assert m.subject_id == "rat-001"
    assert m.replication_index == 1
    assert m.experiment_name == "FR baseline"
    assert m.protocol_id == "fr3"
    assert m.task_file_hash == "abc123"
    assert m.wall_clock_start == start
    assert m.notes == ["operator note one"]
    assert m.metadata["operandum_labels"][0] == "lever_a"


@pytest.mark.unit
def test_session_meta_notes_are_per_instance() -> None:
    """Default-factory list must not be shared between instances."""
    a = SessionMeta(timestamp=0.0, clock_type="V", session_name="a")
    b = SessionMeta(timestamp=0.0, clock_type="V", session_name="b")
    a.notes.append("a-note")
    assert b.notes == []


@pytest.mark.unit
def test_session_meta_wall_clock_start_accepts_both_naive_and_aware() -> None:
    """tz-aware datetime is the documented contract, but the type permits
    naive datetime; tz-validation is left to the caller."""
    naive = datetime(2017, 7, 7, 9, 38, 10)
    aware = datetime(2017, 7, 7, 9, 38, 10, tzinfo=UTC)
    m_naive = SessionMeta(timestamp=0.0, clock_type="V", session_name="x", wall_clock_start=naive)
    m_aware = SessionMeta(timestamp=0.0, clock_type="V", session_name="x", wall_clock_start=aware)
    assert m_naive.wall_clock_start.tzinfo is None
    assert m_aware.wall_clock_start.tzinfo is UTC
