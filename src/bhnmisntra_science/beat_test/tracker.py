"""
BHnMISnTRA: Beat Test Multi-Temporal Tracking & Spatial Region Evaluator.
Implementation of the Four-State Temporal Model:
  PERSISTENT_STAGNATION, RECEDING, RE_INUNDATED, DRAINED.
Compliant with Phase 1.5 Scientific Specification and Phase 1.4.1 Correction Audit.
"""

from dataclasses import dataclass
import math
from typing import Any, Sequence
import numpy as np
from scipy import ndimage

from ..constants import PRD_CONSTANTS
from ..enums import (
    EvidenceStatus,
    ExpectedBehavior,
    PhenomenonType,
    TemporalClusterState,
    TemporalState,
)
from ..exceptions import ProcessingError
from ..policies import evaluate_sustained_ratio_exact


@dataclass(frozen=True)
class TemporalStepEvaluation:
    """Evaluation of a single temporal transition between t_{k-1} and t_k."""
    step_index: int
    state: TemporalState
    area_km2: float | None
    area_change_ratio: float | None
    is_valid: bool
    is_missing: bool
    is_explained: bool
    diagnostic: str
    environmental_context: dict[str, Any]


@dataclass(frozen=True)
class TrajectoryEvaluationResult:
    """
    Complete multi-temporal trajectory evaluation for a cluster or aggregate sequence.
    Supports unpacking: is_compliant, states, reasons = eval_result.
    """
    is_compliant: bool
    state_timeline: tuple[TemporalState, ...]
    diagnostic_reasons: tuple[str, ...]
    initial_area_km2: float
    area_timeline_km2: tuple[float | None, ...]
    step_evaluations: tuple[TemporalStepEvaluation, ...]
    valid_observations_count: int
    missing_observations_count: int
    invalid_observations_count: int
    evidence_status: EvidenceStatus
    unexplained_change_detected: bool
    reference_agreement: dict[str, Any] | None
    provenance: dict[str, Any]
    diagnostic_summary: str

    def __iter__(self):
        """Supports 3-tuple unpacking: is_compliant, states, reasons = eval_res."""
        return iter((self.is_compliant, list(self.state_timeline), list(self.diagnostic_reasons)))


@dataclass(frozen=True)
class RegionTrackingResult:
    """Tracking result for a single contiguous spatial change cluster."""
    region_id: int
    centroid_pixel: tuple[float, float]
    bbox_pixel: tuple[int, int, int, int]  # (min_row, min_col, max_row, max_col)
    initial_area_km2: float
    initial_pixel_count: int
    area_timeline_km2: tuple[float | None, ...]
    pixel_timeline: tuple[int, ...]
    phenomenon: PhenomenonType
    expected_behavior: ExpectedBehavior
    is_compliant: bool
    diagnostic_details: str
    state_timeline: tuple[TemporalState, ...] = ()
    trajectory_result: TrajectoryEvaluationResult | None = None


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
    temporal_states_summary: dict[str, int] | None = None


