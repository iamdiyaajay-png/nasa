"""
BHnMISnTRA: Member 1 Data & Scientific Intelligence
Authoritative Scientific Policy Engines & Evidence Classification Gates.
"""

from typing import Any

from .constants import PRD_CONSTANTS
from .enums import (
    AngleComparisonOutcome,
    ConfounderCriticality,
    ConfounderState,
    EvidenceStatus,
    ExemptionApprovalStatus,
    IncidenceAngleQuality,
    UnavailableAnglePolicy,
)
from .exceptions import ExemptionTargetMismatchError
from .types import enforce_strict_finite_float, enforce_strict_int


# =============================================================================
# 1. INCIDENCE ANGLE EVALUATION POLICY
# =============================================================================

def evaluate_incidence_angle_pair(
    ref_angle_meta: Any,
    sub_angle_meta: Any,
    subsequent_acquisition_id: str,
    max_divergence_deg: float,
    policy: UnavailableAnglePolicy,
    is_subsequent_observation: bool = True
) -> tuple[AngleComparisonOutcome, list[str], bool]:
    """
    Evaluates mid-swath incidence angle compatibility between reference and subsequent passes.
    Enforces target_acquisition_id matching.
    Guarantees administrative exemptions do NOT bypass policy halts or verify physical geometry.
    Returns: (outcome, reasons, has_geometry_uncertainty)
    """
    reasons: list[str] = []
    has_geometry_uncertainty: bool = False

    # 1. Target Acquisition ID Binding Validation
    if sub_angle_meta.exemption is not None:
        if sub_angle_meta.exemption.target_acquisition_id != subsequent_acquisition_id:
            raise ExemptionTargetMismatchError(
                f"Exemption target ID '{sub_angle_meta.exemption.target_acquisition_id}' "
                f"does not match evaluating acquisition ID '{subsequent_acquisition_id}'"
            )

    # 2. Unavailable Angle Handling (Policy Precedence)
    if ref_angle_meta.quality == IncidenceAngleQuality.UNAVAILABLE or sub_angle_meta.quality == IncidenceAngleQuality.UNAVAILABLE:
        # Policy: FAIL_VALIDATION must NEVER be bypassed by an administrative exemption
        if policy == UnavailableAnglePolicy.FAIL_VALIDATION:
            reasons.append("POLICY_HALT: Unavailable incidence angle rejected by FAIL_VALIDATION policy.")
            return AngleComparisonOutcome.UNAVAILABLE_FATAL_ERROR, reasons, True

        # Policy: EXCLUDE_FROM_BEAT_TEST excludes the observation
        if policy == UnavailableAnglePolicy.EXCLUDE_FROM_BEAT_TEST:
            if is_subsequent_observation:
                reasons.append("SOFT_EXCLUSION: Subsequent acquisition has unavailable angle; excluded from Beat Test.")
                return AngleComparisonOutcome.UNAVAILABLE_EXCLUDED, reasons, True
            else:
                reasons.append("FATAL_ERROR: Baseline acquisition has unavailable incidence angle.")
                return AngleComparisonOutcome.UNAVAILABLE_FATAL_ERROR, reasons, True

        # Policy: FLAG_AND_ALLOW_WITH_LIMITATION
        if policy == UnavailableAnglePolicy.FLAG_AND_ALLOW_WITH_LIMITATION:
            has_geometry_uncertainty = True
            if sub_angle_meta.exemption is not None and sub_angle_meta.exemption.approval_status == ExemptionApprovalStatus.APPROVED:
                reasons.append(
                    f"ADMINISTRATIVE EXEMPTION: Missing angle approved by {sub_angle_meta.exemption.approved_by}: "
                    f"'{sub_angle_meta.exemption.justification}'. Physical geometry compatibility remains UNVERIFIED."
                )
            else:
                limitation = sub_angle_meta.documented_limitation or ref_angle_meta.documented_limitation or "Unassessed angle"
                reasons.append(f"FLAGGED: Proceeding with unassessed angle under limitation: {limitation}")
            return AngleComparisonOutcome.UNAVAILABLE_FLAGGED, reasons, has_geometry_uncertainty

    # 3. Numeric Angle Comparison (AVAILABLE or ESTIMATED)
    theta_ref = ref_angle_meta.angle_deg
    theta_sub = sub_angle_meta.angle_deg
    delta_theta = abs(theta_ref - theta_sub)

    is_estimated = (
        ref_angle_meta.quality == IncidenceAngleQuality.ESTIMATED or
        sub_angle_meta.quality == IncidenceAngleQuality.ESTIMATED
    )
    if is_estimated:
        has_geometry_uncertainty = True

    if delta_theta <= max_divergence_deg:
        if is_estimated:
            reasons.append(
                f"COMPLIANT_WITH_WARNING: Angle divergence {delta_theta:.2f}° <= {max_divergence_deg}°, "
                f"but relies on estimated angles (ref={ref_angle_meta.quality}, sub={sub_angle_meta.quality})."
            )
            return AngleComparisonOutcome.COMPLIANT_WITH_ESTIMATE_WARNING, reasons, has_geometry_uncertainty
        reasons.append(f"COMPLIANT: Angle divergence {delta_theta:.2f}° within tolerance {max_divergence_deg}°.")
        return AngleComparisonOutcome.COMPLIANT, reasons, has_geometry_uncertainty

    # 4. Divergence Exceeds Tolerance
    if sub_angle_meta.exemption is not None and sub_angle_meta.exemption.approval_status == ExemptionApprovalStatus.APPROVED:
        has_geometry_uncertainty = True
        reasons.append(
            f"ADMINISTRATIVE EXEMPTION: Angle divergence {delta_theta:.2f}° exceeds {max_divergence_deg}°, "
            f"approved by {sub_angle_meta.exemption.approved_by}: '{sub_angle_meta.exemption.justification}'. "
            f"Physical geometry is INCOMPATIBLE."
        )
        return AngleComparisonOutcome.DIVERGENCE_EXEMPTED, reasons, has_geometry_uncertainty

    reasons.append(f"VIOLATION: Angle divergence {delta_theta:.2f}° strictly exceeds tolerance {max_divergence_deg}°.")
    return AngleComparisonOutcome.DIVERGENCE_VIOLATION, reasons, True


