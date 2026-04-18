"""Tests for :class:`experiment_core.Observation`."""

import pytest

from experiment_core import Observation


@pytest.mark.unit
def test_observation_default_values() -> None:
    obs = Observation()
    assert obs.total_responses == 0
    assert obs.responses_since_last_reinforcement == 0
    assert obs.current_time == 0.0
    assert obs.time_since_last_reinforcement == 0.0
    assert obs.last_response_timestamp == 0.0
    assert obs.component_responses == []
    assert obs.component_time_since_reinforcement == []
    assert obs.timestamp_of_triggering_response == 0.0


@pytest.mark.unit
def test_observation_component_fields_mutable() -> None:
    obs = Observation()
    obs.component_responses.append(3)
    obs.component_time_since_reinforcement.append(1.5)
    assert obs.component_responses == [3]
    assert obs.component_time_since_reinforcement == [1.5]


@pytest.mark.unit
def test_observation_component_fields_are_independent_instances() -> None:
    # default_factory must give each instance its own list (not a shared one).
    a = Observation()
    b = Observation()
    a.component_responses.append(1)
    assert b.component_responses == []


@pytest.mark.unit
def test_observation_dataclass_usable_via_kwargs() -> None:
    obs = Observation(
        total_responses=5,
        responses_since_last_reinforcement=2,
        current_time=1.25,
        component_responses=[1, 1],
    )
    assert obs.total_responses == 5
    assert obs.responses_since_last_reinforcement == 2
    assert obs.current_time == 1.25
    assert obs.component_responses == [1, 1]
