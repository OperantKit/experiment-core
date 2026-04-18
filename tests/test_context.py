import pytest

from experiment_core.context import ExperimentContext


class TestExperimentContextEquality:
    def test_same_id_and_features_are_equal(self):
        a = ExperimentContext("A", {"color": 0.8, "odor": 0.5})
        b = ExperimentContext("A", {"color": 0.8, "odor": 0.5})
        assert a == b

    def test_different_id_not_equal(self):
        a = ExperimentContext("A", {"color": 0.8})
        b = ExperimentContext("B", {"color": 0.8})
        assert a != b

    def test_frozen_immutable(self):
        ctx = ExperimentContext("A", {"color": 0.8})
        with pytest.raises((AttributeError, TypeError)):
            ctx.id = "B"  # type: ignore[misc]


class TestExperimentContextSimilarity:
    def test_identical_context_similarity_is_one(self):
        ctx = ExperimentContext("A", {"color": 0.8, "odor": 0.5})
        assert ctx.similarity(ctx) == pytest.approx(1.0)

    def test_same_features_different_ids_similarity_is_one(self):
        a = ExperimentContext("A", {"color": 0.8})
        b = ExperimentContext("B", {"color": 0.8})
        assert a.similarity(b) == pytest.approx(1.0)

    def test_orthogonal_features_similarity_is_zero(self):
        a = ExperimentContext("A", {"color": 1.0})
        b = ExperimentContext("B", {"odor": 1.0})
        assert a.similarity(b) == pytest.approx(0.0)

    def test_no_shared_keys_similarity_is_zero(self):
        a = ExperimentContext("A", {"color": 0.9})
        b = ExperimentContext("B", {"noise": 0.7})
        assert a.similarity(b) == pytest.approx(0.0)

    def test_empty_features_similarity_is_zero(self):
        a = ExperimentContext("A", {})
        b = ExperimentContext("B", {})
        assert a.similarity(b) == pytest.approx(0.0)

    def test_symmetry(self):
        a = ExperimentContext("A", {"color": 0.8, "odor": 0.3})
        b = ExperimentContext("B", {"color": 0.2, "odor": 0.9})
        assert a.similarity(b) == pytest.approx(b.similarity(a))

    def test_similarity_bounded_zero_to_one(self):
        a = ExperimentContext("A", {"color": 0.8, "odor": 0.5})
        b = ExperimentContext("B", {"color": 0.2, "noise": 0.7})
        sim = a.similarity(b)
        assert 0.0 <= sim <= 1.0

    def test_partial_feature_overlap(self):
        # Shared key: color=1.0 in both; a has extra odor, b has extra noise
        a = ExperimentContext("A", {"color": 1.0, "odor": 0.0})
        b = ExperimentContext("B", {"color": 1.0, "noise": 0.0})
        # Both vectors have only color contributing non-zero → similarity = 1.0
        assert a.similarity(b) == pytest.approx(1.0)

    def test_all_zero_features_similarity_is_zero(self):
        a = ExperimentContext("A", {"color": 0.0, "odor": 0.0})
        b = ExperimentContext("B", {"color": 0.0, "odor": 0.0})
        assert a.similarity(b) == pytest.approx(0.0)