# =============================================================================
# 2. CONFOUNDER EVALUATION POLICY
# =============================================================================

def evaluate_confounders_for_evidence_label(
    confounders: tuple[Any, ...],
    beat_test_matches: bool,
    has_geometry_uncertainty: bool = False
) -> tuple[EvidenceStatus, list[str]]:
    """
    Evaluates confounders for evidence labeling.
    Correctly references c.exemption.justification.
    Enforces that administrative exemptions do NOT manufacture scientific evidence.
    """
    reasons: list[str] = []

    if not beat_test_matches:
        reasons.append("Beat Test: Temporal trajectory does not match expected physical profile.")
        return EvidenceStatus.INCONCLUSIVE, reasons

    if has_geometry_uncertainty:
        reasons.append("Geometry: Observation relied on administrative override or unassessed angle; physical geometry unverified.")
        return EvidenceStatus.INCONCLUSIVE, reasons

    has_critical_unresolved_issue = False

    for c in confounders:
        if c.criticality == ConfounderCriticality.CRITICAL:
            if c.state == ConfounderState.FLAGGED:
                if c.exemption is not None and c.exemption.approval_status == ExemptionApprovalStatus.APPROVED:
                    reasons.append(
                        f"CRITICAL FLAGGED with APPROVED EXEMPTION: '{c.name}' flagged, administratively approved by "
                        f"{c.exemption.approved_by} ('{c.exemption.justification}'). "
                        f"Physical risk remains scientifically unresolved."
                    )
                    has_critical_unresolved_issue = True
                else:
                    reasons.append(f"CRITICAL FLAGGED: Confounder '{c.name}' active ({c.description}).")
                    has_critical_unresolved_issue = True

            elif c.state == ConfounderState.NOT_ASSESSED:
                if c.exemption is not None and c.exemption.approval_status == ExemptionApprovalStatus.APPROVED:
                    reasons.append(
                        f"CRITICAL NOT ASSESSED with APPROVED EXEMPTION: '{c.name}' missing, administratively approved by "
                        f"{c.exemption.approved_by} ('{c.exemption.justification}'). "
                        f"Absence of data is not evidence of absence."
                    )
                    has_critical_unresolved_issue = True
                elif c.exemption is not None and c.exemption.approval_status == ExemptionApprovalStatus.PENDING_REVIEW:
                    reasons.append(f"CRITICAL NOT ASSESSED: '{c.name}' exemption is PENDING REVIEW.")
                    has_critical_unresolved_issue = True
                else:
                    reasons.append(f"CRITICAL NOT ASSESSED: '{c.name}' missing without exemption ({c.scientific_limitation}).")
                    has_critical_unresolved_issue = True

        elif c.criticality == ConfounderCriticality.NON_CRITICAL:
            if c.state == ConfounderState.FLAGGED:
                reasons.append(f"NON-CRITICAL WARNING: Confounder '{c.name}' flagged ({c.description}).")
            elif c.state == ConfounderState.NOT_ASSESSED:
                reasons.append(f"NON-CRITICAL DISCLOSURE: Confounder '{c.name}' not assessed ({c.scientific_limitation}).")

    if has_critical_unresolved_issue:
        return EvidenceStatus.INCONCLUSIVE, reasons

    reasons.append("All critical confounders assessed and verified CLEAR. Physical geometry verified.")
    return EvidenceStatus.SUPPORTED, reasons


# =============================================================================
# 3. BEAT TEST ENFORCEMENT & ZERO-AREA RECESSION DYNAMICS
# =============================================================================

