"""
BHnMISnTRA: Beat Test Multi-Temporal Tracking & Spatial Region Evaluator.
"""

from dataclasses import dataclass
import math
from typing import Any, Sequence
import numpy as np
from scipy import ndimage

from ..enums import ExpectedBehavior, PhenomenonType
from ..exceptions import ProcessingError
from ..policies import (
    check_receding_step,
    evaluate_flood_receding_sequence,
    evaluate_sustained_ratio_exact,
)


@dataclass(frozen=True)
class RegionTrackingResult:
    """Tracking result for a single contiguous spatial change cluster."""
    region_id: int
    centroid_pixel: tuple[float, float]
    bbox_pixel: tuple[int, int, int, int]  # (min_row, min_col, max_row, max_col)
    initial_area_km2: float
    initial_pixel_count: int
    area_timeline_km2: tuple[float, ...]
    pixel_timeline: tuple[int, ...]
    phenomenon: PhenomenonType
    expected_behavior: ExpectedBehavior
    is_compliant: bool
    diagnostic_details: str


@dataclass(frozen=True)
class BeatTestSummary:
    """Aggregate multi-temporal Beat Test evaluation across all detected change regions."""
    total_regions_tracked: int
    compliant_regions: int
    failed_regions: int
    aggregate_initial_area_km2: float
    aggregate_timeline_km2: tuple[float, ...]
    overall_beat_test_passed: bool
    region_results: tuple[RegionTrackingResult, ...]
    diagnostic_summary: str