def evaluate_four_state_trajectory(
    area_timeline: Sequence[float | None] | None = None,
    area_sequence: Sequence[float | None] | None = None,
    environmental_context: Sequence[dict[str, Any] | None] | None = None,
    rainfall_timeline: Sequence[float | None] | None = None,
    wind_timeline: Sequence[float | None] | None = None,
    river_stage_timeline: Sequence[float | None] | None = None,
    hydraulic_plausibility_timeline: Sequence[bool | None] | None = None,
    stagnation_tolerance: float = 0.15,
    recession_tolerance: float = 0.15,
    surge_threshold: float = 0.15,
    mmu_km2: float = 0.001,
    rainfall_threshold_mm: float = 50.0,
    wind_threshold_ms: float = 4.0,
    river_stage_threshold_m: float = 1.0,
    is_synthetic: bool = False,
    reference_evidence: dict[str, Any] | None = None,
) -> TrajectoryEvaluationResult:
    """
    Evaluates step-by-step state transitions and overall multi-temporal trajectory
    under the Four-State Temporal Model:
      PERSISTENT_STAGNATION, RECEDING, RE_INUNDATED, DRAINED.

    Key Invariants:
      1. Never enforces universal monotonic recession: persistent stagnation in below-sea-level
         deltaic polders is physically compliant.
      2. Never interprets missing or invalid acquisitions as drainage.
      3. Never automatically attributes causation to rainfall: re-inundation requires
         concurrence of the Three-Tier Physical Corroboration Framework (Forcing +
         Hydraulic Plausibility + Sensor Artifact Exclusion).
      4. Hard PRD Gate: Fewer than 3 valid subsequent acquisitions strictly results in UNVERIFIED.
      5. Reference agreement remains separate from SAR evidence classification.
      6. Synthetic compliance disclaimers are preserved in provenance.

    Args:
        area_timeline: Sequence of observed areas in km² (first entry is peak comparison baseline).
        area_sequence: Alias for area_timeline.
        environmental_context: Optional sequence of dicts per subsequent step specifying environmental forcing.
        rainfall_timeline: Optional sequence of cumulative 12d rainfall in mm.
        wind_timeline: Optional sequence of ERA5 10m wind speeds in m/s.
        river_stage_timeline: Optional sequence of upstream river gauge rise in meters.
        hydraulic_plausibility_timeline: Optional sequence of booleans indicating hydraulic connectivity.
        stagnation_tolerance: Relative area variation tolerance for stagnation (|ΔA| / A_prev <= 0.15).
        recession_tolerance: Threshold ratio for active recession (ΔA / A_prev < -0.15).
        surge_threshold: Growth ratio threshold for re-inundation (ΔA / A_prev > 0.15).
        mmu_km2: Minimum mapping unit area threshold for drainage (default 0.001 km² = 10 px at 10m).
        rainfall_threshold_mm: Cumulative rainfall threshold for Tier 1 forcing context (default 50.0 mm).
        wind_threshold_ms: Maximum wind speed for Tier 3 artifact check (default 4.0 m/s).
        river_stage_threshold_m: Upstream river stage surge for Tier 1 forcing context (default 1.0 m).
        is_synthetic: Flag indicating synthetic test fixture provenance.
        reference_evidence: Optional independent optical reference evidence block.

    Returns:
        TrajectoryEvaluationResult (unpacks into (is_compliant, state_timeline, diagnostic_reasons)).
    """
    raw_seq = area_timeline if area_timeline is not None else area_sequence
    if raw_seq is None:
        raise ProcessingError("Must provide area_timeline or area_sequence to evaluate_four_state_trajectory.")

    if len(raw_seq) < 2:
        empty_diag = ("Timeline has fewer than 2 observations (at least 1 reference + 1 subsequent required)",)
        return TrajectoryEvaluationResult(
            is_compliant=False,
            state_timeline=(TemporalState.PEAK,),
            diagnostic_reasons=empty_diag,
            initial_area_km2=0.0,
            area_timeline_km2=tuple(raw_seq),
            step_evaluations=(),
            valid_observations_count=0,
            missing_observations_count=0,
            invalid_observations_count=0,
            evidence_status=EvidenceStatus.UNVERIFIED,
            unexplained_change_detected=False,
            reference_agreement=reference_evidence,
            provenance={"error": "insufficient_observations"},
            diagnostic_summary=empty_diag[0],
        )

    # 1. Baseline Area Validation
    a_0 = raw_seq[0]
    if a_0 is None or (isinstance(a_0, float) and math.isnan(a_0)):
        raise ProcessingError("Initial baseline area at index 0 cannot be None or NaN.")
    a_0 = float(a_0)
    if a_0 < 0.0:
        raise ProcessingError(f"Initial baseline area cannot be negative, got {a_0}")

    states: list[TemporalState] = [TemporalState.PEAK]
    reasons: list[str] = [f"Step 0: Peak flood comparison baseline (area = {a_0:.4f} km²)"]
    step_evals: list[TemporalStepEvaluation] = []

    valid_count = 0
    missing_count = 0
    invalid_count = 0
    unexplained_change = False
    is_compliant = True
    a_last_valid = a_0

    # 2. Step-by-Step Transition Evaluation
    for k in range(1, len(raw_seq)):
        # Extract environmental context for step k
        env: dict[str, Any] = {}
        if environmental_context and (k - 1) < len(environmental_context) and environmental_context[k - 1] is not None:
            env.update(environmental_context[k - 1])

        # Overlay specific timelines if provided
        if rainfall_timeline and k < len(rainfall_timeline) and rainfall_timeline[k] is not None:
            env["rainfall_12d_mm"] = float(rainfall_timeline[k])
        if wind_timeline and k < len(wind_timeline) and wind_timeline[k] is not None:
            env["wind_speed_mps"] = float(wind_timeline[k])
        if river_stage_timeline and k < len(river_stage_timeline) and river_stage_timeline[k] is not None:
            env["river_stage_rise_m"] = float(river_stage_timeline[k])
        if hydraulic_plausibility_timeline and k < len(hydraulic_plausibility_timeline) and hydraulic_plausibility_timeline[k] is not None:
            env["hydraulically_plausible"] = bool(hydraulic_plausibility_timeline[k])

        a_curr_raw = raw_seq[k]

        # Check: Missing Observation
        is_missing = (
            a_curr_raw is None
            or (isinstance(a_curr_raw, float) and math.isnan(a_curr_raw))
            or env.get("is_missing", False)
        )
        if is_missing:
            missing_count += 1
            step_state = TemporalState.MISSING
            step_diag = (
                f"Step {k}: Acquisition MISSING / unobserved. Footprint unobserved; "
                f"NOT interpreted as drainage."
            )
            states.append(step_state)
            reasons.append(step_diag)
            step_evals.append(
                TemporalStepEvaluation(
                    step_index=k,
                    state=step_state,
                    area_km2=None,
                    area_change_ratio=None,
                    is_valid=False,
                    is_missing=True,
                    is_explained=False,
                    diagnostic=step_diag,
                    environmental_context=env,
                )
            )
            continue

        # Check: Invalid Observation
        is_valid = env.get("is_valid", True)
        if not is_valid:
            invalid_count += 1
            inval_reason = env.get("invalidation_reason", "Data quality failure or geometric divergence")
            step_state = TemporalState.INVALID
            step_diag = (
                f"Step {k}: Acquisition INVALID ({inval_reason}). Observation excluded from count; "
                f"NOT interpreted as drainage."
            )
            states.append(step_state)
            reasons.append(step_diag)
            step_evals.append(
                TemporalStepEvaluation(
                    step_index=k,
                    state=step_state,
                    area_km2=float(a_curr_raw),
                    area_change_ratio=None,
                    is_valid=False,
                    is_missing=False,
                    is_explained=False,
                    diagnostic=step_diag,
                    environmental_context=env,
                )
            )
            continue

        # Valid Observation
        valid_count += 1
        a_curr = float(a_curr_raw)
        if a_curr < 0.0:
            raise ProcessingError(f"Observed area at step {k} cannot be negative, got {a_curr}")

        rel_change = (a_curr - a_last_valid) / a_last_valid if a_last_valid > 0.0 else 0.0
        rain = float(env.get("rainfall_12d_mm", 0.0))
        wind = float(env.get("wind_speed_mps", 2.0))
        stage_rise = float(env.get("river_stage_rise_m", 0.0))
        high_tide = bool(env.get("astronomical_high_tide", False))
        hyd_plausible = bool(env.get("hydraulically_plausible", True))

        if wind > wind_threshold_ms:
            reasons.append(
                f"Step {k}: Wind speed {wind:.1f} m/s > {wind_threshold_ms:.1f} m/s; "
                f"Bragg wave roughening warning."
            )

        # STATE 1: DRAINED
        if a_curr < mmu_km2:
            step_state = TemporalState.DRAINED
            step_diag = f"Step {k}: Area {a_curr:.4f} km² < MMU ({mmu_km2:.4f} km²); DRAINED."
            step_explained = True

        # STATE 2: RE-INUNDATION AFTER DRAINAGE
        elif a_last_valid < mmu_km2 and a_curr >= mmu_km2:
            # Re-emergence of water after complete drainage: enforce Three-Tier Framework
            tier1_ok = (rain >= rainfall_threshold_mm) or (stage_rise >= river_stage_threshold_m) or high_tide
            tier2_ok = hyd_plausible
            tier3_ok = (wind < wind_threshold_ms)

            if tier1_ok and tier2_ok and tier3_ok:
                step_state = TemporalState.RE_INUNDATED_EXPLAINED
                step_explained = True
                step_diag = (
                    f"Step {k}: Re-inundation to {a_curr:.4f} km² after drainage corroborated by multi-tier physical context "
                    f"(Forcing: rain={rain:.1f}mm, stage_rise={stage_rise:.2f}m; Hydraulic Plausibility: {hyd_plausible}; "
                    f"Sensor Artifact: wind={wind:.1f}m/s). Contextual environmental corroboration, not isolated causation."
                )
            else:
                step_state = TemporalState.RE_INUNDATED_UNEXPLAINED
                step_explained = False
                unexplained_change = True
                is_compliant = False
                step_diag = (
                    f"Step {k}: UNEXPLAINED_GROWTH (Re-inundation) to {a_curr:.4f} km² after drainage. Incomplete physical corroboration: "
                    f"[Tier 1 Forcing: {tier1_ok}, Tier 2 Hydraulic Plausibility: {tier2_ok}, Tier 3 Artifact Exclusion: {tier3_ok}]."
                )

        # STATE 3: RE-INUNDATION FROM ACTIVE FLOOD (Growth exceeding surge threshold)
        elif rel_change > surge_threshold:
            tier1_ok = (rain >= rainfall_threshold_mm) or (stage_rise >= river_stage_threshold_m) or high_tide
            tier2_ok = hyd_plausible
            tier3_ok = (wind < wind_threshold_ms)

            if tier1_ok and tier2_ok and tier3_ok:
                step_state = TemporalState.RE_INUNDATED_EXPLAINED
                step_explained = True
                step_diag = (
                    f"Step {k}: Area grew by {rel_change*100:+.1f}% from {a_last_valid:.4f} to {a_curr:.4f} km²; "
                    f"corroborated by physical context (rain={rain:.1f}mm, stage_rise={stage_rise:.2f}m, wind={wind:.1f}m/s). "
                    f"Corroborating environmental context only, not isolated causation."
                )
            else:
                step_state = TemporalState.RE_INUNDATED_UNEXPLAINED
                step_explained = False
                unexplained_change = True
                is_compliant = False
                step_diag = (
                    f"Step {k}: UNEXPLAINED_GROWTH. Area grew by {rel_change*100:+.1f}%, UNEXPLAINED under incomplete physical corroboration "
                    f"[Tier 1 Forcing: {tier1_ok}, Tier 2 Hydraulic Plausibility: {tier2_ok}, Tier 3 Artifact Exclusion: {tier3_ok}]."
                )

        # STATE 4: PERSISTENT STAGNATION (Area stable within stagnation cushion)
        elif abs(rel_change) <= stagnation_tolerance:
            step_state = TemporalState.PERSISTENT_STAGNATION
            step_explained = True
            step_diag = (
                f"Step {k}: Area {a_curr:.4f} km² within {stagnation_tolerance*100:.0f}% of prev ({rel_change*100:+.1f}%); "
                f"PERSISTENT_STAGNATION (Compliant for below-sea-level deltaic polders)."
            )

        # STATE 5: RECEDING
        elif rel_change < -recession_tolerance or a_curr < a_last_valid:
            step_state = TemporalState.RECEDING
            step_explained = True
            step_diag = f"Step {k}: Area receded from {a_last_valid:.4f} to {a_curr:.4f} km² ({rel_change*100:.1f}%); RECEDING."

        else:
            step_state = TemporalState.UNCERTAIN
            step_explained = True
            step_diag = f"Step {k}: Ambiguous change ({rel_change*100:+.1f}%)."

        a_last_valid = a_curr
        states.append(step_state)
        reasons.append(step_diag)
        step_evals.append(
            TemporalStepEvaluation(
                step_index=k,
                state=step_state,
                area_km2=a_curr,
                area_change_ratio=rel_change,
                is_valid=True,
                is_missing=False,
                is_explained=step_explained,
                diagnostic=step_diag,
                environmental_context=env,
            )
        )

    # 3. Authoritative Evidence Status Invariants
    # Non-negotiable PRD Gate: N_valid >= 3 required for Supported
    if valid_count < PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED:
        evidence_status = EvidenceStatus.UNVERIFIED
        summary_diag = (
            f"PRD Hard Invariant: Insufficient valid repeat acquisitions ({valid_count} < "
            f"{PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED}). Status is strictly UNVERIFIED. We make no claim."
        )
    elif unexplained_change or not is_compliant:
        evidence_status = EvidenceStatus.INCONCLUSIVE
        summary_diag = (
            f"Beat Test: Multi-temporal trajectory contains unexplained surge or non-compliant anomaly; "
            f"status is INCONCLUSIVE."
        )
    else:
        evidence_status = EvidenceStatus.SUPPORTED
        summary_diag = (
            f"Beat Test: Multi-temporal trajectory verified compliant across {valid_count} valid subsequent acquisitions; "
            f"status is SUPPORTED."
        )

    # 4. Provenance Construction
    provenance: dict[str, Any] = {
        "engine": "FOUR_STATE_TEMPORAL_MODEL",
        "initial_area_km2": a_0,
        "total_subsequent_steps": len(raw_seq) - 1,
        "valid_observations_count": valid_count,
        "missing_observations_count": missing_count,
        "invalid_observations_count": invalid_count,
        "unexplained_change_detected": unexplained_change,
        "is_compliant": is_compliant,
        "evidence_status": evidence_status.value,
        "data_authenticity_tier": "TIER 3 - SYNTHETIC FIXTURE" if is_synthetic else "TIER 1 - REAL SATELLITE OBSERVATION",
        "scientific_validation_claimed": False if is_synthetic else True,
        "states_sequence": [s.value for s in states],
    }

    if is_synthetic:
        provenance["synthetic_disclaimer"] = (
            "Synthetic test execution confirms algorithmic correctness only; "
            "empirical scientific validation strictly requires authentic satellite observations."
        )

    # Reference agreement remains completely independent of SAR evidence status
    if reference_evidence is not None:
        provenance["reference_evidence"] = reference_evidence
        provenance["reference_evidence_agreement"] = reference_evidence.get("agreed", None)
        provenance["reference_evidence_source"] = reference_evidence.get("source", "Unknown")

    return TrajectoryEvaluationResult(
        is_compliant=is_compliant,
        state_timeline=tuple(states),
        diagnostic_reasons=tuple(reasons),
        initial_area_km2=a_0,
        area_timeline_km2=tuple(raw_seq),
        step_evaluations=tuple(step_evals),
        valid_observations_count=valid_count,
        missing_observations_count=missing_count,
        invalid_observations_count=invalid_count,
        evidence_status=evidence_status,
        unexplained_change_detected=unexplained_change,
        reference_agreement=reference_evidence,
        provenance=provenance,
        diagnostic_summary=summary_diag,
    )


