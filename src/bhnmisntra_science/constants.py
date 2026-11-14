"""
BHnMISnTRA: Member 1 Data & Scientific Intelligence
PRD-Mandated Immutable Scientific Constants.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _PRDConstants:
    """
    Immutable container for non-negotiable PRD-mandated constants.
    Runtime immutability is guaranteed via frozen dataclass with slots.
    """
    MIN_SUBSEQUENT_FOR_SUPPORTED: int = 3
    SUSTAINED_NUMERATOR: int = 2
    SUSTAINED_DENOMINATOR: int = 3
    SUSTAINED_RATIO: float = 2.0 / 3.0


PRD_CONSTANTS = _PRDConstants()

