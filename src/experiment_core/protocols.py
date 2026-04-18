"""Schedule and ConcurrentSchedule Protocols used by :class:`Session`.

These Protocols describe the minimal surface that :class:`Session` depends
on from schedule implementations. Concrete schedule classes live in
separate packages (for example ``contingency-py``); ``experiment-core``
talks to them structurally via these Protocols.

All time values are canonical seconds (float).
"""

from typing import Protocol, runtime_checkable

from .observation import Observation


@runtime_checkable
class Schedule(Protocol):
    """Minimal schedule interface required by :class:`Session`.

    Single-component schedules are queried via ``is_satisfied`` on each
    ``Session.update`` tick. ``next`` advances any internal state used by
    variable schedules after a reinforcer is delivered. The optional
    ``note_response`` hook allows schedules (for example DRO) to observe
    every response regardless of reinforcement.
    """

    def is_satisfied(self, observation: Observation) -> bool:
        """Return ``True`` if the schedule is currently ready to reinforce."""
        ...

    def next(self) -> None:
        """Advance to the next target (for variable schedules)."""
        ...


@runtime_checkable
class ConcurrentSchedule(Protocol):
    """Multi-component schedule addressed by operandum index.

    Implementations expose ``n_components`` and a ``which_satisfied`` query
    that returns the index of a component ready to reinforce, or ``None``.
    """

    @property
    def n_components(self) -> int:
        """Number of operanda / concurrent components."""
        ...

    def which_satisfied(self, observation: Observation) -> int | None:
        """Return the index of a satisfied component, or ``None``."""
        ...

    def note_response(self, operandum: int, timestamp: float) -> None:
        """Notify the schedule that a response occurred on ``operandum``."""
        ...

    def next(self) -> None:
        """Advance to the next target after a reinforcer is delivered."""
        ...
