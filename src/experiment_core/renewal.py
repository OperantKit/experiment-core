"""
Renewal — context-dependent relapse after extinction.

Bouton (1993, 2002) demonstrated that extinction learning is
context-specific: when the test context differs from the extinction
context, extinguished responding returns (renewal).  The asymmetry
between acquisition (context-general) and extinction (context-specific)
is captured by the renewal index:

    renewal_index = sim(test, acquisition) - sim(test, extinction)

Paradigms
---------
ABA  acquire in A, extinguish in B, test in A  -> renewal_index > 0
AAB  acquire in A, extinguish in A, test in B  -> renewal_index ~ 0
ABC  acquire in A, extinguish in B, test in C  -> renewal_index ~ 0

References
----------
Bouton, M. E. (1993). Context, time, and memory retrieval in the
    interference paradigms of Pavlovian learning. *Psychological Bulletin*,
    114(1), 80-99. https://doi.org/10.1037/0033-2909.114.1.80
Bouton, M. E. (2002). Context, ambiguity, and unlearning: Sources of
    relapse after behavioral extinction. *Biological Psychiatry*, 52(10),
    976-986. https://doi.org/10.1016/S0006-3223(02)01546-9
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .context import ExperimentContext
from .exit_condition import ExitCondition
from .protocols import Schedule
from .session import Session

# ---------------------------------------------------------------------------
# Paradigm enum
# ---------------------------------------------------------------------------


class RenewalParadigm(Enum):
    ABA = "aba"
    AAB = "aab"
    ABC = "abc"


# ---------------------------------------------------------------------------
# Pure renewal-index function
# ---------------------------------------------------------------------------


def renewal_index(
    acquisition_ctx: ExperimentContext,
    extinction_ctx: ExperimentContext,
    test_ctx: ExperimentContext,
) -> float:
    """Compute the renewal index for a given context triple.

    renewal_index = sim(test, acquisition) - sim(test, extinction)

    Positive values indicate renewal; negative values indicate that the
    test context is closer to the extinction context than the acquisition
    context (anti-renewal / enhanced extinction generalisation).
    """
    return test_ctx.similarity(acquisition_ctx) - test_ctx.similarity(extinction_ctx)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class PhaseRecord:
    """Records a context switch event."""

    context: ExperimentContext
    switched_at: float = 0.0


@dataclass
class PhaseResult:
    """Summary of a completed experimental phase."""

    phase: str
    context: ExperimentContext
    n_responses: int
    n_reinforcements: int


# ---------------------------------------------------------------------------
# ContextualSession
# ---------------------------------------------------------------------------


class ContextualSession(Session):
    """A :class:`~experiment_core.session.Session` extended with context tracking.

    Adds:
    - ``current_context`` - the background stimulus bundle currently active.
    - ``phase_log``        - ordered list of :class:`PhaseRecord` entries.
    - :meth:`switch_context` - update context and append to log.
    - :meth:`renewal_index`  - delegate to the module-level function.
    """

    def __init__(
        self,
        schedule: Schedule,
        initial_context: ExperimentContext,
        exit_condition: ExitCondition | None = None,
    ) -> None:
        super().__init__(schedule, exit_condition)
        self._current_context: ExperimentContext = initial_context
        self.phase_log: list[PhaseRecord] = []

    @property
    def current_context(self) -> ExperimentContext:
        return self._current_context

    def switch_context(self, ctx: ExperimentContext, timestamp: float = 0.0) -> None:
        """Switch to *ctx* and record the switch in :attr:`phase_log`."""
        self._current_context = ctx
        self.phase_log.append(PhaseRecord(context=ctx, switched_at=timestamp))

    def renewal_index(
        self,
        acquisition_ctx: ExperimentContext,
        extinction_ctx: ExperimentContext,
        test_ctx: ExperimentContext,
    ) -> float:
        """Renewal index for the supplied context triple."""
        return renewal_index(acquisition_ctx, extinction_ctx, test_ctx)


# ---------------------------------------------------------------------------
# RenewalExperiment
# ---------------------------------------------------------------------------


@dataclass
class RenewalExperiment:
    """Orchestrates ABA / AAB / ABC renewal experiments.

    Parameters
    ----------
    paradigm:
        Which renewal paradigm to use for :meth:`predict_renewal`.
    contexts:
        Mapping of context keys (``"A"``, ``"B"``, ``"C"``) to
        :class:`~experiment_core.context.ExperimentContext` instances.
    session:
        Shared :class:`ContextualSession` updated across phases.
        Created automatically on the first call to :meth:`run_phase`.
    """

    paradigm: RenewalParadigm
    contexts: dict[str, ExperimentContext]
    session: ContextualSession | None = field(default=None, repr=False)

    def predict_renewal(self) -> float:
        """Predict the renewal index based solely on context geometry.

        Uses the paradigm to assign acquisition / extinction / test roles:

        ====  ===========  ===========  ====
        Para  acquisition  extinction   test
        ====  ===========  ===========  ====
        ABA   A            B            A
        AAB   A            A            B
        ABC   A            B            C
        ====  ===========  ===========  ====
        """
        ctxs = self.contexts
        match self.paradigm:
            case RenewalParadigm.ABA:
                return renewal_index(ctxs["A"], ctxs["B"], ctxs["A"])
            case RenewalParadigm.AAB:
                return renewal_index(ctxs["A"], ctxs["A"], ctxs["B"])
            case RenewalParadigm.ABC:
                return renewal_index(ctxs["A"], ctxs["B"], ctxs["C"])

    def run_phase(
        self,
        phase: str,
        context_key: str,
        schedule: Schedule,
        n_responses: int,
    ) -> PhaseResult:
        """Simulate *n_responses* under *schedule* in the specified context.

        A new :class:`ContextualSession` is created on the first call and
        reused (with context switching) for subsequent phases.  Responses
        are fed as discrete events at integer timestamps (t = 0, 1, ...).

        Parameters
        ----------
        phase:
            Descriptive label (e.g. ``"acquisition"``, ``"extinction"``).
        context_key:
            Key into :attr:`contexts` (``"A"``, ``"B"``, or ``"C"``).
        schedule:
            The reinforcement schedule active during this phase.
        n_responses:
            Number of responses to simulate.

        Returns
        -------
        PhaseResult
            Summary including reinforcement count and response count.
        """
        ctx = self.contexts[context_key]

        # Initialise or reinitialise session for this phase's schedule.
        self.session = ContextualSession(schedule, initial_context=ctx)
        self.session.start(0.0)

        for i in range(1, n_responses + 1):
            self.session.update(float(i), i)
            if self.session.state.name == "REINFORCING":
                self.session.end_reinforcement(float(i))

        return PhaseResult(
            phase=phase,
            context=ctx,
            n_responses=n_responses,
            n_reinforcements=self.session.reinforcement_count,
        )
