"""End-to-end integration tests: Session → events → EventSink → JSON.

Confirms that experiment-core events flow cleanly through the downstream
persistence boundary that session-recorder and behavior-scope will
implement. Uses only experiment-core's own types — no hard dependency
on session-recorder.
"""

from __future__ import annotations

import json

import pytest
from contingency import ScheduleBuilder

from experiment_core import (
    ComponentChangeEvent,
    Observation,
    ReinforcerEndEvent,
    ReinforcerStartEvent,
    ResponseEvent,
    Session,
    SessionState,
    StateChangeEvent,
    VirtualClock,
)
from experiment_core.sink import EventSink, InMemorySink, event_to_dict


@pytest.mark.unit
def test_in_memory_sink_satisfies_protocol() -> None:
    sink: EventSink = InMemorySink()
    assert isinstance(sink, EventSink)


@pytest.mark.unit
def test_event_to_dict_encodes_enums_as_names() -> None:
    evt = StateChangeEvent(
        from_state=SessionState.IDLE,
        to_state=SessionState.RUNNING,
        timestamp=0.0,
    )
    d = event_to_dict(evt)
    assert d["from_state"] == "IDLE"
    assert d["to_state"] == "RUNNING"
    assert d["timestamp"] == 0.0


@pytest.mark.unit
def test_event_to_dict_roundtrips_via_json() -> None:
    evt = ReinforcerStartEvent(id=1, timestamp=1.5, operandum=0, potency=0.75)
    payload = json.dumps(event_to_dict(evt))
    restored = json.loads(payload)
    assert restored == {
        "id": 1,
        "timestamp": 1.5,
        "operandum": 0,
        "potency": 0.75,
    }


@pytest.mark.unit
def test_event_to_dict_rejects_non_dataclass() -> None:
    with pytest.raises(TypeError):
        event_to_dict("not an event")  # type: ignore[arg-type]


@pytest.mark.unit
def test_event_to_dict_roundtrips_component_change_event() -> None:
    evt = ComponentChangeEvent(from_component="ICI", to_component="C1", timestamp=60.014)
    payload = json.dumps(event_to_dict(evt))
    restored = json.loads(payload)
    assert restored == {
        "from_component": "ICI",
        "to_component": "C1",
        "timestamp": 60.014,
    }


@pytest.mark.unit
def test_event_to_dict_roundtrips_response_event_with_operandum() -> None:
    evt = ResponseEvent(id=42, timestamp=2.5, operandum=1)
    payload = json.dumps(event_to_dict(evt))
    restored = json.loads(payload)
    assert restored == {
        "id": 42,
        "timestamp": 2.5,
        "operandum": 1,
    }


@pytest.mark.integration
def test_session_events_flow_to_sink_with_virtual_clock() -> None:
    """Drive a Session with VirtualClock, sink every event, then verify."""
    clock = VirtualClock()
    sink = InMemorySink()

    session = Session(schedule=ScheduleBuilder.fr(2))
    session.start(clock.now())

    responses = 0
    for _ in range(2):
        clock.advance(0.5)
        responses += 1
        session.update(clock.now(), responses)

    assert session.state == SessionState.REINFORCING

    clock.advance(0.1)
    session.end_reinforcement(clock.now())

    for evt in session.events:
        sink.emit(evt)

    dicts = sink.to_dicts()
    assert len(dicts) == len(session.events)

    # All dicts are JSON-serialisable.
    serialised = json.dumps(dicts)
    restored = json.loads(serialised)
    assert len(restored) == len(dicts)

    # Session lifecycle visible via state transitions.
    transitions = [d for d in dicts if "from_state" in d]
    states = [(t["from_state"], t["to_state"]) for t in transitions]
    assert states[0] == ("IDLE", "RUNNING")
    assert ("RUNNING", "REINFORCING") in states
    assert ("REINFORCING", "RUNNING") in states

    # One reinforcement delivered.
    start_events = [d for d in dicts if "potency" in d]
    end_events = [d for d in dicts if "operandum" in d and "potency" not in d]
    assert len(start_events) == 1
    assert len(end_events) == 1


@pytest.mark.integration
def test_concurrent_session_events_tagged_with_operandum() -> None:
    """Concurrent sessions route events through the sink with operandum IDs."""
    clock = VirtualClock()
    sink = InMemorySink()

    schedule = ScheduleBuilder.concurrent(
        {"op0": ScheduleBuilder.fr(1), "op1": ScheduleBuilder.fr(1)}
    )
    session = Session(schedule=schedule)
    session.start(clock.now())

    clock.advance(0.1)
    session.handle_response_on(1, clock.now())
    assert session.state == SessionState.REINFORCING

    clock.advance(0.05)
    session.end_reinforcement(clock.now())

    for evt in session.events:
        sink.emit(evt)

    start = [e for e in sink.events if isinstance(e, ReinforcerStartEvent)]
    end = [e for e in sink.events if isinstance(e, ReinforcerEndEvent)]
    assert len(start) == 1
    assert len(end) == 1
    assert start[0].operandum == 1
    assert end[0].operandum == 1

    # JSON round-trip preserves the operandum.
    payload = json.loads(json.dumps(sink.to_dicts()))
    start_payload = [p for p in payload if "potency" in p][0]
    assert start_payload["operandum"] == 1


@pytest.mark.integration
def test_sink_satisfies_downstream_event_flow_contract() -> None:
    """Any object with ``emit(event) -> None`` satisfies EventSink."""

    class CountingSink:
        def __init__(self) -> None:
            self.count = 0

        def emit(self, event: object) -> None:
            self.count += 1

    clock = VirtualClock()
    session = Session(schedule=ScheduleBuilder.fr(1))
    sink: EventSink = CountingSink()
    assert isinstance(sink, EventSink)

    session.start(clock.now())
    clock.advance(1.0)
    session.update(clock.now(), 1)
    for evt in session.events:
        sink.emit(evt)
    assert sink.count == len(session.events)  # type: ignore[attr-defined]


@pytest.mark.unit
def test_observation_is_dataclass_asdict_compatible() -> None:
    """Observation survives asdict() — useful for snapshot debugging."""
    from dataclasses import asdict

    obs = Observation(total_responses=5, current_time=1.0)
    d = asdict(obs)
    assert d["total_responses"] == 5
    assert d["current_time"] == 1.0