def evaluate_mixed_spatial_trajectories(
    cluster_timelines: Sequence[Sequence[float | None]],
    environmental_context: Sequence[dict[str, Any] | None] | None = None,
    stagnation_tolerance: float = 0.15,
    recession_tolerance: float = 0.15,
    mmu_km2: float = 0.001,
) -> tuple[dict[str, int], tuple[TrajectoryEvaluationResult, ...]]:
    """
    Evaluates mixed spatial trajectories across multiple independent spatial clusters.
    Returns aggregate state counts and individual cluster evaluations.
    """
    results: list[TrajectoryEvaluationResult] = []
    state_counts = {
        "receding": 0,
        "persistent_stagnation": 0,
        "re_inundated_explained": 0,
        "re_inundated_unexplained": 0,
        "drained": 0,
        "missing": 0,
        "invalid": 0,
        "uncertain": 0,
    }

    for timeline in cluster_timelines:
        res = evaluate_four_state_trajectory(
            area_timeline=timeline,
            environmental_context=environmental_context,
            stagnation_tolerance=stagnation_tolerance,
            recession_tolerance=recession_tolerance,
            mmu_km2=mmu_km2,
        )
        results.append(res)
        # Classify final observed state of cluster
        if len(res.state_timeline) > 1:
            final_st = res.state_timeline[-1]
            if final_st == TemporalState.RECEDING:
                state_counts["receding"] += 1
            elif final_st == TemporalState.PERSISTENT_STAGNATION:
                state_counts["persistent_stagnation"] += 1
            elif final_st == TemporalState.RE_INUNDATED_EXPLAINED:
                state_counts["re_inundated_explained"] += 1
            elif final_st == TemporalState.RE_INUNDATED_UNEXPLAINED:
                state_counts["re_inundated_unexplained"] += 1
            elif final_st == TemporalState.DRAINED:
                state_counts["drained"] += 1
            elif final_st == TemporalState.MISSING:
                state_counts["missing"] += 1
            elif final_st == TemporalState.INVALID:
                state_counts["invalid"] += 1
            else:
                state_counts["uncertain"] += 1

    return state_counts, tuple(results)


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
    environmental_context: Sequence[dict[str, Any] | None] | None = None,
) -> BeatTestSummary:
    """
    Executes pre-registered Beat Test multi-temporal tracking across all
    detected candidate change regions using the Four-State Temporal Model.

    Args:
        baseline_change_mask: 2D boolean array of sieved baseline detections.
        reference_raster_db: 2D float array of reference baseline in dB.
        subsequent_rasters_db: Sequence of >= 3 2D float arrays for subsequent acquisitions in dB.
        threshold_db: Change threshold in dB.
        pixel_area_km2: Area of one pixel in square kilometers.
        phenomenon: PhenomenonType.
        expected_behavior: Expected temporal trajectory (RECEDING or SUSTAINED).
        receding_tolerance_ratio: Measurement noise cushion for recession steps (default 0.05).
        min_region_pixels: Minimum pixel size for an initial region to be tracked.
        nodata_mask: Optional nodata mask.
        environmental_context: Optional sequence of environmental parameters per subsequent acquisition.

    Returns:
        BeatTestSummary containing region-by-region and aggregate verification.
    """
    if not isinstance(baseline_change_mask, np.ndarray) or baseline_change_mask.ndim != 2:
        raise ProcessingError("baseline_change_mask must be a 2D numpy boolean array")
    if len(subsequent_rasters_db) < PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED:
        raise ProcessingError(
            f"Beat Test strictly requires >= {PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED} subsequent acquisitions, "
            f"got {len(subsequent_rasters_db)}"
        )
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
            temporal_states_summary={},
        )

    # Pre-calculate difference masks for all subsequent acquisitions
    subsequent_masks: list[np.ndarray | None] = []
    for idx, sub_arr in enumerate(subsequent_rasters_db):
        if sub_arr is None:
            subsequent_masks.append(None)
            continue
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

    state_counts = {
        "receding": 0,
        "persistent_stagnation": 0,
        "re_inundated_explained": 0,
        "re_inundated_unexplained": 0,
        "drained": 0,
        "uncertain": 0,
    }

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
        area_timeline: list[float | None] = [init_area]
        pixel_timeline: list[int] = [pixel_count]

        for step_idx, s_mask in enumerate(subsequent_masks):
            if s_mask is None:
                area_timeline.append(None)
                pixel_timeline.append(0)
            else:
                overlap_pixels = int(np.sum(s_mask & region_pixels))
                overlap_area = float(overlap_pixels * pixel_area_km2)
                area_timeline.append(overlap_area)
                pixel_timeline.append(overlap_pixels)
                agg_timeline[step_idx + 1] += overlap_area

        # Evaluate compliance according to expected behavior
        state_timeline: tuple[TemporalState, ...] = ()
        traj_result: TrajectoryEvaluationResult | None = None

        if expected_behavior == ExpectedBehavior.RECEDING:
            traj_result = evaluate_four_state_trajectory(
                area_timeline=tuple(area_timeline),
                environmental_context=environmental_context,
                stagnation_tolerance=receding_tolerance_ratio,
                mmu_km2=min_region_pixels * pixel_area_km2,
            )
            is_compliant = traj_result.is_compliant
            diag = "; ".join(traj_result.diagnostic_reasons)
            state_timeline = traj_result.state_timeline

            # Aggregate state tally
            if len(state_timeline) > 1:
                fin_st = state_timeline[-1]
                if fin_st == TemporalState.RECEDING:
                    state_counts["receding"] += 1
                elif fin_st == TemporalState.PERSISTENT_STAGNATION:
                    state_counts["persistent_stagnation"] += 1
                elif fin_st == TemporalState.RE_INUNDATED_EXPLAINED:
                    state_counts["re_inundated_explained"] += 1
                elif fin_st == TemporalState.RE_INUNDATED_UNEXPLAINED:
                    state_counts["re_inundated_unexplained"] += 1
                elif fin_st == TemporalState.DRAINED:
                    state_counts["drained"] += 1
                else:
                    state_counts["uncertain"] += 1

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
            area_timeline_km2=tuple(round(a, 6) if a is not None else None for a in area_timeline),
            pixel_timeline=tuple(pixel_timeline),
            phenomenon=phenomenon,
            expected_behavior=expected_behavior,
            is_compliant=is_compliant,
            diagnostic_details=diag,
            state_timeline=state_timeline,
            trajectory_result=traj_result,
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
        temporal_states_summary=state_counts,
    )
