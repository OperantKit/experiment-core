"""Experimental orchestration core for operantkit.

Session lifecycle, ExperimentContext, and Renewal paradigms.
Schedule runtime is accessed via Protocol (see :mod:`experiment_core.protocols`).

All time values in this package are canonical seconds (float).
"""

from .clock import Clock, RealtimeClock, VirtualClock
from .context import ExperimentContext
from .delay import DelayFunction
from .events import (
    ReinforcerEndEvent,
    ReinforcerStartEvent,
    ResponseEvent,
    SessionEvent,
    SessionState,
    StateChangeEvent,
)
from .exit_condition import ExitCondition, ReinforcementCountExit, TimeLimitExit
from .observation import Observation
from .protocols import ConcurrentSchedule, Schedule
from .renewal import (
    ContextualSession,
    PhaseRecord,
    PhaseResult,
    RenewalExperiment,
    RenewalParadigm,
    renewal_index,
)
from .session import Session

__version__ = "0.1.0a0"

__all__ = [
    "Clock",
    "VirtualClock",
    "RealtimeClock",
    "ExperimentContext",
    "Session",
    "SessionState",
    "ResponseEvent",
    "ReinforcerStartEvent",
    "ReinforcerEndEvent",
    "StateChangeEvent",
    "SessionEvent",
    "Observation",
    "DelayFunction",
    "ExitCondition",
    "ReinforcementCountExit",
    "TimeLimitExit",
    "Schedule",
    "ConcurrentSchedule",
    "RenewalParadigm",
    "ContextualSession",
    "RenewalExperiment",
    "PhaseRecord",
    "PhaseResult",
    "renewal_index",
    "__version__",
]
