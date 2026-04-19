"""Tests for the :class:`Schedule` alias into ``contingency``."""

from __future__ import annotations

import pytest
from contingency import Schedule as ContingencySchedule
from contingency import ScheduleBuilder

from experiment_core import Schedule


@pytest.mark.unit
def test_schedule_is_contingency_schedule_alias() -> None:
    """``experiment_core.Schedule`` is the same class as ``contingency.Schedule``."""
    assert Schedule is ContingencySchedule


@pytest.mark.unit
def test_builder_fr_is_instance_of_schedule() -> None:
    sched = ScheduleBuilder.fr(1)
    assert isinstance(sched, Schedule)


@pytest.mark.unit
def test_builder_concurrent_is_instance_of_schedule() -> None:
    sched = ScheduleBuilder.concurrent({"a": ScheduleBuilder.fr(1), "b": ScheduleBuilder.fr(1)})
    assert isinstance(sched, Schedule)


@pytest.mark.unit
def test_concurrent_schedule_is_no_longer_exported() -> None:
    """``ConcurrentSchedule`` was removed from the public API."""
    with pytest.raises(ImportError):
        exec("from experiment_core import ConcurrentSchedule")
