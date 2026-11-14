"""
BHnMISnTRA: SAR Log-Ratio Change Detection, Spatial Tuning Separation, & Sieving.
"""

import math
from typing import Any
import numpy as np
from scipy import ndimage

from ..config import (
    FixedDbThresholdConfig,
    OtsuThresholdConfig,
    RobustMadThresholdConfig,
    ThresholdConfig,
)
from ..enums import PhenomenonType
from ..exceptions import ProcessingError


def compute_log_ratio(
    comparison_db: np.ndarray,
    reference_db: np.ndarray,
    nodata_mask: np.ndarray | None = None,
) -> np.ndarray:
    """
    Computes the log-ratio change raster between comparison and reference SAR acquisitions:
    Delta sigma0_dB = sigma0_comp_dB - sigma0_ref_dB

    Because both inputs are in calibrated decibels (10*log10(sigma0)),
    Delta sigma0_dB = 10 * log10(sigma0_comp / sigma0_ref),
    computed via subtraction without ratio instability near zero.

    Returns:
        2D float32 numpy array of backscatter change in decibels (dB).
    """
    if not isinstance(comparison_db, np.ndarray) or not isinstance(reference_db, np.ndarray):
        raise TypeError("Both comparison_db and reference_db must be numpy ndarrays")
    if comparison_db.ndim != 2 or reference_db.ndim != 2:
        raise ProcessingError(f"Both arrays must be 2D, got comp={comparison_db.ndim}D, ref={reference_db.ndim}D")
    if comparison_db.shape != reference_db.shape:
        raise ProcessingError(
            f"Shape mismatch: comparison shape {comparison_db.shape} != reference shape {reference_db.shape}"
        )
    if comparison_db.size == 0:
        raise ProcessingError("Cannot compute log-ratio on empty arrays")

    diff_db = comparison_db.astype(np.float32) - reference_db.astype(np.float32)

    if nodata_mask is not None:
        if nodata_mask.shape != diff_db.shape:
            raise ProcessingError(f"nodata_mask shape {nodata_mask.shape} != diff shape {diff_db.shape}")
        diff_db[nodata_mask] = np.nan

    return diff_db


