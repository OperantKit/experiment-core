"""Session lifecycle and reinforcement bookkeeping.

All time values are canonical seconds (float).
"""

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
from .protocols import ConcurrentSchedule, Schedule


def _is_concurrent_schedule(schedule: object) -> bool:
    """Structural check for ConcurrentSchedule protocol conformance.

    ``typing.Protocol`` ``isinstance`` checks only inspect attribute presence,
    so we match the same semantics explicitly via ``hasattr``.
    """
    return hasattr(schedule, "n_components") and hasattr(schedule, "which_satisfied")


def _is_contingency_schedule(schedule: object) -> bool:
    """Structural check for a :mod:`contingency` schedule.

    Single-component ``contingency`` schedules expose ``step(now, event)
    -> Outcome`` + ``reset()`` (see :mod:`contingency.interfaces`). They
    do not expose ``is_satisfied`` / ``next``. Compound concurrent
    schedules from ``contingency.schedules.concurrent.Concurrent`` are
    plain schedules that additionally accept
    ``ResponseEvent.operandum`` — no separate ``ConcurrentSchedule``
    surface is needed here.
    """
    return (
        hasattr(schedule, "step")
        and hasattr(schedule, "reset")
        and not hasattr(schedule, "is_satisfied")
    )


def _contingency_step_satisfied(
    schedule: object,
    current_time: float,
    is_new_response: bool,
    operandum: str = "main",
) -> bool:
    """Invoke a ``contingency.Schedule.step`` and return its ``reinforced`` flag.

    This helper lets :class:`Session` drive both the legacy
    ``is_satisfied/next`` Protocol and the canonical ``contingency``
    step/reset API from the same update tick.

    ``operandum`` is threaded through so concurrent schedules can route
    the event to the correct component. Single-operandum callers use
    the default ``"main"``.
    """
    from contingency.entities import ResponseEvent as CResponseEvent

    event = CResponseEvent(time=current_time, operandum=operandum) if is_new_response else None
    outcome = schedule.step(current_time, event)  # type: ignore[attr-defined]
    return bool(outcome.reinforced)


