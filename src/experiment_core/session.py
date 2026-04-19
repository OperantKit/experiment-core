"""Session lifecycle and reinforcement bookkeeping.

All time values are canonical seconds (float). ``Session`` drives
:class:`contingency.Schedule` instances directly via their
``step(now, event) -> Outcome`` + ``reset()`` API.
"""

from __future__ import annotations

from contingency.entities import ResponseEvent as _CResponseEvent

from .delay import DelayFunction
from .events import (
    ReinforcerEndEvent,
    ReinforcerStartEvent,
    SessionEvent,
    SessionState,
    StateChangeEvent,
)
from .exit_condition import ExitCondition, ReinforcementCountExit, TimeLimitExit
from .observation import Observation
from .protocols import Schedule


def _is_contingency_concurrent(schedule: object) -> bool:
    """Detect :class:`contingency.schedules.concurrent.Concurrent`.

    A compound concurrent schedule carries a ``components`` mapping
    (operandum key -> component schedule). Responses are routed via
    :attr:`contingency.entities.ResponseEvent.operandum`.
    """
    return hasattr(schedule, "components") and hasattr(schedule, "step")


def _step_satisfied(
    schedule: Schedule,
    now: float,
    is_new_response: bool,
    operandum: str = "main",
) -> bool:
    """Drive a single :meth:`contingency.Schedule.step` and return ``reinforced``."""
    event = _CResponseEvent(time=now, operandum=operandum) if is_new_response else None
    outcome = schedule.step(now, event)
    return bool(outcome.reinforced)


