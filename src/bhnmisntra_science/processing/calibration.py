"""
BHnMISnTRA: SAR Radiometric Calibration & State Machine.
"""

import math
from typing import Any
import numpy as np

from ..config import (
    CalibratedDbCalibration,
    CalibratedLinearCalibration,
    CalibrationMetadata,
    RawDnCalibration,
)
from ..enums import CalibrationState
from ..exceptions import AmbiguousCalibrationMetadataError, ScientificError


class CalibrationStateConflictError(ScientificError):
    """Raised when data values contradict declared calibration state (e.g. negative linear power)."""
    pass


def calibrate_sar_array(
    arr: np.ndarray,
    calibration: CalibrationMetadata,
    nodata_mask: np.ndarray | None = None,
    linear_floor_epsilon: float = 1e-7
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Calibrates a 2D SAR array to calibrated decibels (dB: 10*log10(sigma0)).
    Enforces product-aware calibration, double-calibration prevention, and provenance retention.

    Returns: (calibrated_db_array, calibration_provenance_record)
    """
    if not isinstance(arr, np.ndarray):
        raise TypeError(f"Expected numpy ndarray, got {type(arr).__name__}")
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D SAR array (height, width), got {arr.ndim}D shape: {arr.shape}")
    if arr.size == 0:
        raise ValueError("Cannot calibrate empty SAR array")

    data = arr.astype(np.float32, copy=True)
    if nodata_mask is not None:
        if nodata_mask.shape != data.shape:
            raise ValueError(f"nodata_mask shape {nodata_mask.shape} does not match data shape {data.shape}")
        valid_mask = ~nodata_mask
    else:
        valid_mask = np.isfinite(data)

    if not np.any(valid_mask):
        raise ValueError("Array contains zero valid (non-nodata/finite) pixels")

    valid_vals = data[valid_mask]
    provenance_record: dict[str, Any] = {
        "calibration_state": calibration.calibration_state.value,
        "source_doc": calibration.provenance.calibration_source_doc,
        "input_stats": {
            "min": float(np.min(valid_vals)),
            "max": float(np.max(valid_vals)),
            "mean": float(np.mean(valid_vals)),
        },
    }

    # =========================================================================
    # STATE 1: RAW DN (Digital Numbers needing calibration LUT / factor)
    # =========================================================================
    if isinstance(calibration, RawDnCalibration):
        # Double-calibration guard: Raw DN cannot have negative values
        if np.any(valid_vals < 0.0):
            raise CalibrationStateConflictError(
                f"Declared RAW_DN state contradicted by negative values (min={np.min(valid_vals)}). "
                f"Data appears to already be in logarithmic/dB units. Double-calibration prevented."
            )

        # Apply calibration equation
        # sigma0_linear = DN^2 (or DN if already amplitude/power scaled per documentation)
        if calibration.provenance.applied_scale == "dn_squared":
            linear_sigma = np.square(valid_vals)
        else:
            linear_sigma = valid_vals

        # Safe convert to dB
        safe_linear = np.maximum(linear_sigma, linear_floor_epsilon)
        db_vals = 10.0 * np.log10(safe_linear)

        data[valid_mask] = db_vals
        provenance_record["applied_equation"] = "10 * log10(max(DN^2, 1e-7))"
        provenance_record["lut_or_aux"] = calibration.provenance.lut_or_aux_file

    # =========================================================================
    # STATE 2: CALIBRATED LINEAR POWER (sigma0 or gamma0 in linear scale >= 0)
    # =========================================================================
    elif isinstance(calibration, CalibratedLinearCalibration):
        # Double-calibration guard: Linear power cross-section must be strictly >= 0
        if np.any(valid_vals < 0.0):
            raise CalibrationStateConflictError(
                f"Declared CALIBRATED_LINEAR_POWER state contradicted by negative values (min={np.min(valid_vals)}). "
                f"Data appears to already be in logarithmic/dB units. Double-calibration prevented."
            )

        scale_factor = float(calibration.provenance.calibration_factor)
        linear_scaled = valid_vals * scale_factor
        safe_linear = np.maximum(linear_scaled, linear_floor_epsilon)
        db_vals = 10.0 * np.log10(safe_linear)

        data[valid_mask] = db_vals
        provenance_record["applied_equation"] = f"10 * log10(max(linear * {scale_factor}, 1e-7))"
        provenance_record["declared_scale"] = calibration.provenance.declared_linear_scale

    # =========================================================================
    # STATE 3: CALIBRATED DECIBELS (sigma0 or gamma0 already in dB)
    # =========================================================================
    elif isinstance(calibration, CalibratedDbCalibration):
        # Sanity validation: dB values in Earth observation typically range between -60 dB and +20 dB
        # A mean > 100 strongly indicates raw uncalibrated DN, not decibels
        if np.mean(valid_vals) > 50.0:
            raise CalibrationStateConflictError(
                f"Declared CALIBRATED_DB state contradicted by excessively high values (mean={np.mean(valid_vals):.1f}). "
                f"Data appears to be uncalibrated digital numbers. Conversion blocked."
            )

        # Pass-through without re-applying logarithm
        provenance_record["applied_equation"] = "pass_through_calibrated_db (no recalibration)"
        provenance_record["decibel_reference"] = calibration.provenance.decibel_reference_scale

    else:
        raise AmbiguousCalibrationMetadataError(f"Unsupported calibration type: {type(calibration).__name__}")

    if nodata_mask is not None:
        data[nodata_mask] = np.nan

    provenance_record["output_stats_db"] = {
        "min": float(np.nanmin(data)),
        "max": float(np.nanmax(data)),
        "mean": float(np.nanmean(data)),
    }

    return data.astype(np.float32), provenance_record