class Session:
    """Single- or multi-component reinforcement session.

    The session owns an :class:`Observation`, a schedule, and an event log.
    Callers drive the session with :meth:`start`, :meth:`update` (and/or
    :meth:`handle_response_on` for concurrent schedules), and
    :meth:`end_reinforcement`.
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

        # Delay of Reinforcement related
        self.delay_function: DelayFunction = DelayFunction()
        self.default_reinforcer_value: float = default_reinforcer_value

        # Timestamp of the response that triggered the most-recent (pending)
        # reinforcement. Used to compute delay-to-delivery when
        # reinforcement actually starts on a later update tick.
        self._pending_trigger_timestamp: float | None = None

        # --- Concurrent (multi-operandum) bookkeeping ----------------
        # When ``schedule`` conforms to ConcurrentSchedule we maintain
        # per-component response counts and per-component last-reinforcement
        # times so the runner can drive the session via
        # :meth:`handle_response_on`. Single-component sessions leave
        # these untouched.
        self._is_concurrent: bool = _is_concurrent_schedule(schedule)
        n_components: int = schedule.n_components if self._is_concurrent else 0
        self._component_responses: list[int] = [0] * n_components
        self._last_reinforcement_responses_per: list[int] = [0] * n_components
        self._last_reinforcement_time_per: list[float] = [0.0] * n_components
        # The operandum index of the most recent reinforcement (used to
        # tag the matching ReinforcerEndEvent).
        self._last_reinforced_operandum: int | None = None

        # Schedule API dispatch flag: ``contingency.Schedule`` uses
        # ``step(now, event) -> Outcome`` whereas legacy ``experiment_core.
        # Schedule`` uses ``is_satisfied(observation)``. Both are supported
        # on the same code path during the SCOPE-alignment migration; see
        # ``~/.claude/plans/experiment-core-scope-alignment.md``.
        self._uses_contingency_api: bool = _is_contingency_schedule(schedule)

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
        responses to one of several operanda on a concurrent schedule.
        """
        if not self._is_concurrent:
            raise ValueError(
                "handle_response_on requires a ConcurrentSchedule; "
                "use update() for single-component sessions."
            )
        if not (0 <= operandum < len(self._component_responses)):
            raise IndexError(
                f"operandum {operandum} out of range "
                f"(n_components={len(self._component_responses)})"
            )
        self._component_responses[operandum] += 1
        # Notify the schedule for COD bookkeeping.
        concurrent: ConcurrentSchedule = self.schedule  # type: ignore[assignment]
        concurrent.note_response_on(operandum, timestamp)
        # Drive the schedule evaluation with the updated counts.
        total = sum(self._component_responses)
        self.update(timestamp, total)

    def update(self, timestamp: float, total_responses: int) -> None:
        """Advance the session to ``timestamp`` with ``total_responses`` accrued."""
        # While a reinforcement is in progress (between ReinforcerStartEvent
        # and ReinforcerEndEvent) subsequent update() calls "refine" the
        # pending reinforcement by updating its event timestamp and potency
        # to reflect the delay between the triggering response and the
        # actual delivery time. This models reinforcement-delay effects
        # where the reinforcer is committed at response time but delivered
        # after some latency.
        if self.state == SessionState.REINFORCING:
            if self._pending_trigger_timestamp is None:
                return
            # Only refine when no new response occurred on this tick,
            # i.e. this is a pure time advance toward reinforcement delivery.
            if total_responses == self.observation.total_responses:
                delay_duration = timestamp - self._pending_trigger_timestamp
                if delay_duration < 0:
                    delay_duration = 0.0
                potency = self.delay_function.calculate_potency(delay_duration, is_signaled=False)
                # Update the most recent ReinforcerStartEvent in place.
                for evt in reversed(self.events):
                    if isinstance(evt, ReinforcerStartEvent):
                        evt.timestamp = timestamp
                        evt.potency = potency
                        break
                # Keep reinforcement_history in sync.
                if self.reinforcement_history:
                    count = self.reinforcement_history[-1][1]
                    self.reinforcement_history[-1] = (timestamp, count)
            return

        if self.state != SessionState.RUNNING:
            return

        # Check Exit Conditions
        if self.exit_condition:
            if isinstance(self.exit_condition, ReinforcementCountExit):
                if self.reinforcement_count >= self.exit_condition.count:
                    self._transition_to(SessionState.FINISHED, timestamp)
                    return
            elif isinstance(self.exit_condition, TimeLimitExit):
                if timestamp - self.events[0].timestamp >= self.exit_condition.limit:
                    self._transition_to(SessionState.FINISHED, timestamp)
                    return

        # Detect whether this update carries a new response. The triggering
        # response timestamp is the time at which the satisfying response
        # occurred (used for delay-of-reinforcement calculations).
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
            concurrent: ConcurrentSchedule = self.schedule  # type: ignore[assignment]
            idx = concurrent.which_satisfied(self.observation)
            if idx is not None:
                # Calculate initial potency using the delay between the
                # triggering response and the current tick. For an update
                # where the triggering response arrived on the same tick
                # this is 0; subsequent refinement (see REINFORCING branch
                # above) will update the event if delivery is deferred.
                trigger_ts = self.observation.timestamp_of_triggering_response
                self._pending_trigger_timestamp = trigger_ts
                delay_duration = max(0.0, timestamp - trigger_ts)
                potency = self.delay_function.calculate_potency(delay_duration, is_signaled=False)

                self.reinforcement_count += 1
                self.reinforcement_history.append((timestamp, self.reinforcement_count))
                self._last_reinforced_operandum = idx
                self.events.append(
                    ReinforcerStartEvent(
                        self.reinforcement_count,
                        timestamp,
                        operandum=idx,
                        potency=potency,
                    )
                )
                self._transition_to(SessionState.REINFORCING, timestamp)
            return

        satisfied = (
            _contingency_step_satisfied(self.schedule, timestamp, is_new_response)
            if self._uses_contingency_api
            else self.schedule.is_satisfied(self.observation)
        )
        if satisfied:
            trigger_ts = self.observation.timestamp_of_triggering_response
            self._pending_trigger_timestamp = trigger_ts
            delay_duration = max(0.0, timestamp - trigger_ts)
            potency = self.delay_function.calculate_potency(delay_duration, is_signaled=False)

            self.reinforcement_count += 1
            self.reinforcement_history.append((timestamp, self.reinforcement_count))
            self.events.append(
                ReinforcerStartEvent(self.reinforcement_count, timestamp, potency=potency)
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
            if not self._uses_contingency_api:
                self.schedule.next()
            self._last_reinforced_operandum = None
            self._pending_trigger_timestamp = None
            self._transition_to(SessionState.RUNNING, timestamp)
            # Re-evaluate the exit condition immediately so callers do
            # not need to issue an extra response/tick to discover that
            # the session is over.
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

        Parameters
        ----------
        current_time : float
            The current timestamp for calculation.
        window : Optional[float]
            The time window (seconds) over which to calculate the rate.
            If ``None``, the rate is calculated over the entire session duration.

        Returns
        -------
        float
            The effective reinforcement rate (effective reinforcers per minute).
        """
        if self.start_time is None or not self.events:
            return 0.0

        relevant_reinforcers = []
        for event in self.events:
            if isinstance(event, ReinforcerStartEvent):
                if window is None or (current_time - window <= event.timestamp <= current_time):
                    relevant_reinforcers.append(event)

        if not relevant_reinforcers:
            return 0.0

        effective_reinforcement_count = sum(event.potency for event in relevant_reinforcers)

        duration_sec = 0.0
        if window:
            duration_sec = window
        else:
            duration_sec = current_time - self.start_time
            if self.start_time is not None:
                # Adjust duration for events before start_time if window is None
                min_event_time = (
                    min(e.timestamp for e in relevant_reinforcers)
                    if relevant_reinforcers
                    else self.start_time
                )
                duration_sec = current_time - min(self.start_time, min_event_time)

        if duration_sec <= 0:
            return 0.0

        return (effective_reinforcement_count / duration_sec) * 60.0