class Session:
    """Reinforcement session driver.

    Accepts any :class:`contingency.Schedule` — atomic (FR, VR, FI, VI, ...)
    or compound :class:`contingency.schedules.concurrent.Concurrent`.
    Single-operandum callers drive the session with :meth:`update`;
    concurrent callers use :meth:`handle_response_on`.
    """

    def __init__(
        self,
        schedule: Schedule,
        exit_condition: ExitCondition | None = None,
        default_reinforcer_value: float = 1.0,
    ) -> None:
        self.state: SessionState = SessionState.IDLE
        self.schedule: Schedule = schedule
        self.exit_condition: ExitCondition | None = exit_condition
        self.events: list[SessionEvent] = []
        self.observation: Observation = Observation()
        self.reinforcement_count: int = 0
        self._last_reinforcement_responses: int = 0
        self.reinforcement_history: list[tuple[float, float]] = []
        self.start_time: float | None = None
        self._last_reinforcement_time: float = 0.0

        # Delay of Reinforcement related.
        self.delay_function: DelayFunction = DelayFunction()
        self.default_reinforcer_value: float = default_reinforcer_value

        # Timestamp of the response that triggered the most-recent (pending)
        # reinforcement. Used to compute delay-to-delivery when reinforcement
        # actually starts on a later update tick.
        self._pending_trigger_timestamp: float | None = None

        # --- Concurrent (multi-operandum) bookkeeping ----------------
        self._is_concurrent: bool = _is_contingency_concurrent(schedule)
        self._concurrent_component_keys: list[str] = (
            list(schedule.components.keys())  # type: ignore[attr-defined]
            if self._is_concurrent
            else []
        )
        n_components = len(self._concurrent_component_keys)
        self._component_responses: list[int] = [0] * n_components
        self._last_reinforcement_responses_per: list[int] = [0] * n_components
        self._last_reinforcement_time_per: list[float] = [0.0] * n_components

        # Operandum (string key) of the in-flight response on the current
        # update tick. Populated by :meth:`handle_response_on` and consumed
        # by :meth:`update`.
        self._pending_response_operandum: str | None = None
        # Integer operandum index of the same in-flight response, used to
        # tag ``ReinforcerStartEvent`` / ``ReinforcerEndEvent``.
        self._last_intended_operandum: int | None = None
        # The operandum index of the most recent reinforcement (used to tag
        # the matching ``ReinforcerEndEvent``).
        self._last_reinforced_operandum: int | None = None

    def start(self, timestamp: float) -> None:
        """Begin the session. No-op if not in :attr:`SessionState.IDLE`."""
        if self.state == SessionState.IDLE:
            self.start_time = timestamp
            self._last_reinforcement_time = timestamp
            if self._is_concurrent:
                self._last_reinforcement_time_per = [timestamp] * len(
                    self._last_reinforcement_time_per
                )
            self._transition_to(SessionState.RUNNING, timestamp)

    def handle_response_on(self, operandum: int, timestamp: float) -> None:
        """Record a response on a specific operandum (concurrent only).

        Callers driving a single-component session should keep using
        :meth:`update`. This method is invoked by runners that dispatch
        responses to one of several operanda on a
        :class:`contingency.schedules.concurrent.Concurrent` schedule.
        """
        if not self._is_concurrent:
            raise ValueError(
                "handle_response_on requires a concurrent schedule; "
                "use update() for single-component sessions."
            )
        if not (0 <= operandum < len(self._component_responses)):
            raise IndexError(
                f"operandum {operandum} out of range "
                f"(n_components={len(self._component_responses)})"
            )
        self._component_responses[operandum] += 1
        self._pending_response_operandum = self._concurrent_component_keys[operandum]
        self._last_intended_operandum = operandum

        # Drive the schedule evaluation with the updated total.
        total = sum(self._component_responses)
        self.update(timestamp, total)

    def update(self, timestamp: float, total_responses: int) -> None:
        """Advance the session to ``timestamp`` with ``total_responses`` accrued."""
        # While a reinforcement is in progress (between ReinforcerStartEvent
        # and ReinforcerEndEvent) subsequent update() calls "refine" the
        # pending reinforcement by updating its event timestamp and potency
        # to reflect the delay between the triggering response and the
        # actual delivery time.
        if self.state == SessionState.REINFORCING:
            if self._pending_trigger_timestamp is None:
                return
            if total_responses == self.observation.total_responses:
                delay_duration = timestamp - self._pending_trigger_timestamp
                if delay_duration < 0:
                    delay_duration = 0.0
                potency = self.delay_function.calculate_potency(delay_duration, is_signaled=False)
                for evt in reversed(self.events):
                    if isinstance(evt, ReinforcerStartEvent):
                        evt.timestamp = timestamp
                        evt.potency = potency
                        break
                if self.reinforcement_history:
                    count = self.reinforcement_history[-1][1]
                    self.reinforcement_history[-1] = (timestamp, count)
            return

        if self.state != SessionState.RUNNING:
            return

        # Check exit conditions.
        if self.exit_condition:
            if isinstance(self.exit_condition, ReinforcementCountExit):
                if self.reinforcement_count >= self.exit_condition.count:
                    self._transition_to(SessionState.FINISHED, timestamp)
                    return
            elif isinstance(self.exit_condition, TimeLimitExit):
                if timestamp - self.events[0].timestamp >= self.exit_condition.limit:
                    self._transition_to(SessionState.FINISHED, timestamp)
                    return

        is_new_response = total_responses > self.observation.total_responses

        self.observation.current_time = timestamp
        self.observation.total_responses = total_responses
        self.observation.time_since_last_reinforcement = timestamp - self._last_reinforcement_time
        self.observation.responses_since_last_reinforcement = (
            total_responses - self._last_reinforcement_responses
        )
        if is_new_response:
            self.observation.last_response_timestamp = timestamp
            self.observation.timestamp_of_triggering_response = timestamp

        if self._is_concurrent:
            self.observation.component_responses = [
                c - r
                for c, r in zip(
                    self._component_responses,
                    self._last_reinforcement_responses_per,
                    strict=True,
                )
            ]
            self.observation.component_time_since_reinforcement = [
                timestamp - t for t in self._last_reinforcement_time_per
            ]
            op_key = self._pending_response_operandum
            self._pending_response_operandum = None
            reinforced = _step_satisfied(
                self.schedule,
                timestamp,
                is_new_response,
                operandum=op_key or "main",
            )
            idx = self._last_intended_operandum if reinforced else None
            if idx is not None:
                self._start_reinforcement(timestamp, operandum=idx)
            return

        if _step_satisfied(self.schedule, timestamp, is_new_response):
            self._start_reinforcement(timestamp, operandum=None)

    def _start_reinforcement(self, timestamp: float, operandum: int | None) -> None:
        trigger_ts = self.observation.timestamp_of_triggering_response
        self._pending_trigger_timestamp = trigger_ts
        delay_duration = max(0.0, timestamp - trigger_ts)
        potency = self.delay_function.calculate_potency(delay_duration, is_signaled=False)

        self.reinforcement_count += 1
        self.reinforcement_history.append((timestamp, self.reinforcement_count))
        self._last_reinforced_operandum = operandum
        self.events.append(
            ReinforcerStartEvent(
                self.reinforcement_count,
                timestamp,
                operandum=operandum,
                potency=potency,
            )
        )
        self._transition_to(SessionState.REINFORCING, timestamp)

    def end_reinforcement(self, timestamp: float) -> None:
        """Conclude the current reinforcer delivery and return to RUNNING."""
        if self.state == SessionState.REINFORCING:
            op = self._last_reinforced_operandum if self._is_concurrent else None
            self.events.append(
                ReinforcerEndEvent(self.reinforcement_count, timestamp, operandum=op)
            )
            self._last_reinforcement_time = timestamp
            self._last_reinforcement_responses = self.observation.total_responses
            if self._is_concurrent and op is not None:
                self._last_reinforcement_time_per[op] = timestamp
                self._last_reinforcement_responses_per[op] = self._component_responses[op]
            self._last_reinforced_operandum = None
            self._pending_trigger_timestamp = None
            self._transition_to(SessionState.RUNNING, timestamp)
            # Re-evaluate the exit condition immediately so callers do not
            # need to issue an extra response/tick to discover that the
            # session is over.
            self.update(timestamp, self.observation.total_responses)

    def _transition_to(self, next_state: SessionState, timestamp: float) -> None:
        """Change session state and emit a :class:`StateChangeEvent`."""
        from_state = self.state
        self.state = next_state
        self.events.append(StateChangeEvent(from_state, next_state, timestamp))

    def get_reinforcement_rate(self, current_time: float, window: float | None = None) -> float:
        """Calculate reinforcement rate (reinforcers/min) over a window or entire session."""
        if self.start_time is None or not self.reinforcement_history:
            return 0.0

        relevant_history = self.reinforcement_history
        if window:
            relevant_history = [
                h for h in self.reinforcement_history if current_time - h[0] <= window
            ]

        if not relevant_history:
            return 0.0

        duration_sec = current_time - max(
            self.start_time,
            current_time - window if window else self.start_time,
        )
        if duration_sec <= 0:
            return 0.0

        count = len(relevant_history)
        return (count / duration_sec) * 60.0

    def get_behavioral_momentum(self, current_time: float, sensitivity: float = 1.0) -> float:
        """Estimate behavioral momentum (mass) using BMT.

        ``mass = reinforcement_rate ** sensitivity``.

        Nevin, J. A. (1992). An integrative model for the study of behavioral momentum.
        Journal of the Experimental Analysis of Behavior, 57(3), 301-316.
        https://doi.org/10.1901/JEAB.1992.57-301
        """
        rate = self.get_reinforcement_rate(current_time)
        return rate**sensitivity

    def get_effective_reinforcement_rate(
        self, current_time: float, window: float | None = None
    ) -> float:
        """Calculate the effective reinforcement rate (effective reinforcers/min).

        Each reinforcer's contribution is weighted by its potency.
        """
        if self.start_time is None or not self.events:
            return 0.0

        relevant_reinforcers: list[ReinforcerStartEvent] = []
        for event in self.events:
            if isinstance(event, ReinforcerStartEvent):
                if window is None or (current_time - window <= event.timestamp <= current_time):
                    relevant_reinforcers.append(event)

        if not relevant_reinforcers:
            return 0.0

        effective_reinforcement_count = sum(event.potency for event in relevant_reinforcers)

        if window:
            duration_sec = window
        else:
            min_event_time = min(e.timestamp for e in relevant_reinforcers)
            duration_sec = current_time - min(self.start_time, min_event_time)

        if duration_sec <= 0:
            return 0.0

        return (effective_reinforcement_count / duration_sec) * 60.0
