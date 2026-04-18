"""Tests for the :class:`Schedule` and :class:`ConcurrentSchedule` Protocols."""

import pytest

from experiment_core import ConcurrentSchedule, Observation, Schedule

from ._fakes import FakeConcurrent, FakeFR


@pytest.mark.unit
def test_fake_fr_conforms_to_schedule_protocol() -> None:
    sched = FakeFR(target=3)
    assert isinstance(sched, Schedule)


@pytest.mark.unit
def test_fake_fr_is_satisfied_semantics() -> None:
    sched = FakeFR(target=3)
    obs = Observation(responses_since_last_reinforcement=2)
    assert sched.is_satisfied(obs) is False
    obs = Observation(responses_since_last_reinforcement=3)
    assert sched.is_satisfied(obs) is True


@pytest.mark.unit
def test_fake_concurrent_conforms_to_concurrent_protocol() -> None:
    sched = FakeConcurrent(targets=[1, 2])
    assert isinstance(sched, ConcurrentSchedule)


@pytest.mark.unit
def test_fake_concurrent_which_satisfied() -> None:
    sched = FakeConcurrent(targets=[2, 3])
    obs = Observation(component_responses=[1, 0])
    assert sched.which_satisfied(obs) is None
    obs = Observation(component_responses=[2, 0])
    assert sched.which_satisfied(obs) == 0
    obs = Observation(component_responses=[0, 3])
    assert sched.which_satisfied(obs) == 1
