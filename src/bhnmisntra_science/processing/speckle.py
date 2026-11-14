"""
BHnMISnTRA: SAR Speckle Filtering & Logarithmic Bias Prevention.
"""

import math
from typing import Literal
import numpy as np
from scipy import ndimage

from ..exceptions import ProcessingError


SpeckleFilterType = Literal["boxcar", "lee", "median", "none"]


def apply_speckle_filter(
    arr: np.ndarray,
    filter_name: SpeckleFilterType = "boxcar",
    window_size: int = 5,
    is_db: bool = True,
    equivalent_looks: float = 4.0,
    nodata_mask: np.ndarray | None = None,
    linear_floor_epsilon: float = 1e-7,
) -> np.ndarray:
    """
    Applies spatial speckle reduction to SAR data.

    CRITICAL SCIENTIFIC PRINCIPLE - LOGARITHMIC BIAS PREVENTION:
    If `is_db` is True, the input is in decibels (10*log10(sigma0)).
    Spatial averaging directly in dB produces a downward bias of up to 2.5 dB
    because E[log(X)] != log(E[X]) for speckle distributions.
    This function strictly:
      1. Transforms dB -> Linear Power: P = 10^(dB / 10)
      2. Performs spatial filtering on Linear Power
      3. Transforms back Linear Power -> dB: 10 * log10(max(P_filt, epsilon))

    Args:
        arr: 2D SAR array.
        filter_name: "boxcar", "lee", "median", or "none".
        window_size: Odd integer >= 3 (e.g. 3, 5, 7).
        is_db: True if input is in dB; False if linear power.
        equivalent_looks: Equivalent Number of Looks (ENL) for Lee filter (default 4.0 for Sentinel-1 GRD).
        nodata_mask: Optional boolean mask where True indicates invalid/nodata pixels.
        linear_floor_epsilon: Minimum linear power floor before log10.

    Returns:
        Filtered 2D float32 numpy array matching input units.
    """
    if not isinstance(arr, np.ndarray) or arr.ndim != 2:
        raise ProcessingError(f"Expected 2D numpy array, got {type(arr)} with shape {getattr(arr, 'shape', None)}")
    if arr.size == 0:
        raise ProcessingError("Cannot filter empty array")

    if filter_name == "none":
        return arr.astype(np.float32, copy=True)

    if not isinstance(window_size, int) or isinstance(window_size, bool):
        raise ProcessingError(f"window_size must be an integer, got {window_size!r}")
    if window_size < 3 or window_size % 2 == 0:
        raise ProcessingError(f"window_size must be an odd integer >= 3, got {window_size}")

    if not math.isfinite(equivalent_looks) or equivalent_looks <= 0.0:
        raise ProcessingError(f"equivalent_looks must be a finite positive number, got {equivalent_looks}")

    # Build mask of valid pixels
    if nodata_mask is not None:
        if nodata_mask.shape != arr.shape:
            raise ProcessingError(f"nodata_mask shape {nodata_mask.shape} does not match arr {arr.shape}")
        valid_mask = (~nodata_mask) & np.isfinite(arr)
    else:
        valid_mask = np.isfinite(arr)

    if not np.any(valid_mask):
        raise ProcessingError("Array has zero valid pixels to filter")

    data = arr.astype(np.float64, copy=True)

    # 1. Convert to linear power if is_db
    if is_db:
        # P = 10^(dB / 10)
        linear = np.zeros_like(data)
        linear[valid_mask] = np.power(10.0, data[valid_mask] / 10.0)
    else:
        linear = np.maximum(data, 0.0)

    # Prepare normalized convolution weights for boundaries and nodata
    weights = valid_mask.astype(np.float64)
    weighted_linear = linear * weights

    # 2. Execute selected filter on Linear Power
    if filter_name == "boxcar":
        # Normalized uniform boxcar filter
        sum_linear = ndimage.uniform_filter(weighted_linear, size=window_size, mode="reflect")
        sum_weights = ndimage.uniform_filter(weights, size=window_size, mode="reflect")
        safe_weights = np.maximum(sum_weights, 1e-8)
        filtered_linear = np.where(sum_weights > 0.05, sum_linear / safe_weights, linear)

    elif filter_name == "lee":
        # Standard Lee Filter:
        # Var_noise = 1 / ENL
        # local_mean = uniform_filter(I)
        # local_var = uniform_filter(I^2) - local_mean^2
        # W = max(0, (local_var - Var_noise * local_mean^2) / (local_var * (1 + Var_noise)))
        # I_filtered = local_mean + W * (I - local_mean)
        var_noise = 1.0 / equivalent_looks

        sum_w = ndimage.uniform_filter(weights, size=window_size, mode="reflect")
        safe_w = np.maximum(sum_w, 1e-8)

        local_mean = ndimage.uniform_filter(weighted_linear, size=window_size, mode="reflect") / safe_w
        local_sq_mean = ndimage.uniform_filter(weighted_linear ** 2, size=window_size, mode="reflect") / safe_w
        local_var = np.maximum(0.0, local_sq_mean - (local_mean ** 2))

        # Noise variance based on local mean
        noise_var = var_noise * (local_mean ** 2)

        # Weight calculation with numerical stability
        denom = local_var * (1.0 + var_noise)
        safe_denom = np.maximum(denom, 1e-12)
        weight = np.where(
            denom > 1e-12,
            np.clip((local_var - noise_var) / safe_denom, 0.0, 1.0),
            0.0,
        )

        filtered_linear = local_mean + weight * (linear - local_mean)
        filtered_linear = np.where(sum_w > 0.05, filtered_linear, linear)

    elif filter_name == "median":
        # Spatial median on valid linear data
        filtered_linear = ndimage.median_filter(linear, size=window_size, mode="reflect")

    else:
        raise ProcessingError(f"Unsupported speckle filter: {filter_name}")

    # 3. Convert back to dB if requested
    if is_db:
        safe_linear = np.maximum(filtered_linear, linear_floor_epsilon)
        out = 10.0 * np.log10(safe_linear)
    else:
        out = filtered_linear

    # Preserve NaN at nodata locations
    out[~valid_mask] = np.nan
    return out.astype(np.float32)

