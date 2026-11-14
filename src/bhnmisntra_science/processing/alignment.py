"""
BHnMISnTRA: SAR Co-Registration & Spatial Alignment Validation.
"""

from dataclasses import dataclass
import math
from typing import Sequence
import numpy as np

from ..exceptions import RasterAlignmentError


@dataclass(frozen=True)
class AlignmentMetadata:
    """
    Immutable spatial reference and grid alignment metadata for a SAR raster.
    Transform follows standard GDAL / Affine 6-tuple convention:
    (a, b, c, d, e, f) where:
      X_geo = a + b * pixel_x + c * pixel_y
      Y_geo = d + e * pixel_x + f * pixel_y
    For north-up unrotated rasters:
      b = pixel_width, c = 0.0, e = 0.0, f = -pixel_height
    """
    shape: tuple[int, int]
    crs: str
    transform: tuple[float, float, float, float, float, float]
    resolution_meters: tuple[float, float]

    def __post_init__(self) -> None:
        if len(self.shape) != 2:
            raise ValueError(f"Shape must be a 2-tuple (height, width), got {self.shape}")
        if self.shape[0] <= 0 or self.shape[1] <= 0:
            raise ValueError(f"Shape dimensions must be positive integers, got {self.shape}")
        if not isinstance(self.crs, str) or not self.crs.strip():
            raise ValueError("CRS must be a non-empty string identifier (e.g. 'EPSG:4326')")
        if len(self.transform) != 6:
            raise ValueError(f"Transform must be a 6-tuple of floats, got length {len(self.transform)}")
        for i, val in enumerate(self.transform):
            if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val):
                raise ValueError(f"Transform element {i} must be finite float, got {val!r}")
        if len(self.resolution_meters) != 2:
            raise ValueError(f"Resolution must be a 2-tuple (res_x, res_y), got {self.resolution_meters}")
        if self.resolution_meters[0] <= 0 or self.resolution_meters[1] <= 0:
            raise ValueError(f"Resolution values must be positive numbers, got {self.resolution_meters}")


def validate_raster_alignment(
    alignments: Sequence[AlignmentMetadata],
    transform_tolerance: float = 1e-4,
) -> bool:
    """
    Verifies that all SAR acquisitions in a time-series or baseline-pair share
    an identical spatial grid, coordinate reference system, and affine geotransform.

    Raises RasterAlignmentError if any alignment invariant is violated.
    Returns True upon successful verification.
    """
    if not alignments or len(alignments) < 2:
        raise ValueError("Must provide at least two AlignmentMetadata instances to validate alignment.")

    ref = alignments[0]
    ref_crs = ref.crs.strip().upper()

    for idx, cand in enumerate(alignments[1:], start=1):
        # 1. Grid shape check
        if cand.shape != ref.shape:
            raise RasterAlignmentError(
                f"Raster grid shape mismatch between acquisition 0 {ref.shape} "
                f"and acquisition {idx} {cand.shape}. Resampling/co-registration required."
            )

        # 2. CRS check
        cand_crs = cand.crs.strip().upper()
        if cand_crs != ref_crs:
            raise RasterAlignmentError(
                f"Coordinate reference system mismatch: acquisition 0 is '{ref.crs}', "
                f"while acquisition {idx} is '{cand.crs}'."
            )

        # 3. Affine Transform check
        for param_idx, (t_ref, t_cand) in enumerate(zip(ref.transform, cand.transform)):
            diff = abs(t_ref - t_cand)
            if diff > transform_tolerance:
                raise RasterAlignmentError(
                    f"Geotransform mismatch at element {param_idx}: "
                    f"acquisition 0={t_ref:.7f}, acquisition {idx}={t_cand:.7f} "
                    f"(diff={diff:.7f} > tol={transform_tolerance}). Grid is not co-registered."
                )

    return True

