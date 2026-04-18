"""
ExperimentContext — background stimulus bundle for renewal research.

In Bouton's (1993, 2002) framework, "context" refers to the set of
background stimuli (exteroceptive, temporal, interoceptive) that modulate
whether extinction learning generalises to a given test situation.
This module provides a minimal, hashable representation and a cosine
similarity metric used to quantify context overlap.

References
----------
Bouton, M. E. (1993). Context, time, and memory retrieval in the
    interference paradigms of Pavlovian learning. *Psychological Bulletin*,
    114(1), 80–99. https://doi.org/10.1037/0033-2909.114.1.80
Bouton, M. E. (2002). Context, ambiguity, and unlearning: Sources of
    relapse after behavioral extinction. *Biological Psychiatry*, 52(10),
    976–986. https://doi.org/10.1016/S0006-3223(02)01546-9
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ExperimentContext:
    """Immutable bundle of background stimulus features.

    Parameters
    ----------
    id:
        Human-readable label (e.g. ``"A"``, ``"extinction_chamber"``).
    features:
        Mapping of feature name → non-negative float intensity.
        Examples: ``{"color_hue": 0.3, "odor_intensity": 0.8}``.
        Missing keys are treated as 0.0 when computing similarity.
    """

    id: str
    features: dict[str, float]

    def similarity(self, other: ExperimentContext) -> float:
        """Cosine similarity between this context and *other*.

        Only feature keys present in *either* context contribute.
        Returns a value in ``[0.0, 1.0]``, where:
        - ``1.0`` means identical feature vectors
        - ``0.0`` means orthogonal (no shared feature activation) or
          either context has all-zero features.
        """
        all_keys = self.features.keys() | other.features.keys()
        if not all_keys:
            return 0.0

        dot = sum(self.features.get(k, 0.0) * other.features.get(k, 0.0) for k in all_keys)
        norm_self = math.sqrt(sum(v * v for v in self.features.values()))
        norm_other = math.sqrt(sum(v * v for v in other.features.values()))

        denom = norm_self * norm_other
        if denom == 0.0:
            return 0.0
        return dot / denom
