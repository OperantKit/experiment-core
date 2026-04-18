"""Session-termination conditions.

All time values are canonical seconds (float).
"""

from dataclasses import dataclass


@dataclass
class ReinforcementCountExit:
    """Terminate the session after a fixed number of reinforcers."""

    count: int


@dataclass
class TimeLimitExit:
    """Terminate the session after a fixed elapsed duration (seconds)."""

    limit: float


ExitCondition = ReinforcementCountExit | TimeLimitExit
