"""EventSink Protocol and in-memory reference implementation.

experiment-core owns the event *types* (:mod:`experiment_core.events`)
but delegates *persistence* to downstream packages:

- ``session-recorder`` writes events to JSONL
- ``behavior-scope`` streams them to a dashboard
- tests and simulators typically want an in-memory capture

This module defines the narrow Protocol that all sinks must satisfy,
plus :class:`InMemorySink` for unit tests and simulation replay.

Every event dataclass in :mod:`experiment_core.events` is constructed
from simple types (int / float / enum / Optional[int]) and is therefore
``dataclasses.asdict``-serialisable. :func:`event_to_dict` produces a
JSON-friendly ``dict`` (enum -> name string) that any ``json.dump``
implementation can accept.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from .events import SessionEvent


@runtime_checkable
class EventSink(Protocol):
    """Accepts Session events as they are emitted."""

    def emit(self, event: SessionEvent) -> None:  # pragma: no cover
        ...


def event_to_dict(event: SessionEvent) -> dict[str, Any]:
    """Convert an event dataclass to a JSON-serialisable dict.

    Enums are replaced by their ``name`` string so that downstream
    JSON writers (including the standard library's :mod:`json`) can
    encode the result without a custom serialiser.
    """
    if not is_dataclass(event):
        raise TypeError(f"event {event!r} is not a dataclass")
    raw = asdict(event)
    return {k: _encode(v) for k, v in raw.items()}


def _encode(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_encode(v) for v in value]
    return value


class InMemorySink:
    """Reference :class:`EventSink` that accumulates events in a list."""

    def __init__(self) -> None:
        self._events: list[SessionEvent] = []

    def emit(self, event: SessionEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> list[SessionEvent]:
        return list(self._events)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [event_to_dict(e) for e in self._events]

    def clear(self) -> None:
        self._events.clear()
