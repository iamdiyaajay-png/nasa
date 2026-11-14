"""
BHnMISnTRA: SAR Signal Processing Core.
"""

from .calibration import calibrate_sar_array
from .alignment import validate_raster_alignment, AlignmentMetadata
from .speckle import apply_speckle_filter
from .log_ratio import (
    compute_log_ratio,
    create_spatial_tuning_mask,
    compute_threshold,
    generate_change_mask,
)

__all__ = [
    "calibrate_sar_array",
    "validate_raster_alignment",
    "AlignmentMetadata",
    "apply_speckle_filter",
    "compute_log_ratio",
    "create_spatial_tuning_mask",
    "compute_threshold",
    "generate_change_mask",
]

