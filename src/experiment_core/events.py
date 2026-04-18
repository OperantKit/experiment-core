"""Session event dataclasses and the :class:`SessionState` enum.

All time values are canonical seconds (float).
"""

from dataclasses import dataclass
from enum import Enum


class SessionState(Enum):
    """Lifecycle states for a :class:`~experiment_core.session.Session`."""

    IDLE = 0
    RUNNING = 1
    REINFORCING = 2
    PAUSED = 3
    FINISHED = 4


@dataclass
class ResponseEvent:
    """A single subject response."""

    id: int
    timestamp: float


@dataclass
class ReinforcerStartEvent:
    """Emitted when a reinforcer is scheduled for delivery.

    ``potency`` reflects the delay-discounted strength of the reinforcer at
    the moment of delivery.
    """

    id: int
    timestamp: float
    operandum: int | None = None
    potency: float = 1.0


@dataclass
class ReinforcerEndEvent:
    """Emitted when a reinforcer delivery completes."""

    id: int
    timestamp: float
    operandum: int | None = None


@dataclass
class StateChangeEvent:
    """Emitted when the session transitions between :class:`SessionState` values."""

    from_state: SessionState
    to_state: SessionState
    timestamp: float


SessionEvent = ResponseEvent | ReinforcerStartEvent | ReinforcerEndEvent | StateChangeEvent
