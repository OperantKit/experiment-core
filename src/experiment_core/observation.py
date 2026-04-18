"""Observation dataclass used by schedule predicates.

All time values are canonical seconds (float).
"""

from dataclasses import dataclass, field


@dataclass
class Observation:
    """Snapshot of session-level state passed to schedule predicates.

    Attributes
    ----------
    total_responses : int
        Cumulative response count since session start.
    responses_since_last_reinforcement : int
        Responses emitted since the most recent reinforcer delivery.
    current_time : float
        Current timestamp (seconds) within the session.
    time_since_last_reinforcement : float
        Elapsed seconds since the most recent reinforcer delivery.
    last_response_timestamp : float
        Timestamp of the most recent response.
    component_responses : list[int]
        Per-component response counts (used by compound schedules such as
        Concurrent). Empty for single-component sessions.
    component_time_since_reinforcement : list[float]
        Per-component elapsed seconds since each component's last
        reinforcer delivery. Empty for single-component sessions.
    timestamp_of_triggering_response : float
        Timestamp of the response that satisfied the schedule, used for
        delay-of-reinforcement calculations.
    """

    total_responses: int = 0
    responses_since_last_reinforcement: int = 0
    current_time: float = 0.0
    time_since_last_reinforcement: float = 0.0
    last_response_timestamp: float = 0.0
    component_responses: list[int] = field(default_factory=list)
    component_time_since_reinforcement: list[float] = field(default_factory=list)
    timestamp_of_triggering_response: float = 0.0