def evaluate_sustained_ratio_exact(re_detections: Any, valid_observations: Any) -> bool:
    """
    Evaluates re_detections / valid_observations >= 2/3 using exact integer cross-multiplication.
    Rejects booleans, floats, strings, negative counts, and re_detections > valid_observations.
    """
    m = enforce_strict_int(re_detections, "re_detections")
    n = enforce_strict_int(valid_observations, "valid_observations")

    if m < 0:
        raise ValueError(f"re_detections must be non-negative, got {m}")
    if n < 1:
        raise ValueError(f"valid_observations must be >= 1, got {n}")
    if m > n:
        raise ValueError(f"re_detections ({m}) cannot exceed valid_observations ({n})")

    # PRD Exact Rule: 3 * m >= 2 * n
    return (PRD_CONSTANTS.SUSTAINED_DENOMINATOR * m) >= (PRD_CONSTANTS.SUSTAINED_NUMERATOR * n)


def check_receding_step(area_prev: Any, area_curr: Any, tolerance: Any) -> tuple[bool, str]:
    """
    Evaluates a single temporal step in flood recession.
    Enforces strict numeric validation and zero-area boundary dynamics.
    """
    a_prev = enforce_strict_finite_float(area_prev, "area_prev")
    a_curr = enforce_strict_finite_float(area_curr, "area_curr")
    tol = enforce_strict_finite_float(tolerance, "tolerance")

    if a_prev < 0.0 or a_curr < 0.0:
        raise ValueError(f"Areas must be non-negative, got prev={a_prev}, curr={a_curr}")
    if not (0.0 <= tol <= 1.0):
        raise ValueError(f"flood_growth_tolerance must be in [0.0, 1.0], got {tol}")

    if a_prev == 0.0:
        if a_curr == 0.0:
            return True, "Area remained 0.0 km²; compliant."
        else:
            return False, f"UNEXPLAINED_GROWTH (Re-inundation). Water emerged (area={a_curr:.4f} km²) after complete drainage (0.0 km²)."

    max_allowed = a_prev * (1.0 + tol)
    if a_curr <= max_allowed:
        return True, f"Receding compliant: area {a_curr:.4f} <= allowed {max_allowed:.4f} km²."

    growth_pct = ((a_curr - a_prev) / a_prev) * 100.0
    return False, f"UNEXPLAINED_GROWTH. Area grew by {growth_pct:.1f}%, exceeding {tol*100.0}% tolerance."


def evaluate_flood_receding_sequence(
    area_sequence: tuple[Any, ...],
    tolerance: Any
) -> tuple[bool, list[str]]:
    """
    Evaluates step-by-step flood recession across a sequence of observations: (A_0, A_1, ..., A_N).
    Enforces strict numeric validation, positive bounds, and zero-area boundary physics.
    """
    tol = enforce_strict_finite_float(tolerance, "tolerance")
    if not (0.0 <= tol <= 1.0):
        raise ValueError(f"flood_growth_tolerance must be in [0.0, 1.0], got {tol}")

    if not isinstance(area_sequence, tuple):
        raise ValueError(f"area_sequence must be a tuple, got {type(area_sequence).__name__}")
    if len(area_sequence) < 2:
        raise ValueError(f"area_sequence must have at least 2 observations, got {len(area_sequence)}")

    clean_areas: list[float] = []
    for idx, a in enumerate(area_sequence):
        val = enforce_strict_finite_float(a, f"area_sequence[{idx}]")
        if val < 0.0:
            raise ValueError(f"area_sequence[{idx}] must be non-negative, got {val}")
        clean_areas.append(val)

    reasons: list[str] = []
    is_compliant = True

    for k in range(1, len(clean_areas)):
        step_ok, step_msg = check_receding_step(clean_areas[k - 1], clean_areas[k], tol)
        reasons.append(f"Step {k}: {step_msg}")
        if not step_ok:
            is_compliant = False

    return is_compliant, reasons


# =============================================================================
# 4. ONE AUTHORITATIVE FINAL SCIENTIFIC CLASSIFIER
# =============================================================================

def classify_final_evidence(
    valid_subsequent_observations_count: int,
    beat_test_matches: bool,
    has_geometry_uncertainty: bool,
    confounders: tuple[Any, ...]
) -> tuple[EvidenceStatus, list[str]]:
    """
    The ONE authoritative scientific evidence classification gate for BHnMISnTRA.
    No helper function or administrative exemption may independently authorize Supported.

    SUPPORTED requires ALL of:
    1. At least 3 valid subsequent observations (N_valid >= 3).
    2. Beat Test compliance (beat_test_matches is True).
    3. Physical geometry compatibility verified (has_geometry_uncertainty is False).
    4. All critical confounders assessed and verified CLEAR.
    5. Zero unresolved scientific uncertainty.
    """
    reasons: list[str] = []

    # PRD Hard Rule: Fewer than 3 valid repeat observations forces Unverified
    if valid_subsequent_observations_count < PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED:
        reasons.append(
            f"PRD Hard Rule: Insufficient repeat observations ({valid_subsequent_observations_count} < "
            f"{PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED}). We make no claim."
        )
        return EvidenceStatus.UNVERIFIED, reasons

    # Evaluate Confounders, Geometry and Beat Test
    label, eval_reasons = evaluate_confounders_for_evidence_label(
        confounders=confounders,
        beat_test_matches=beat_test_matches,
        has_geometry_uncertainty=has_geometry_uncertainty,
    )
    reasons.extend(eval_reasons)
    return label, reasons

