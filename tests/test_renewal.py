from dataclasses import dataclass

import pytest

from experiment_core import Observation
from experiment_core.context import ExperimentContext
from experiment_core.renewal import (
    ContextualSession,
    PhaseRecord,
    PhaseResult,
    RenewalExperiment,
    RenewalParadigm,
    renewal_index,
)
from tests._fakes import FakeFR


@dataclass
class FakeExtinction:
    """Fake extinction schedule: never satisfied."""

    def is_satisfied(self, obs: Observation) -> bool:
        return False

    def next(self) -> None:  # pragma: no cover - trivial
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ctx_a():
    return ExperimentContext("A", {"color": 1.0, "odor": 0.0})


@pytest.fixture
def ctx_b():
    return ExperimentContext("B", {"color": 0.0, "odor": 1.0})


@pytest.fixture
def ctx_c():
    return ExperimentContext("C", {"noise": 1.0})


# ---------------------------------------------------------------------------
# RenewalParadigm
# ---------------------------------------------------------------------------


class TestRenewalParadigm:
    def test_enum_values(self):
        assert RenewalParadigm.ABA.value == "aba"
        assert RenewalParadigm.AAB.value == "aab"
        assert RenewalParadigm.ABC.value == "abc"


# ---------------------------------------------------------------------------
# renewal_index (pure function)
# ---------------------------------------------------------------------------


class TestRenewalIndex:
    def test_aba_returns_positive(self, ctx_a, ctx_b):
        # sim(A,A) - sim(A,B) = 1.0 - 0.0 = 1.0
        assert renewal_index(ctx_a, ctx_b, ctx_a) == pytest.approx(1.0)

    def test_aab_returns_zero(self, ctx_a, ctx_b):
        # acquisition=A, extinction=A, test=B
        # sim(B,A) - sim(B,A) = 0.0
        assert renewal_index(ctx_a, ctx_a, ctx_b) == pytest.approx(0.0)

    def test_abc_all_orthogonal_returns_zero(self, ctx_a, ctx_b, ctx_c):
        # sim(C,A) = 0, sim(C,B) = 0 -> 0.0
        assert renewal_index(ctx_a, ctx_b, ctx_c) == pytest.approx(0.0)

    def test_identical_acquisition_and_extinction_returns_zero(self, ctx_a):
        assert renewal_index(ctx_a, ctx_a, ctx_a) == pytest.approx(0.0)

    def test_returns_negative_when_test_closer_to_extinction(self, ctx_a, ctx_b):
        # extinction context IS the test context (anti-renewal case)
        # sim(B,A) - sim(B,B) = 0.0 - 1.0 = -1.0
        assert renewal_index(ctx_a, ctx_b, ctx_b) == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# ContextualSession
# ---------------------------------------------------------------------------


class TestContextualSessionInit:
    def test_initial_context_stored(self, ctx_a):
        s = ContextualSession(FakeFR(5), initial_context=ctx_a)
        assert s.current_context == ctx_a

    def test_phase_log_empty_on_init(self, ctx_a):
        s = ContextualSession(FakeFR(5), initial_context=ctx_a)
        assert s.phase_log == []


class TestContextualSessionSwitchContext:
    def test_switch_updates_current_context(self, ctx_a, ctx_b):
        s = ContextualSession(FakeFR(5), initial_context=ctx_a)
        s.switch_context(ctx_b)
        assert s.current_context == ctx_b

    def test_switch_appends_phase_record(self, ctx_a, ctx_b):
        s = ContextualSession(FakeFR(5), initial_context=ctx_a)
        s.switch_context(ctx_b, timestamp=10.0)
        assert len(s.phase_log) == 1
        record = s.phase_log[0]
        assert record.context == ctx_b
        assert record.switched_at == pytest.approx(10.0)

    def test_multiple_switches_accumulate_in_log(self, ctx_a, ctx_b, ctx_c):
        s = ContextualSession(FakeFR(5), initial_context=ctx_a)
        s.switch_context(ctx_b, timestamp=5.0)
        s.switch_context(ctx_c, timestamp=10.0)
        assert len(s.phase_log) == 2
        assert s.phase_log[0].context == ctx_b
        assert s.phase_log[1].context == ctx_c