def create_spatial_tuning_mask(
    shape: tuple[int, int],
    split_ratio: float = 0.5,
    axis: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Creates disjoint spatial tuning and evaluation masks.

    CRITICAL SCIENTIFIC PRINCIPLE - DATA SNOOPING PREVENTION:
    Dynamic thresholds (Otsu, Robust MAD) must be computed on a spatially
    isolated tuning split to avoid circular threshold overfitting.
    The evaluation mask serves as the out-of-sample test region.

    Args:
        shape: 2-tuple (height, width).
        split_ratio: Fraction of grid along selected axis dedicated to tuning (0.1 to 0.9).
        axis: 0 for split along height (latitude), 1 for split along width (longitude).

    Returns:
        (tuning_mask, eval_mask): Disjoint boolean arrays where tuning_mask & eval_mask is False everywhere.
    """
    if len(shape) != 2 or shape[0] <= 0 or shape[1] <= 0:
        raise ValueError(f"Shape must be positive 2-tuple, got {shape}")
    if not isinstance(split_ratio, (int, float)) or isinstance(split_ratio, bool):
        raise TypeError(f"split_ratio must be a float, got {type(split_ratio).__name__}")
    if not (0.05 <= split_ratio <= 0.95):
        raise ValueError(f"split_ratio must be between 0.05 and 0.95, got {split_ratio}")
    if axis not in (0, 1):
        raise ValueError(f"axis must be 0 or 1, got {axis}")

    tuning_mask = np.zeros(shape, dtype=bool)
    eval_mask = np.zeros(shape, dtype=bool)

    dim_size = shape[axis]
    split_idx = max(1, min(dim_size - 1, int(round(dim_size * split_ratio))))

    if axis == 0:
        tuning_mask[:split_idx, :] = True
        eval_mask[split_idx:, :] = True
    else:
        tuning_mask[:, :split_idx] = True
        eval_mask[:, split_idx:] = True

    return tuning_mask, eval_mask


def compute_threshold(
    diff_db: np.ndarray,
    config: ThresholdConfig,
    tuning_mask: np.ndarray | None = None,
    phenomenon: PhenomenonType = PhenomenonType.FLOOD,
) -> float:
    """
    Computes change threshold in dB from log-ratio difference raster.

    Args:
        diff_db: 2D difference array (Delta sigma0 in dB).
        config: ThresholdConfig union (FixedDbThresholdConfig, RobustMadThresholdConfig, OtsuThresholdConfig).
        tuning_mask: Optional boolean mask restricting threshold tuning to a spatial subset.
        phenomenon: PhenomenonType. Default is FLOOD_INUNDATION (backscatter decrease).

    Returns:
        Threshold value in dB (float).
    """
    if not isinstance(diff_db, np.ndarray) or diff_db.ndim != 2:
        raise ProcessingError("diff_db must be a 2D numpy ndarray")

    # Fixed threshold does not inspect data; returns pre-registered parameter
    if isinstance(config, FixedDbThresholdConfig):
        return float(config.drop_threshold_db)

    # Isolate sample data for dynamic strategies
    if tuning_mask is not None:
        if tuning_mask.shape != diff_db.shape:
            raise ProcessingError(f"tuning_mask shape {tuning_mask.shape} != diff_db shape {diff_db.shape}")
        valid_sample = diff_db[tuning_mask & np.isfinite(diff_db)]
    else:
        valid_sample = diff_db[np.isfinite(diff_db)]

    if valid_sample.size < 10:
        raise ProcessingError(
            f"Insufficient valid tuning pixels ({valid_sample.size} < 10) to compute dynamic threshold."
        )

    # Strategy 2: Robust MAD
    if isinstance(config, RobustMadThresholdConfig):
        median_val = float(np.median(valid_sample))
        abs_dev = np.abs(valid_sample - median_val)
        mad_val = float(np.median(abs_dev))
        # Normal-consistent standard deviation scale factor: 1.4826
        normal_mad = 1.4826 * mad_val

        k = float(config.k_multiplier)
        if phenomenon in (PhenomenonType.FLOOD, PhenomenonType.CLEARING):
            # Water or clearing reduces backscatter -> threshold in negative tail
            threshold_db = median_val - (k * normal_mad)
        else:
            # Positive change (e.g. double-bounce or roughness increase)
            threshold_db = median_val + (k * normal_mad)

        return float(threshold_db)

    # Strategy 3: Otsu
    elif isinstance(config, OtsuThresholdConfig):
        p_min, p_max = config.clip_percentiles
        v_min, v_max = float(np.percentile(valid_sample, p_min)), float(np.percentile(valid_sample, p_max))

        if v_min >= v_max:
            raise ProcessingError(f"Percentile clipping collapsed: p_min={v_min:.3f}, p_max={v_max:.3f}")

        clipped = np.clip(valid_sample, v_min, v_max)
        hist, bin_edges = np.histogram(clipped, bins=config.num_histogram_bins, range=(v_min, v_max))
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

        total_pixels = float(clipped.size)
        prob = hist / total_pixels

        # Otsu's inter-class variance maximization
        cum_prob = np.cumsum(prob)
        cum_mean = np.cumsum(prob * bin_centers)
        global_mean = cum_mean[-1]

        best_variance = -1.0
        best_threshold = float(bin_centers[len(bin_centers) // 2])

        # Avoid boundary division by zero
        for i in range(1, len(bin_centers) - 1):
            w0 = cum_prob[i]
            w1 = 1.0 - w0
            if w0 <= 1e-10 or w1 <= 1e-10:
                continue

            u0 = cum_mean[i] / w0
            u1 = (global_mean - cum_mean[i]) / w1
            between_variance = w0 * w1 * ((u0 - u1) ** 2)

            if between_variance > best_variance:
                best_variance = between_variance
                best_threshold = float(bin_centers[i])

        return best_threshold

    else:
        raise ProcessingError(f"Unsupported threshold configuration: {type(config).__name__}")


def generate_change_mask(
    diff_db: np.ndarray,
    threshold_db: float,
    min_mapping_unit_pixels: int = 10,
    phenomenon: PhenomenonType = PhenomenonType.FLOOD,
    nodata_mask: np.ndarray | None = None,
    pixel_area_km2: float | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Generates binary change mask with morphological cluster sieving.

    Args:
        diff_db: 2D difference array in dB.
        threshold_db: Scalar change threshold in dB.
        min_mapping_unit_pixels: Minimum contiguous cluster size in pixels.
        phenomenon: PhenomenonType determining threshold direction.
        nodata_mask: Optional boolean array marking nodata.
        pixel_area_km2: Optional area per pixel in km2 for area computation.

    Returns:
        (sieved_mask, summary_dict)
    """
    if not isinstance(diff_db, np.ndarray) or diff_db.ndim != 2:
        raise ProcessingError("diff_db must be a 2D numpy ndarray")
    if not math.isfinite(threshold_db):
        raise ProcessingError(f"threshold_db must be finite float, got {threshold_db}")
    if min_mapping_unit_pixels < 1:
        raise ProcessingError(f"min_mapping_unit_pixels must be >= 1, got {min_mapping_unit_pixels}")

    # 1. Raw candidate detection
    if threshold_db < 0.0 or phenomenon in (PhenomenonType.FLOOD, PhenomenonType.CLEARING):
        cand_mask = (diff_db <= threshold_db) & np.isfinite(diff_db)
    else:
        cand_mask = (diff_db >= threshold_db) & np.isfinite(diff_db)

    if nodata_mask is not None:
        cand_mask[nodata_mask] = False

    raw_count = int(np.sum(cand_mask))

    # 2. Morphological cluster sieving (8-connectivity)
    structure_8conn = np.ones((3, 3), dtype=int)
    labeled_arr, num_features = ndimage.label(cand_mask, structure=structure_8conn)

    sieved_mask = np.zeros_like(cand_mask, dtype=bool)
    surviving_clusters = 0

    if num_features > 0:
        counts = np.bincount(labeled_arr.ravel())
        # Index 0 is background
        valid_labels = np.where(counts >= min_mapping_unit_pixels)[0]
        valid_labels = valid_labels[valid_labels > 0]

        if valid_labels.size > 0:
            sieved_mask = np.isin(labeled_arr, valid_labels)
            surviving_clusters = int(valid_labels.size)

    sieved_count = int(np.sum(sieved_mask))
    sieving_filtered_count = raw_count - sieved_count

    summary: dict[str, Any] = {
        "threshold_db": float(threshold_db),
        "raw_candidate_pixels": raw_count,
        "sieved_change_pixels": sieved_count,
        "filtered_noise_pixels": sieving_filtered_count,
        "surviving_cluster_count": surviving_clusters,
        "min_mapping_unit_pixels": min_mapping_unit_pixels,
    }

    if pixel_area_km2 is not None and pixel_area_km2 > 0.0:
        summary["sieved_change_area_km2"] = float(sieved_count * pixel_area_km2)
        summary["raw_candidate_area_km2"] = float(raw_count * pixel_area_km2)

    return sieved_mask, summary
