"""
BHnMISnTRA: Member 1 Data & Scientific Intelligence Orchestrator.
End-to-End Scientific Pipeline & Evidence Ledger Generator.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import numpy as np

from .beat_test.tracker import BeatTestSummary, track_change_regions
from .config import InvestigationConfig
from .constants import PRD_CONSTANTS
from .enums import AngleComparisonOutcome, EvidenceStatus, ExpectedBehavior, PhenomenonType
from .exceptions import (
    DuplicateProductIdError,
    GeometryMismatchError,
    InsufficientAcquisitionsError,
    ProcessingError,
    RasterAlignmentError,
)
from .policies import (
    classify_final_evidence,
    evaluate_confounders_for_evidence_label,
    evaluate_incidence_angle_pair,
)
from .processing.alignment import AlignmentMetadata, validate_raster_alignment
from .processing.calibration import calibrate_sar_array
from .processing.log_ratio import (
    compute_log_ratio,
    compute_threshold,
    create_spatial_tuning_mask,
    generate_change_mask,
)
from .processing.speckle import apply_speckle_filter


@dataclass(frozen=True)
class PipelineExecutionResult:
    """Complete scientific outcome, intermediate artifacts, and Evidence Ledger."""
    evidence_status: EvidenceStatus
    classification_reasons: tuple[str, ...]
    beat_test_summary: BeatTestSummary
    baseline_change_stats: dict[str, Any]
    calibration_provenance: dict[str, Any]
    spatial_alignment_verified: bool
    evidence_ledger: dict[str, Any]
    sieved_change_mask: np.ndarray
    diff_raster_db: np.ndarray
    data_authenticity_tier: str


def run_scientific_pipeline(
    config: InvestigationConfig,
    raster_data: Mapping[str, tuple[np.ndarray, AlignmentMetadata]],
    data_authenticity_tier: str = "TIER 3 - SYNTHETIC FIXTURE (NOT REAL SATELLITE DATA)",
) -> PipelineExecutionResult:
    """
    Executes Member 1's end-to-end scientific processing pipeline:
      1. Sequence & Metadata Validation
      2. Geometry & Incidence-Angle Verification
      3. Raster Alignment & Co-Registration Verification
      4. Radiometric Calibration to dB (with double-calibration protection)
      5. Speckle Filtering in Linear Power (logarithmic bias prevention)
      6. Log-Ratio Difference Calculation (Comparison vs Reference)
      7. Spatial Tuning vs Evaluation Split Separation
      8. Change Threshold Computation
      9. Morphological Sieving by MMU
      10. Multi-Temporal Beat Test Tracking across >= 3 subsequent acquisitions
      11. Confounder Assessment
      12. Final Three-State Evidence Classification
      13. Inspectable Evidence Ledger Construction

    Args:
        config: Validated InvestigationConfig instance.
        raster_data: Dictionary mapping product_id -> (2D numpy array, AlignmentMetadata).
        data_authenticity_tier: Explicit provenance badge (TIER 1 - REAL, TIER 2 - PREPARED, TIER 3 - SYNTHETIC).

    Returns:
        PipelineExecutionResult containing final status, rasters, statistics, and audit ledger.
    """
    ref_acq = config.reference_acquisition
    comp_acq = config.comparison_acquisition
    sub_acqs = config.subsequent_acquisitions
    all_acqs = [ref_acq, comp_acq] + list(sub_acqs)
    params = config.parameters

    phenom = PhenomenonType(config.phenomenon_type)
    exp_behav = ExpectedBehavior(config.expected_behavior)

    # 1. Product ID Duplicate and Sequence Size Check
    all_product_ids = [acq.product_id for acq in all_acqs]
    if len(all_product_ids) != len(set(all_product_ids)):
        raise DuplicateProductIdError(f"Duplicate product IDs detected in investigation: {all_product_ids}")

    if len(sub_acqs) < PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED:
        raise InsufficientAcquisitionsError(
            f"Investigation requires >= {PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED} subsequent acquisitions, "
            f"got {len(sub_acqs)}"
        )

    # 2. Geometry Compatibility & Incidence Angle Verification
    has_geometry_uncertainty = False
    ref_sensor = ref_acq.sensor

    # Verify all non-reference acquisitions against reference geometry
    for idx, cand in enumerate([comp_acq] + list(sub_acqs), start=1):
        outcome, angle_reasons, angle_geom_unc = evaluate_incidence_angle_pair(
            ref_angle_meta=ref_sensor.incidence_angle,
            sub_angle_meta=cand.sensor.incidence_angle,
            subsequent_acquisition_id=cand.product_id,
            max_divergence_deg=params.max_incidence_angle_divergence_deg,
            policy=params.unavailable_incidence_angle_policy,
        )
        if angle_geom_unc:
            has_geometry_uncertainty = True

    # 3. Raster Presence & Spatial Alignment Verification
    for pid in all_product_ids:
        if pid not in raster_data:
            raise ProcessingError(f"Missing raster data for product ID '{pid}'")

    alignments = [raster_data[pid][1] for pid in all_product_ids]
    validate_raster_alignment(alignments)
    alignment_verified = True

    # 4. Calibration to dB
    calibrated_rasters_db: dict[str, np.ndarray] = {}
    calibration_records: dict[str, Any] = {}

    for acq in all_acqs:
        raw_arr = raster_data[acq.product_id][0]
        cal_db, prov = calibrate_sar_array(raw_arr, acq.calibration)
        calibrated_rasters_db[acq.product_id] = cal_db
        calibration_records[acq.product_id] = prov

    # 5. Speckle Filtering in Linear Space
    filtered_rasters_db: dict[str, np.ndarray] = {}

    for pid, c_db in calibrated_rasters_db.items():
        filt_db = apply_speckle_filter(
            arr=c_db,
            filter_name=params.speckle_filter_name,
            window_size=params.speckle_window_size,
            is_db=True,
            equivalent_looks=4.0,
        )
        filtered_rasters_db[pid] = filt_db

    ref_db = filtered_rasters_db[ref_acq.product_id]
    comp_db = filtered_rasters_db[comp_acq.product_id]

    # 6. Log-Ratio Difference Calculation (Comparison Event vs Reference Baseline)
    diff_db = compute_log_ratio(comp_db, ref_db)

    # 7. Spatial Tuning vs Evaluation Split Separation
    t_mask, e_mask = create_spatial_tuning_mask(
        shape=diff_db.shape,
        split_ratio=params.spatial_tuning_split_ratio,
        axis=1,
    )

    # 8. Change Threshold Computation
    threshold_db = compute_threshold(
        diff_db=diff_db,
        config=params.threshold_strategy,
        tuning_mask=t_mask,
        phenomenon=phenom,
    )

    # Pixel Area from resolution (m^2 -> km^2)
    res_m = alignments[0].resolution_meters
    pixel_area_km2 = (res_m[0] * res_m[1]) / 1e6

    # 9. Morphological Sieving by MMU
    sieved_mask, change_summary = generate_change_mask(
        diff_db=diff_db,
        threshold_db=threshold_db,
        min_mapping_unit_pixels=params.min_mapping_unit_pixels,
        phenomenon=phenom,
        pixel_area_km2=pixel_area_km2,
    )

    # 10. Multi-Temporal Beat Test Tracking across Subsequent Sequence
    subsequent_rasters_seq = [filtered_rasters_db[s.product_id] for s in sub_acqs]
    beat_summary = track_change_regions(
        baseline_change_mask=sieved_mask,
        reference_raster_db=ref_db,
        subsequent_rasters_db=subsequent_rasters_seq,
        threshold_db=threshold_db,
        pixel_area_km2=pixel_area_km2,
        phenomenon=phenom,
        expected_behavior=exp_behav,
        receding_tolerance_ratio=params.flood_growth_tolerance,
        min_region_pixels=params.min_mapping_unit_pixels,
    )

    # 11. Confounder Assessment & Scientific Uncertainty
    confounders = config.confounders
    confounder_status, confounder_reasons = evaluate_confounders_for_evidence_label(
        confounders=confounders,
        beat_test_matches=beat_summary.overall_beat_test_passed,
        has_geometry_uncertainty=has_geometry_uncertainty,
    )

    # 12. Final Three-State Evidence Classification
    final_status, classification_reasons = classify_final_evidence(
        valid_subsequent_observations_count=len(sub_acqs),
        beat_test_matches=beat_summary.overall_beat_test_passed,
        has_geometry_uncertainty=has_geometry_uncertainty,
        confounders=confounders,
    )

    # 13. Construct Complete PRD Evidence Ledger
    evidence_ledger: dict[str, Any] = {
        "platform": "BHnMISnTRA - Radar Evidence & Surface Change Intelligence",
        "scientific_module": "Member 1 - Data & Scientific Intelligence",
        "data_authenticity_tier": data_authenticity_tier,
        "investigation_id": config.investigation_id,
        "study_area_id": config.study_area_id,
        "phenomenon": phenom.value,
        "expected_behavior": exp_behav.value,
        "evidence_label": final_status.value,
        "classification_reasons": classification_reasons,
        "audit_checks": {
            "spatial_alignment_verified": alignment_verified,
            "beat_test_passed": beat_summary.overall_beat_test_passed,
            "has_geometry_uncertainty": has_geometry_uncertainty,
            "subsequent_observations_count": len(sub_acqs),
            "minimum_required_subsequent": PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED,
        },
        "change_detection_metrics": {
            "threshold_db": threshold_db,
            "strategy": params.threshold_strategy.strategy_name,
            "raw_candidate_pixels": change_summary["raw_candidate_pixels"],
            "sieved_change_pixels": change_summary["sieved_change_pixels"],
            "sieved_change_area_km2": change_summary.get("sieved_change_area_km2", 0.0),
            "surviving_cluster_count": change_summary["surviving_cluster_count"],
        },
        "beat_test_metrics": {
            "total_regions_tracked": beat_summary.total_regions_tracked,
            "compliant_regions": beat_summary.compliant_regions,
            "failed_regions": beat_summary.failed_regions,
            "aggregate_timeline_km2": beat_summary.aggregate_timeline_km2,
            "diagnostic_summary": beat_summary.diagnostic_summary,
        },
        "calibration_provenance": calibration_records,
    }

    return PipelineExecutionResult(
        evidence_status=final_status,
        classification_reasons=tuple(classification_reasons),
        beat_test_summary=beat_summary,
        baseline_change_stats=change_summary,
        calibration_provenance=calibration_records,
        spatial_alignment_verified=alignment_verified,
        evidence_ledger=evidence_ledger,
        sieved_change_mask=sieved_mask,
        diff_raster_db=diff_db,
        data_authenticity_tier=data_authenticity_tier,
    )
