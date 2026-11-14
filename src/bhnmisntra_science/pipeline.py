"""
BHnMISnTRA: Member 1 Data & Scientific Intelligence Orchestrator.
End-to-End Scientific Pipeline & Evidence Ledger Generator.
Phase 2.3 Integrated Architecture: Direct Abutting Slice Assembly + Four-State Temporal Model.
"""

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence
import numpy as np

from .beat_test.tracker import (
    BeatTestSummary,
    RegionTrackingResult,
    TrajectoryEvaluationResult,
    evaluate_four_state_trajectory,
    track_change_regions,
)
from .config import InvestigationConfig
from .constants import PRD_CONSTANTS
from .enums import (
    AngleComparisonOutcome,
    EvidenceStatus,
    ExpectedBehavior,
    PhenomenonType,
    TemporalState,
)
from .exceptions import (
    DuplicateProductIdError,
    GeometryMismatchError,
    InsufficientAcquisitionsError,
    MissingSliceError,
    ProcessingError,
    RasterAlignmentError,
    SliceAssemblyError,
    SliceBoundaryGapError,
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
from .processing.mosaicking import (
    AssembledRaster,
    SliceInput,
    SlicePair,
    assemble_abutting_slices,
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
    acquisition_dates: tuple[str, ...] = ()
    temporal_states: tuple[str, ...] = ()
    coverage_metrics: dict[str, Any] = field(default_factory=dict)
    slice_assembly_provenance: dict[str, Any] = field(default_factory=dict)
    scientific_limitations: tuple[str, ...] = ()
    structured_summary: dict[str, Any] = field(default_factory=dict)


def _resolve_acquisition_raster(
    pid: str,
    is_subsequent: bool,
    raster_data: Mapping[str, Any] | None,
    slice_data: Mapping[str, Any] | None,
    master_grid: AlignmentMetadata | None,
    allow_missing_subsequent: bool,
    allow_partial_slices: bool,
) -> tuple[np.ndarray | None, AlignmentMetadata | None, dict[str, Any] | None]:
    """
    Resolves an acquisition input from either slice_data or raster_data.
    Supports single pre-assembled rasters, SlicePair, dicts, or slice tuples.
    Returns: (raw_array, alignment_metadata, slice_assembly_provenance).
    """
    # 1. Check slice_data first
    if slice_data is not None and pid in slice_data:
        s_entry = slice_data[pid]
        if s_entry is None:
            if is_subsequent and allow_missing_subsequent:
                return None, None, None
            raise ProcessingError(f"Slice data for product ID '{pid}' is None.")

        if isinstance(s_entry, AssembledRaster):
            return s_entry.data, s_entry.metadata, s_entry.provenance

        if isinstance(s_entry, SlicePair):
            assembled = assemble_abutting_slices(
                slice_north=s_entry.slice_north,
                slice_south=s_entry.slice_south,
                master_grid=master_grid,
                allow_partial=s_entry.allow_partial or allow_partial_slices,
                raise_on_gap=s_entry.raise_on_gap,
            )
            return assembled.data, assembled.metadata, assembled.provenance

        if isinstance(s_entry, dict):
            n_sl = s_entry.get("north") or s_entry.get("slice_north")
            s_sl = s_entry.get("south") or s_entry.get("slice_south")
            p_allow = s_entry.get("allow_partial", allow_partial_slices)
            gap_raise = s_entry.get("raise_on_gap", True)
            assembled = assemble_abutting_slices(
                slice_north=n_sl,
                slice_south=s_sl,
                master_grid=master_grid,
                allow_partial=p_allow,
                raise_on_gap=gap_raise,
            )
            return assembled.data, assembled.metadata, assembled.provenance

        if isinstance(s_entry, (tuple, list)):
            if len(s_entry) != 2:
                raise ProcessingError(f"Slice entry tuple for '{pid}' must have length 2, got {len(s_entry)}")
            assembled = assemble_abutting_slices(
                slice_north=s_entry[0],
                slice_south=s_entry[1],
                master_grid=master_grid,
                allow_partial=allow_partial_slices,
                raise_on_gap=True,
            )
            return assembled.data, assembled.metadata, assembled.provenance

        raise ProcessingError(f"Unsupported slice_data type for product ID '{pid}': {type(s_entry).__name__}")

    # 2. Check raster_data
    if raster_data is not None and pid in raster_data:
        r_entry = raster_data[pid]
        if r_entry is None:
            if is_subsequent and allow_missing_subsequent:
                return None, None, None
            raise ProcessingError(f"Raster data for product ID '{pid}' is None.")

        if isinstance(r_entry, AssembledRaster):
            return r_entry.data, r_entry.metadata, r_entry.provenance

        if isinstance(r_entry, SlicePair):
            assembled = assemble_abutting_slices(
                slice_north=r_entry.slice_north,
                slice_south=r_entry.slice_south,
                master_grid=master_grid,
                allow_partial=r_entry.allow_partial or allow_partial_slices,
                raise_on_gap=r_entry.raise_on_gap,
            )
            return assembled.data, assembled.metadata, assembled.provenance

        if isinstance(r_entry, dict) and ("north" in r_entry or "south" in r_entry or "slice_north" in r_entry):
            n_sl = r_entry.get("north") or r_entry.get("slice_north")
            s_sl = r_entry.get("south") or r_entry.get("slice_south")
            p_allow = r_entry.get("allow_partial", allow_partial_slices)
            gap_raise = r_entry.get("raise_on_gap", True)
            assembled = assemble_abutting_slices(
                slice_north=n_sl,
                slice_south=s_sl,
                master_grid=master_grid,
                allow_partial=p_allow,
                raise_on_gap=gap_raise,
            )
            return assembled.data, assembled.metadata, assembled.provenance

        if isinstance(r_entry, tuple):
            # Check if it is a pre-assembled (np.ndarray, AlignmentMetadata)
            if len(r_entry) == 2 and isinstance(r_entry[0], np.ndarray) and isinstance(r_entry[1], AlignmentMetadata):
                return r_entry[0], r_entry[1], None

            # Otherwise it represents a slice pair: (slice_north, slice_south)
            if len(r_entry) == 2:
                assembled = assemble_abutting_slices(
                    slice_north=r_entry[0],
                    slice_south=r_entry[1],
                    master_grid=master_grid,
                    allow_partial=allow_partial_slices,
                    raise_on_gap=True,
                )
                return assembled.data, assembled.metadata, assembled.provenance

            raise ProcessingError(f"Invalid tuple structure for product ID '{pid}': length {len(r_entry)}")

        raise ProcessingError(f"Unsupported raster_data format for product ID '{pid}': {type(r_entry).__name__}")

    # 3. Neither source provides this acquisition
    if is_subsequent and allow_missing_subsequent:
        return None, None, None

    raise ProcessingError(f"Missing raster data for product ID '{pid}'")


def run_scientific_pipeline(
    config: InvestigationConfig,
    raster_data: Mapping[str, Any] | None = None,
    slice_data: Mapping[str, Any] | None = None,
    environmental_context: Sequence[dict[str, Any] | None] | None = None,
    master_grid: AlignmentMetadata | None = None,
    data_authenticity_tier: str = "TIER 3 - SYNTHETIC FIXTURE (NOT REAL SATELLITE DATA)",
    allow_missing_subsequent: bool = False,
    allow_partial_slices: bool = False,
    reference_evidence: dict[str, Any] | None = None,
) -> PipelineExecutionResult:
    """
    Executes Member 1's end-to-end scientific processing pipeline:
      1. Sequence & Metadata Validation
      2. Geometry & Incidence-Angle Verification
      3. Compatible Slice Assembly (Direct Abutting spatial concatenation)
      4. Raster Alignment & Co-Registration Verification
      5. Radiometric Calibration to dB (with double-calibration protection)
      6. Speckle Filtering in Linear Power (logarithmic bias prevention)
      7. Log-Ratio Difference Calculation (Comparison Event vs Reference Baseline)
      8. Spatial Tuning vs Evaluation Split Separation
      9. Change Threshold Computation
      10. Morphological Sieving by MMU
      11. Multi-Temporal Beat Test Tracking (Four-State Model with Three-Tier Corroboration)
      12. Confounder Assessment & Scientific Uncertainty
      13. Final Three-State Evidence Classification
      14. Structured Results & Inspectable Evidence Ledger Construction

    Args:
        config: Validated InvestigationConfig instance.
        raster_data: Dictionary mapping product_id -> (2D numpy array, AlignmentMetadata) OR SlicePair.
        slice_data: Optional mapping of product_id -> SlicePair or (slice_north, slice_south).
        environmental_context: Optional sequence of environmental parameters per subsequent step.
        master_grid: Optional explicit AlignmentMetadata for target UTM Zone 43N grid.
        data_authenticity_tier: Explicit provenance badge (TIER 1 - REAL, TIER 2 - PREPARED, TIER 3 - SYNTHETIC).
        allow_missing_subsequent: If True, permits subsequent acquisitions to be None/missing.
        allow_partial_slices: If True, permits single-slice observation per pass.
        reference_evidence: Optional independent optical reference evidence block.

    Returns:
        PipelineExecutionResult containing final status, rasters, statistics, structured results, and ledger.
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

    # 3. Compatible Slice Assembly and Ingestion
    raw_rasters: dict[str, np.ndarray | None] = {}
    alignments: dict[str, AlignmentMetadata | None] = {}
    slice_assembly_records: dict[str, Any] = {}

    for acq in all_acqs:
        pid = acq.product_id
        is_sub = acq in sub_acqs
        arr, meta, asm_prov = _resolve_acquisition_raster(
            pid=pid,
            is_subsequent=is_sub,
            raster_data=raster_data,
            slice_data=slice_data,
            master_grid=master_grid,
            allow_missing_subsequent=allow_missing_subsequent,
            allow_partial_slices=allow_partial_slices,
        )
        raw_rasters[pid] = arr
        alignments[pid] = meta
        if asm_prov is not None:
            slice_assembly_records[pid] = asm_prov

    # Reference and comparison baselines must be present and valid
    if raw_rasters[ref_acq.product_id] is None or raw_rasters[comp_acq.product_id] is None:
        raise ProcessingError("Reference and comparison baseline acquisitions are strictly required to establish flood change mask.")

    # 4. Raster Alignment Verification across all present rasters
    present_alignments = [alignments[pid] for pid in all_product_ids if alignments.get(pid) is not None]
    validate_raster_alignment(present_alignments)
    alignment_verified = True

    # 5. Radiometric Calibration to dB
    calibrated_rasters_db: dict[str, np.ndarray | None] = {}
    calibration_records: dict[str, Any] = {}

    for acq in all_acqs:
        pid = acq.product_id
        raw_arr = raw_rasters[pid]
        if raw_arr is not None:
            cal_db, prov = calibrate_sar_array(raw_arr, acq.calibration)
            calibrated_rasters_db[pid] = cal_db
            calibration_records[pid] = prov
        else:
            calibrated_rasters_db[pid] = None
            calibration_records[pid] = {"status": "MISSING", "calibrated": False}

    # 6. Speckle Filtering in Linear Space
    filtered_rasters_db: dict[str, np.ndarray | None] = {}

    for pid, c_db in calibrated_rasters_db.items():
        if c_db is not None:
            filt_db = apply_speckle_filter(
                arr=c_db,
                filter_name=params.speckle_filter_name,
                window_size=params.speckle_window_size,
                is_db=True,
                equivalent_looks=4.0,
            )
            filtered_rasters_db[pid] = filt_db
        else:
            filtered_rasters_db[pid] = None

    ref_db = filtered_rasters_db[ref_acq.product_id]
    comp_db = filtered_rasters_db[comp_acq.product_id]
    assert ref_db is not None and comp_db is not None

    # 7. Log-Ratio Difference Calculation (Comparison Event vs Reference Baseline)
    diff_db = compute_log_ratio(comp_db, ref_db)

    # 8. Spatial Tuning vs Evaluation Split Separation
    t_mask, e_mask = create_spatial_tuning_mask(
        shape=diff_db.shape,
        split_ratio=params.spatial_tuning_split_ratio,
        axis=1,
    )

    # 9. Change Threshold Computation
    threshold_db = compute_threshold(
        diff_db=diff_db,
        config=params.threshold_strategy,
        tuning_mask=t_mask,
        phenomenon=phenom,
    )

    # Pixel Area from resolution (m^2 -> km^2)
    res_m = present_alignments[0].resolution_meters
    pixel_area_km2 = (res_m[0] * res_m[1]) / 1e6

    # 10. Morphological Sieving by MMU
    sieved_mask, change_summary = generate_change_mask(
        diff_db=diff_db,
        threshold_db=threshold_db,
        min_mapping_unit_pixels=params.min_mapping_unit_pixels,
        phenomenon=phenom,
        pixel_area_km2=pixel_area_km2,
    )

    # 11. Multi-Temporal Beat Test Tracking (Four-State Model)
    subsequent_rasters_seq = [filtered_rasters_db.get(s.product_id) for s in sub_acqs]
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
        environmental_context=environmental_context,
    )

    # Compute valid subsequent observations count
    if beat_summary.region_results and beat_summary.region_results[0].trajectory_result is not None:
        valid_sub_count = beat_summary.region_results[0].trajectory_result.valid_observations_count
    else:
        valid_sub_count = 0
        for idx, r in enumerate(subsequent_rasters_seq):
            if r is not None:
                is_v = True
                if environmental_context and idx < len(environmental_context) and environmental_context[idx] is not None:
                    is_v = bool(environmental_context[idx].get("is_valid", True))
                if is_v:
                    valid_sub_count += 1

    # 12. Confounder Assessment & Scientific Uncertainty
    confounders = config.confounders
    confounder_status, confounder_reasons = evaluate_confounders_for_evidence_label(
        confounders=confounders,
        beat_test_matches=beat_summary.overall_beat_test_passed,
        has_geometry_uncertainty=has_geometry_uncertainty,
    )

    # 13. Final Three-State Evidence Classification
    final_status, classification_reasons = classify_final_evidence(
        valid_subsequent_observations_count=valid_sub_count,
        beat_test_matches=beat_summary.overall_beat_test_passed,
        has_geometry_uncertainty=has_geometry_uncertainty,
        confounders=confounders,
    )

    # 14. Structured Results & Limitations Compilation
    acquisition_dates = tuple(str(acq.acquisition_utc) for acq in all_acqs)

    if beat_summary.region_results and beat_summary.region_results[0].trajectory_result is not None:
        states_seq = tuple(s.value for s in beat_summary.region_results[0].trajectory_result.state_timeline)
    else:
        st_list = ["BASELINE_REF", "PEAK_COMP"]
        for idx, r in enumerate(subsequent_rasters_seq):
            if r is None:
                st_list.append("MISSING")
            elif environmental_context and idx < len(environmental_context) and environmental_context[idx] and not environmental_context[idx].get("is_valid", True):
                st_list.append("INVALID")
            else:
                st_list.append("NO_CHANGE_OBSERVED")
        states_seq = tuple(st_list)

    missing_count = sum(1 for r in subsequent_rasters_seq if r is None)
    invalid_count = len(sub_acqs) - valid_sub_count - missing_count
    coverage_metrics: dict[str, Any] = {
        "master_crs": present_alignments[0].crs,
        "master_shape": present_alignments[0].shape,
        "resolution_meters": present_alignments[0].resolution_meters,
        "pixel_area_km2": pixel_area_km2,
        "total_acquisitions_planned": len(all_acqs),
        "subsequent_acquisitions_total": len(sub_acqs),
        "subsequent_acquisitions_valid": valid_sub_count,
        "subsequent_acquisitions_missing": missing_count,
        "subsequent_acquisitions_invalid": invalid_count,
        "minimum_required_subsequent": PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED,
        "temporal_coverage_complete": (valid_sub_count >= PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED),
        "slices_assembled_count": len(slice_assembly_records),
    }

    limitations: list[str] = []
    if valid_sub_count < PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED:
        limitations.append(
            f"PRD Hard Rule: Insufficient valid subsequent acquisitions ({valid_sub_count} < "
            f"{PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED}). Final status is strictly UNVERIFIED. We make no claim."
        )
    limitations.append(
        "Empirical thresholds (15% area change tolerance, 50mm cumulative rainfall, 4.0 m/s surface wind speed) "
        "are PROVISIONAL engineering heuristics awaiting field gauge calibration."
    )
    if has_geometry_uncertainty:
        limitations.append("Incidence angle geometry uncertainty flagged; physical geometry compatibility is not fully verified.")
    for c in confounders:
        if c.scientific_limitation:
            limitations.append(f"Confounder '{c.name}': {c.scientific_limitation}")
    if "SYNTHETIC" in data_authenticity_tier:
        limitations.append(
            "Synthetic fixture execution confirms algorithmic correctness only; empirical scientific validation requires authentic satellite observations."
        )

    structured_summary: dict[str, Any] = {
        "investigation_id": config.investigation_id,
        "study_area_id": config.study_area_id,
        "phenomenon": phenom.value,
        "expected_behavior": exp_behav.value,
        "evidence_status": final_status.value,
        "classification_reasons": list(classification_reasons),
        "acquisition_dates": list(acquisition_dates),
        "temporal_states": list(states_seq),
        "coverage": coverage_metrics,
        "beat_test_passed": beat_summary.overall_beat_test_passed,
        "slice_assembly_applied": len(slice_assembly_records) > 0,
        "limitations": list(limitations),
    }

    # 15. Construct Complete PRD Evidence Ledger
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
            "valid_subsequent_observations_count": valid_sub_count,
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
            "temporal_states_summary": beat_summary.temporal_states_summary,
        },
        "calibration_provenance": calibration_records,
        "slice_assembly_provenance": slice_assembly_records,
        "structured_results": structured_summary,
        "acquisition_dates": list(acquisition_dates),
        "temporal_states": list(states_seq),
        "coverage": coverage_metrics,
        "scientific_limitations": list(limitations),
    }

    if reference_evidence is not None:
        evidence_ledger["reference_evidence"] = reference_evidence

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
        acquisition_dates=acquisition_dates,
        temporal_states=states_seq,
        coverage_metrics=coverage_metrics,
        slice_assembly_provenance=slice_assembly_records,
        scientific_limitations=tuple(limitations),
        structured_summary=structured_summary,
    )
