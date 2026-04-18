"""Functions and classes for modeling the effects of delay of reinforcement.

All time values are canonical seconds (float).
"""

import math
from dataclasses import dataclass


@dataclass
class DelayFunction:
    """Calculates the effective potency of a reinforcer based on delay.

    Attributes
    ----------
    base_k : float
        The base decay rate for the exponential decay model. Higher values mean
        steeper decay with delay (more sensitive to delay).
    signal_factor : float
        Factor by which base_k is reduced when a signal is present (0.0 to 1.0).
        A value of 0.5 means the decay rate is halved with a signal.
    individual_sensitivity : float
        A multiplier for base_k to model individual differences in delay
        sensitivity. Higher values mean steeper decay.
    """

    base_k: float = 0.5
    signal_factor: float = 0.5
    individual_sensitivity: float = 1.0

    def calculate_potency(self, delay_duration: float, is_signaled: bool) -> float:
        """Calculate the effective potency of a reinforcer.

        Parameters
        ----------
        delay_duration : float
            Duration (seconds) between the triggering response and the
            reinforcer delivery.
        is_signaled : bool
            ``True`` if a signaling stimulus is present during the delay.

        Returns
        -------
        float
            The effective potency of the reinforcer, bounded to ``[0.0, 1.0]``.
        """
        adjusted_k = self.base_k * self.individual_sensitivity
        if is_signaled:
            adjusted_k *= self.signal_factor

        potency = math.exp(-adjusted_k * delay_duration)
        return max(0.0, min(1.0, potency))
