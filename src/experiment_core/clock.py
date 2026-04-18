"""Clock abstraction for experiment-core.

Session itself is time-source-agnostic: callers pass canonical-second
timestamps to :meth:`Session.start`, :meth:`Session.update`, and
:meth:`Session.end_reinforcement`. This module provides two small helpers
callers can use to generate those timestamps:

- :class:`VirtualClock` — deterministic, advance-on-demand. Use in
  simulations and unit tests so the runner never waits in real time.
- :class:`RealtimeClock` — thin wrapper around :func:`time.monotonic`
  with an optional offset so simulation-replay timestamps can be
  reproduced after a session has completed.

Both implement the :class:`Clock` Protocol, which exposes only ``now()``.
"""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Anything that can produce a canonical-second timestamp."""

    def now(self) -> float:  # pragma: no cover — Protocol definition
        ...


class VirtualClock:
    """Deterministic clock for simulations and tests.

    The clock never advances on its own; callers move it forward with
    :meth:`advance` or :meth:`set`. This makes it trivial to reproduce
    any ordering of events without real-time waits.
    """

    def __init__(self, start: float = 0.0) -> None:
        if start < 0.0:
            raise ValueError("start must be non-negative")
        self._t: float = float(start)

    def now(self) -> float:
        return self._t

    def advance(self, dt: float) -> float:
        """Advance time by ``dt`` seconds (must be non-negative)."""
        if dt < 0.0:
            raise ValueError("dt must be non-negative")
        self._t += float(dt)
        return self._t

    def set(self, t: float) -> float:
        """Set the clock to ``t`` (must not move backwards)."""
        t = float(t)
        if t < self._t:
            raise ValueError("clock cannot move backwards")
        self._t = t
        return self._t

    def reset(self, start: float = 0.0) -> None:
        """Reset the clock to ``start`` (discards elapsed time)."""
        if start < 0.0:
            raise ValueError("start must be non-negative")
        self._t = float(start)


class RealtimeClock:
    """Wall-clock timer based on :func:`time.monotonic`.

    The first call to :meth:`now` establishes the zero point (or
    the explicit ``start`` argument, if given). Subsequent calls
    return seconds elapsed since that zero point.
    """

    def __init__(self, start: float = 0.0) -> None:
        self._offset: float = float(start)
        self._epoch: float | None = None

    def now(self) -> float:
        if self._epoch is None:
            self._epoch = time.monotonic()
            return self._offset
        return self._offset + (time.monotonic() - self._epoch)

    def reset(self, start: float = 0.0) -> None:
        if start < 0.0:
            raise ValueError("start must be non-negative")
        self._offset = float(start)
        self._epoch = None
