"""Test fakes: hand-rolled Schedule / ConcurrentSchedule conformers.

These live outside ``src/`` so they do not ship with the package.
"""

from dataclasses import dataclass, field

from experiment_core import Observation


@dataclass
class FakeFR:
    """Fake fixed-ratio schedule: satisfied after ``target`` responses."""

    target: int = 1

    def is_satisfied(self, obs: Observation) -> bool:
        return obs.responses_since_last_reinforcement >= self.target

    def next(self) -> None:  # pragma: no cover - trivial
        return None


@dataclass
class FakeConcurrent:
    """Fake concurrent schedule: per-component FR targets."""

    targets: list[int]
    responses_by_operandum: list[tuple[int, float]] = field(default_factory=list)

    @property
    def n_components(self) -> int:
        return len(self.targets)

    def which_satisfied(self, obs: Observation) -> int | None:
        for i, t in enumerate(self.targets):
            if i < len(obs.component_responses) and obs.component_responses[i] >= t:
                return i
        return None

    def next(self) -> None:  # pragma: no cover - trivial
        return None

    def note_response_on(self, operandum: int, timestamp: float) -> None:
        self.responses_by_operandum.append((operandum, timestamp))
