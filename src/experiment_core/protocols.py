"""Schedule Protocol — aliased to :class:`contingency.Schedule`.

experiment-core drives ``contingency`` schedules directly via
``Schedule.step(now, event) -> Outcome`` + ``Schedule.reset()``. The
package no longer declares its own schedule Protocol. Compound concurrent
schedules are modelled by :class:`contingency.schedules.concurrent.Concurrent`,
whose :attr:`~contingency.schedules.concurrent.Concurrent.components`
mapping carries the operandum keys; no separate ``ConcurrentSchedule``
type is required.
"""

from __future__ import annotations

from contingency import Schedule

__all__ = ["Schedule"]