class TestContextualSessionRenewalIndex:
    def test_delegates_to_renewal_index_function(self, ctx_a, ctx_b):
        s = ContextualSession(FakeFR(5), initial_context=ctx_a)
        expected = renewal_index(ctx_a, ctx_b, ctx_a)
        assert s.renewal_index(ctx_a, ctx_b, ctx_a) == pytest.approx(expected)

    def test_aba_positive(self, ctx_a, ctx_b):
        s = ContextualSession(FakeFR(5), initial_context=ctx_a)
        assert s.renewal_index(ctx_a, ctx_b, ctx_a) > 0.0

    def test_aab_zero(self, ctx_a, ctx_b):
        s = ContextualSession(FakeFR(5), initial_context=ctx_a)
        assert s.renewal_index(ctx_a, ctx_a, ctx_b) == pytest.approx(0.0)


class TestContextualSessionInheritsSession:
    def test_can_start_and_update(self, ctx_a):
        s = ContextualSession(FakeFR(2), initial_context=ctx_a)
        s.start(0.0)
        s.update(1.0, 1)
        s.update(2.0, 2)
        assert s.reinforcement_count == 1


# ---------------------------------------------------------------------------
# PhaseRecord / PhaseResult
# ---------------------------------------------------------------------------


class TestPhaseRecord:
    def test_fields(self, ctx_a):
        rec = PhaseRecord(context=ctx_a, switched_at=5.0)
        assert rec.context == ctx_a
        assert rec.switched_at == pytest.approx(5.0)


class TestPhaseResult:
    def test_fields(self, ctx_a):
        result = PhaseResult(
            phase="acquisition",
            context=ctx_a,
            n_responses=20,
            n_reinforcements=4,
        )
        assert result.phase == "acquisition"
        assert result.n_responses == 20
        assert result.n_reinforcements == 4


# ---------------------------------------------------------------------------
# RenewalExperiment.predict_renewal
# ---------------------------------------------------------------------------


class TestRenewalExperimentPredictRenewal:
    def test_aba_positive(self, ctx_a, ctx_b):
        exp = RenewalExperiment(
            paradigm=RenewalParadigm.ABA,
            contexts={"A": ctx_a, "B": ctx_b},
        )
        assert exp.predict_renewal() > 0.0

    def test_aab_zero(self, ctx_a, ctx_b):
        exp = RenewalExperiment(
            paradigm=RenewalParadigm.AAB,
            contexts={"A": ctx_a, "B": ctx_b},
        )
        assert exp.predict_renewal() == pytest.approx(0.0)

    def test_abc_orthogonal_zero(self, ctx_a, ctx_b, ctx_c):
        exp = RenewalExperiment(
            paradigm=RenewalParadigm.ABC,
            contexts={"A": ctx_a, "B": ctx_b, "C": ctx_c},
        )
        assert exp.predict_renewal() == pytest.approx(0.0)

    def test_aba_symmetric_contexts_gives_max_renewal(self, ctx_a, ctx_b):
        exp = RenewalExperiment(
            paradigm=RenewalParadigm.ABA,
            contexts={"A": ctx_a, "B": ctx_b},
        )
        assert exp.predict_renewal() == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# RenewalExperiment.run_phase
# ---------------------------------------------------------------------------


class TestRenewalExperimentRunPhase:
    def test_run_phase_returns_phase_result(self, ctx_a, ctx_b):
        exp = RenewalExperiment(
            paradigm=RenewalParadigm.ABA,
            contexts={"A": ctx_a, "B": ctx_b},
        )
        result = exp.run_phase("acquisition", "A", FakeFR(5), n_responses=20)
        assert isinstance(result, PhaseResult)
        assert result.phase == "acquisition"
        assert result.context == ctx_a

    def test_run_phase_counts_reinforcements(self, ctx_a, ctx_b):
        exp = RenewalExperiment(
            paradigm=RenewalParadigm.ABA,
            contexts={"A": ctx_a, "B": ctx_b},
        )
        result = exp.run_phase("acquisition", "A", FakeFR(5), n_responses=15)
        assert result.n_reinforcements == 3
        assert result.n_responses == 15

    def test_extinction_phase_gives_zero_reinforcements(self, ctx_a, ctx_b):
        exp = RenewalExperiment(
            paradigm=RenewalParadigm.ABA,
            contexts={"A": ctx_a, "B": ctx_b},
        )
        result = exp.run_phase("extinction", "B", FakeExtinction(), n_responses=20)
        assert result.n_reinforcements == 0

    def test_run_phase_updates_session_context(self, ctx_a, ctx_b):
        exp = RenewalExperiment(
            paradigm=RenewalParadigm.ABA,
            contexts={"A": ctx_a, "B": ctx_b},
        )
        exp.run_phase("acquisition", "A", FakeFR(5), n_responses=5)
        exp.run_phase("extinction", "B", FakeExtinction(), n_responses=5)
        assert exp.session is not None
        assert exp.session.current_context == ctx_b