def track_change_regions(
    baseline_change_mask: np.ndarray,
    reference_raster_db: np.ndarray,
    subsequent_rasters_db: Sequence[np.ndarray],
    threshold_db: float,
    pixel_area_km2: float,
    phenomenon: PhenomenonType = PhenomenonType.FLOOD,
    expected_behavior: ExpectedBehavior = ExpectedBehavior.RECEDING,
    receding_tolerance_ratio: float = 0.05,
    min_region_pixels: int = 10,
    nodata_mask: np.ndarray | None = None,
) -> BeatTestSummary:
    """
    Executes pre-registered Beat Test multi-temporal tracking across all
    detected candidate change regions.

    Args:
        baseline_change_mask: 2D boolean array of sieved baseline detections.
        reference_raster_db: 2D float array of reference baseline in dB.
        subsequent_rasters_db: Sequence of >= 3 2D float arrays for subsequent acquisitions in dB.
        threshold_db: Change threshold in dB.
        pixel_area_km2: Area of one pixel in square kilometers.
        phenomenon: PhenomenonType.
        expected_behavior: Expected temporal trajectory (EXPECTED_RECEDING or EXPECTED_SUSTAINED).
        receding_tolerance_ratio: Measurement noise cushion for recession steps (default 0.05).
        min_region_pixels: Minimum pixel size for an initial region to be tracked.
        nodata_mask: Optional nodata mask.

    Returns:
        BeatTestSummary containing region-by-region and aggregate verification.
    """
    if not isinstance(baseline_change_mask, np.ndarray) or baseline_change_mask.ndim != 2:
        raise ProcessingError("baseline_change_mask must be a 2D numpy boolean array")
    if len(subsequent_rasters_db) < 3:
        raise ProcessingError(f"Beat Test strictly requires >= 3 subsequent acquisitions, got {len(subsequent_rasters_db)}")
    if pixel_area_km2 <= 0.0 or not math.isfinite(pixel_area_km2):
        raise ProcessingError(f"pixel_area_km2 must be finite and positive, got {pixel_area_km2}")

    # Connected component labeling of baseline detection (8-connectivity)
    structure_8conn = np.ones((3, 3), dtype=int)
    labeled_baseline, num_features = ndimage.label(baseline_change_mask, structure=structure_8conn)

    if num_features == 0:
        return BeatTestSummary(
            total_regions_tracked=0,
            compliant_regions=0,
            failed_regions=0,
            aggregate_initial_area_km2=0.0,
            aggregate_timeline_km2=tuple(0.0 for _ in range(len(subsequent_rasters_db) + 1)),
            overall_beat_test_passed=True,
            region_results=(),
            diagnostic_summary="Zero candidate change regions detected in baseline mask. Beat test trivially clear.",
        )

    # Pre-calculate difference masks for all subsequent acquisitions
    subsequent_masks: list[np.ndarray] = []
    for idx, sub_arr in enumerate(subsequent_rasters_db):
        if sub_arr.shape != baseline_change_mask.shape:
            raise ProcessingError(
                f"Subsequent raster {idx} shape {sub_arr.shape} does not match baseline {baseline_change_mask.shape}"
            )
        diff_k = sub_arr.astype(np.float32) - reference_raster_db.astype(np.float32)
        if threshold_db < 0.0 or phenomenon in (PhenomenonType.FLOOD, PhenomenonType.CLEARING):
            mask_k = (diff_k <= threshold_db) & np.isfinite(diff_k)
        else:
            mask_k = (diff_k >= threshold_db) & np.isfinite(diff_k)
        if nodata_mask is not None:
            mask_k[nodata_mask] = False
        subsequent_masks.append(mask_k)

    region_results: list[RegionTrackingResult] = []
    agg_timeline = [0.0] * (len(subsequent_rasters_db) + 1)
    agg_initial_area = 0.0

    # Evaluate each region
    for feat_id in range(1, num_features + 1):
        region_pixels = (labeled_baseline == feat_id)
        pixel_count = int(np.sum(region_pixels))
        if pixel_count < min_region_pixels:
            continue

        init_area = pixel_count * pixel_area_km2
        agg_initial_area += init_area
        agg_timeline[0] += init_area

        # Centroid & BBox
        rows, cols = np.where(region_pixels)
        min_r, max_r = int(np.min(rows)), int(np.max(rows))
        min_c, max_c = int(np.min(cols)), int(np.max(cols))
        centroid = (float(np.mean(rows)), float(np.mean(cols)))

        # Track area over time
        area_timeline = [init_area]
        pixel_timeline = [pixel_count]

        for step_idx, s_mask in enumerate(subsequent_masks):
            overlap_pixels = int(np.sum(s_mask & region_pixels))
            overlap_area = float(overlap_pixels * pixel_area_km2)
            area_timeline.append(overlap_area)
            pixel_timeline.append(overlap_pixels)
            agg_timeline[step_idx + 1] += overlap_area

        # Evaluate compliance according to expected behavior
        if expected_behavior == ExpectedBehavior.RECEDING:
            is_compliant, reasons = evaluate_flood_receding_sequence(
                area_sequence=tuple(area_timeline),
                tolerance=receding_tolerance_ratio,
            )
            diag = "; ".join(reasons)
        elif expected_behavior == ExpectedBehavior.SUSTAINED:
            # Sustained change: check how many subsequent timepoints still detect change
            # (threshold: at least 50% of initial area retained)
            re_detections = sum(1 for a in area_timeline[1:] if a >= 0.5 * init_area)
            is_compliant = evaluate_sustained_ratio_exact(
                re_detections=re_detections,
                valid_observations=len(subsequent_rasters_db),
            )
            diag = (
                f"Sustained re-detections: {re_detections}/{len(subsequent_rasters_db)} "
                f"({'COMPLIANT' if is_compliant else 'NON-COMPLIANT'})"
            )
        else:
            raise ProcessingError(f"Unsupported expected_behavior: {expected_behavior}")

        res = RegionTrackingResult(
            region_id=feat_id,
            centroid_pixel=centroid,
            bbox_pixel=(min_r, min_c, max_r, max_c),
            initial_area_km2=round(init_area, 6),
            initial_pixel_count=pixel_count,
            area_timeline_km2=tuple(round(a, 6) for a in area_timeline),
            pixel_timeline=tuple(pixel_timeline),
            phenomenon=phenomenon,
            expected_behavior=expected_behavior,
            is_compliant=is_compliant,
            diagnostic_details=diag,
        )
        region_results.append(res)

    total_tracked = len(region_results)
    compliant_count = sum(1 for r in region_results if r.is_compliant)
    failed_count = total_tracked - compliant_count

    # Beat test passes overall if all tracked regions comply
    overall_passed = (failed_count == 0) and (total_tracked > 0)
    summary_msg = (
        f"Tracked {total_tracked} regions: {compliant_count} compliant, {failed_count} failed. "
        f"Overall Beat Test: {'PASSED' if overall_passed else 'FAILED'}."
    )

    return BeatTestSummary(
        total_regions_tracked=total_tracked,
        compliant_regions=compliant_count,
        failed_regions=failed_count,
        aggregate_initial_area_km2=round(agg_initial_area, 6),
        aggregate_timeline_km2=tuple(round(a, 6) for a in agg_timeline),
        overall_beat_test_passed=overall_passed,
        region_results=tuple(region_results),
        diagnostic_summary=summary_msg,
    )
