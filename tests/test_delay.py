"""Tests for :class:`experiment_core.DelayFunction`."""

import math

import pytest

from experiment_core import DelayFunction

ABS_TOL = 1e-9


@pytest.mark.unit
def test_zero_delay_gives_full_potency() -> None:
    df = DelayFunction()
    assert math.isclose(df.calculate_potency(0.0, is_signaled=False), 1.0, abs_tol=ABS_TOL)


@pytest.mark.unit
def test_large_delay_gives_small_potency() -> None:
    df = DelayFunction()
    potency = df.calculate_potency(50.0, is_signaled=False)
    assert potency < 1e-6


@pytest.mark.unit
def test_signal_reduces_decay_rate() -> None:
    df = DelayFunction()
    unsignaled = df.calculate_potency(2.0, is_signaled=False)
    signaled = df.calculate_potency(2.0, is_signaled=True)
    # A signal halves the effective k by default, so signaled > unsignaled.
    assert signaled > unsignaled


@pytest.mark.unit
@pytest.mark.parametrize("delay", [0.0, 0.1, 1.0, 5.0, 100.0])
def test_potency_bounds(delay: float) -> None:
    df = DelayFunction()
    for signaled in (False, True):
        p = df.calculate_potency(delay, is_signaled=signaled)
        assert 0.0 <= p <= 1.0


@pytest.mark.unit
def test_individual_sensitivity_steepens_decay() -> None:
    base = DelayFunction()
    steep = DelayFunction(individual_sensitivity=2.0)
    assert steep.calculate_potency(1.0, False) < base.calculate_potency(1.0, False)
