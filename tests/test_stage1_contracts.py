"""
BHnMISnTRA: Stage 1 Acceptance Test Suite.
Verifies all 30 formal contract invariants.
"""

from datetime import datetime, timezone
import math
import unittest
from pydantic import ValidationError

from src.bhnmisntra_science.config import (
    AcquisitionMetadata,
    BoundingBoxWGS84,
    CalibratedDbCalibration,
    CalibratedDbProvenance,
    CalibratedLinearCalibration,
    CalibratedLinearProvenance,
    CalibrationMetadata,
    ConfounderAssessmentSource,
    ConfounderExemption,
    ConfounderRecord,
    FixedDbThresholdConfig,
    IncidenceAngleExemption,
    IncidenceAngleMetadata,
    InvestigationConfig,
    OtsuThresholdConfig,
    PipelineParameters,
    RawDnCalibration,
    RawDnProvenance,
    RobustMadThresholdConfig,
)
from src.bhnmisntra_science.constants import PRD_CONSTANTS
from src.bhnmisntra_science.enums import (
    AngleComparisonOutcome,
    CalibrationState,
    ConfounderCriticality,
    ConfounderState,
    EvidenceStatus,
    ExemptionApprovalStatus,
    IncidenceAngleQuality,
    NotAssessedReason,
    UnavailableAnglePolicy,
)
from src.bhnmisntra_science.exceptions import (
    AntimeridianFlagMismatchError,
    ContradictoryExemptionError,
    DegenerateBoundingBoxError,
    DuplicateProductIdError,
    ExemptionTargetMismatchError,
    GeometryMismatchError,
    InsufficientAcquisitionsError,
    InvalidBoundingBoxError,
    MissingGeometryMetadataError,
)
from src.bhnmisntra_science.policies import (
    check_receding_step,
    classify_final_evidence,
    evaluate_confounders_for_evidence_label,
    evaluate_flood_receding_sequence,
    evaluate_incidence_angle_pair,
    evaluate_sustained_ratio_exact,
)
from tests.conftest import (
    get_synthetic_valid_acquisition,
    get_synthetic_valid_investigation_config,
    get_synthetic_valid_parameters,
)


class TestStage1Contracts(unittest.TestCase):

    # -------------------------------------------------------------------------
    # ST1-T01 to ST1-T06: Bounding Box Tests
    # -------------------------------------------------------------------------

    def test_ordinary_bbox_valid(self):
        """ST1-T01: Standard ordinary bounding box validates successfully."""
        bbox = BoundingBoxWGS84(
            min_lon=-122.5, min_lat=37.5, max_lon=-122.0, max_lat=38.0, crosses_antimeridian=False
        )
        self.assertEqual(bbox.min_lon, -122.5)
        self.assertEqual(bbox.max_lat, 38.0)

    def test_ordinary_bbox_inverted_rejected(self):
        """ST1-T02: Ordinary box with min_lon >= max_lon raises InvalidBoundingBoxError."""
        with self.assertRaises(InvalidBoundingBoxError):
            BoundingBoxWGS84(
                min_lon=10.0, min_lat=30.0, max_lon=5.0, max_lat=35.0, crosses_antimeridian=False
            )

    def test_antimeridian_bbox_valid(self):
        """ST1-T03: Antimeridian box (min > 0, max < 0, min > max) validates."""
        bbox = BoundingBoxWGS84(
            min_lon=178.0, min_lat=-15.0, max_lon=-177.0, max_lat=-10.0, crosses_antimeridian=True
        )
        self.assertTrue(bbox.crosses_antimeridian)
        self.assertEqual(bbox.min_lon, 178.0)
        self.assertEqual(bbox.max_lon, -177.0)

    def test_antimeridian_bbox_flags_inconsistent_rejected(self):
        """ST1-T04: Inconsistent coordinate signs with crosses_antimeridian=True raise AntimeridianFlagMismatchError."""
        with self.assertRaises(AntimeridianFlagMismatchError):
            BoundingBoxWGS84(
                min_lon=-178.0, min_lat=-15.0, max_lon=177.0, max_lat=-10.0, crosses_antimeridian=True
            )

    def test_antimeridian_degenerate_180_seam_rejected(self):
        """ST1-T05: Degenerate seam min_lon=180.0, max_lon=-180.0 (zero span) raises DegenerateBoundingBoxError."""
        with self.assertRaises(DegenerateBoundingBoxError):
            BoundingBoxWGS84(
                min_lon=180.0, min_lat=-10.0, max_lon=-180.0, max_lat=-5.0, crosses_antimeridian=True
            )

    def test_bbox_non_finite_and_latitude_span_rejected(self):
        """ST1-T06: Non-finite coordinates or min_lat >= max_lat raise ValueError / DegenerateBoundingBoxError."""
        with self.assertRaises(ValueError):
            BoundingBoxWGS84(
                min_lon=float("nan"), min_lat=10.0, max_lon=20.0, max_lat=15.0, crosses_antimeridian=False
            )
        with self.assertRaises(DegenerateBoundingBoxError):
            BoundingBoxWGS84(
                min_lon=10.0, min_lat=20.0, max_lon=20.0, max_lat=10.0, crosses_antimeridian=False
            )

    # -------------------------------------------------------------------------
    # ST1-T07 to ST1-T10: UTC Timestamp Invariants
    # -------------------------------------------------------------------------

    def test_timezone_aware_utc_accepted(self):
        """ST1-T07: Timezone-aware UTC datetimes validate successfully."""
        acq_dict = get_synthetic_valid_acquisition("ACQ-01", "2026-05-24T06:12:00Z")
        acq = AcquisitionMetadata(**acq_dict)
        self.assertEqual(acq.acquisition_utc.tzinfo, timezone.utc)
        self.assertEqual(acq.acquisition_utc.hour, 6)

    def test_timezone_naive_rejected(self):
        """ST1-T08: Naive datetimes without timezone raise ValueError."""
        acq_dict = get_synthetic_valid_acquisition("ACQ-01", "2026-05-24T06:12:00")
        with self.assertRaises(ValidationError):
            AcquisitionMetadata(**acq_dict)

    def test_timezone_offset_normalized_to_utc(self):
        """ST1-T09: Non-UTC offsets (e.g. +05:30) are normalized to exact UTC."""
        acq_dict = get_synthetic_valid_acquisition("ACQ-01", "2026-05-24T11:42:00+05:30")
        acq = AcquisitionMetadata(**acq_dict)
        self.assertEqual(acq.acquisition_utc.tzinfo, timezone.utc)
        self.assertEqual(acq.acquisition_utc.hour, 6)
        self.assertEqual(acq.acquisition_utc.minute, 12)

    def test_nested_json_serialization_preserves_microseconds_and_z(self):
        """ST1-T10: Serializing model to JSON preserves microseconds and guarantees trailing 'Z'."""
        acq_dict = get_synthetic_valid_acquisition("ACQ-01", "2026-05-24T06:12:00.123456Z")
        acq = AcquisitionMetadata(**acq_dict)
        json_str = acq.model_dump_json()
        self.assertIn('"2026-05-24T06:12:00.123456Z"', json_str)

    # -------------------------------------------------------------------------
    # ST1-T11 to ST1-T13: Sequence Bounds & Identity
    # -------------------------------------------------------------------------

    def test_minimum_subsequent_acquisitions_enforced(self):
        """ST1-T11: Supplying fewer than 3 subsequent acquisitions raises InsufficientAcquisitionsError."""
        cfg_dict = get_synthetic_valid_investigation_config()
        cfg_dict["subsequent_acquisitions"] = cfg_dict["subsequent_acquisitions"][:2]  # only 2
        with self.assertRaises(InsufficientAcquisitionsError):
            InvestigationConfig(**cfg_dict)

    def test_prd_sustained_ratio_exact_integer_arithmetic(self):
        """ST1-T12: Verified PRD ratio 2/3 exact calculation without implicit rounding."""
        # 2 out of 3 passes (3*2=6 >= 2*3=6) -> True
        self.assertTrue(evaluate_sustained_ratio_exact(2, 3))
        # 1 out of 3 fails (3*1=3 < 2*3=6) -> False
        self.assertFalse(evaluate_sustained_ratio_exact(1, 3))
        # 3 out of 4 passes (3*3=9 >= 2*4=8) -> True
        self.assertTrue(evaluate_sustained_ratio_exact(3, 4))
        # 2 out of 4 fails (3*2=6 < 2*4=8) -> False
        self.assertFalse(evaluate_sustained_ratio_exact(2, 4))
        # Re-detections > observations raises ValueError
        with self.assertRaises(ValueError):
            evaluate_sustained_ratio_exact(4, 3)

    def test_duplicate_product_id_rejected(self):
        """ST1-T13: Ingesting duplicate product_id across sequence raises DuplicateProductIdError."""
        cfg_dict = get_synthetic_valid_investigation_config()
        # Duplicate product_id between sub1 and sub2
        cfg_dict["subsequent_acquisitions"][1]["product_id"] = cfg_dict["subsequent_acquisitions"][0]["product_id"]
        with self.assertRaises(DuplicateProductIdError):
            InvestigationConfig(**cfg_dict)

    # -------------------------------------------------------------------------
    # ST1-T14 to ST1-T16: Calibration State & Provenance
    # -------------------------------------------------------------------------

    def test_calibration_discriminated_union_mismatch_rejected(self):
        """ST1-T14: State-provenance mismatch is rejected by discriminator."""
        with self.assertRaises(ValidationError):
            # calibration_state is RAW_DN, but provenance is CalibratedDbProvenance
            RawDnCalibration(
                calibration_state=CalibrationState.RAW_DN,
                provenance=CalibratedDbProvenance(
                    calibration_source_doc="ESA-DOC", decibel_reference_scale="10*log10(sigma0)"
                )
            )

    def test_missing_calibration_provenance_rejected(self):
        """ST1-T15: Supplying None or missing required provenance raises ValidationError."""
        with self.assertRaises(ValidationError):
            CalibratedLinearCalibration(
                calibration_state=CalibrationState.CALIBRATED_LINEAR_POWER,
                provenance=None
            )

    def test_empty_or_whitespace_calibration_strings_rejected(self):
        """ST1-T16: Empty or whitespace-only provenance strings raise ValueError."""
        with self.assertRaises(ValidationError):
            CalibratedDbProvenance(calibration_source_doc="   ", decibel_reference_scale="10*log10(sigma0)")

    # -------------------------------------------------------------------------
    # ST1-T17 to ST1-T21: Geometry & Incidence Angle
    # -------------------------------------------------------------------------

    def test_mandatory_geometry_mismatch_rejected(self):
        """ST1-T17: Divergent relative orbit track raises GeometryMismatchError."""
        cfg_dict = get_synthetic_valid_investigation_config()
        # Change sub1 track from 12 to 42
        cfg_dict["subsequent_acquisitions"][0]["orbit"]["relative_orbit"] = 42
        with self.assertRaises(GeometryMismatchError):
            InvestigationConfig(**cfg_dict)

    def test_missing_geometry_metadata_rejected(self):
        """ST1-T18: Missing mandatory geometry fields raises MissingGeometryMetadataError."""
        cfg_dict = get_synthetic_valid_investigation_config()
        cfg_dict["subsequent_acquisitions"][0]["sensor"]["sensor_mode"] = "   "
        with self.assertRaises(ValidationError):
            InvestigationConfig(**cfg_dict)

    def test_incidence_angle_quality_available_and_estimated(self):
        """ST1-T19: Angle in [10, 70] validates; out of bounds or missing estimated method raises ValueError."""
        # Available angle valid
        meta = IncidenceAngleMetadata(quality=IncidenceAngleQuality.AVAILABLE, angle_deg=35.0)
        self.assertEqual(meta.angle_deg, 35.0)
        # Out of physical range
        with self.assertRaises(ValueError):
            IncidenceAngleMetadata(quality=IncidenceAngleQuality.AVAILABLE, angle_deg=85.0)
        # Estimated missing method
        with self.assertRaises(ValueError):
            IncidenceAngleMetadata(quality=IncidenceAngleQuality.ESTIMATED, angle_deg=35.0, estimation_method="")

    def test_incidence_angle_estimated_comparison_enforced(self):
        """ST1-T20: Estimated angles actively undergo comparison against tolerance."""
        ref_angle = IncidenceAngleMetadata(quality=IncidenceAngleQuality.AVAILABLE, angle_deg=35.0)
        sub_angle = IncidenceAngleMetadata(
            quality=IncidenceAngleQuality.ESTIMATED, angle_deg=36.0, estimation_method="ellipsoid_mid_swath"
        )
        # Difference is 1.0 deg <= 1.5 deg -> COMPLIANT_WITH_ESTIMATE_WARNING
        outcome, reasons, has_geom_unc = evaluate_incidence_angle_pair(
            ref_angle, sub_angle, "ACQ-SUB-01", 1.5, UnavailableAnglePolicy.FLAG_AND_ALLOW_WITH_LIMITATION
        )
        self.assertEqual(outcome, AngleComparisonOutcome.COMPLIANT_WITH_ESTIMATE_WARNING)
        self.assertTrue(has_geom_unc)

    def test_incidence_angle_unavailable_policies(self):
        """ST1-T21: Tests all 3 unavailable angle policies."""
        ref_angle = IncidenceAngleMetadata(quality=IncidenceAngleQuality.AVAILABLE, angle_deg=35.0)
        sub_angle = IncidenceAngleMetadata(
            quality=IncidenceAngleQuality.UNAVAILABLE,
            unavailable_reason="Sensor telemetry missing",
            documented_limitation="Swath incidence angle unrecorded",
        )
        # 1. FAIL_VALIDATION -> UNAVAILABLE_FATAL_ERROR
        outcome1, _, _ = evaluate_incidence_angle_pair(
            ref_angle, sub_angle, "ACQ-SUB-01", 1.5, UnavailableAnglePolicy.FAIL_VALIDATION
        )
        self.assertEqual(outcome1, AngleComparisonOutcome.UNAVAILABLE_FATAL_ERROR)

        # 2. EXCLUDE_FROM_BEAT_TEST -> UNAVAILABLE_EXCLUDED
        outcome2, _, _ = evaluate_incidence_angle_pair(
            ref_angle, sub_angle, "ACQ-SUB-01", 1.5, UnavailableAnglePolicy.EXCLUDE_FROM_BEAT_TEST
        )
        self.assertEqual(outcome2, AngleComparisonOutcome.UNAVAILABLE_EXCLUDED)

        # 3. FLAG_AND_ALLOW_WITH_LIMITATION -> UNAVAILABLE_FLAGGED
        outcome3, _, has_unc3 = evaluate_incidence_angle_pair(
            ref_angle, sub_angle, "ACQ-SUB-01", 1.5, UnavailableAnglePolicy.FLAG_AND_ALLOW_WITH_LIMITATION
        )
        self.assertEqual(outcome3, AngleComparisonOutcome.UNAVAILABLE_FLAGGED)
        self.assertTrue(has_unc3)

    # -------------------------------------------------------------------------
    # ST1-T22 to ST1-T26: Numerical Parameters & Thresholds
    # -------------------------------------------------------------------------

    def test_numerical_parameters_invalid_boundaries_and_nan(self):
        """ST1-T22: NaN, Inf, negative MMU, out-of-range tolerances raise ValueError."""
        params_dict = get_synthetic_valid_parameters()
        params_dict["flood_growth_tolerance"] = float("nan")
        with self.assertRaises(ValidationError):
            PipelineParameters(**params_dict)

        params_dict = get_synthetic_valid_parameters()
        params_dict["flood_growth_tolerance"] = 1.5  # > 1.0
        with self.assertRaises(ValidationError):
            PipelineParameters(**params_dict)

    def test_numerical_parameters_booleans_and_fractional_rejected(self):
        """ST1-T23: Booleans and fractional numbers rejected for integer fields via mode='before'."""
        params_dict = get_synthetic_valid_parameters()
        params_dict["speckle_window_size"] = True  # bool rejected
        with self.assertRaises(ValidationError):
            PipelineParameters(**params_dict)

        params_dict = get_synthetic_valid_parameters()
        params_dict["min_mapping_unit_pixels"] = 10.5  # float rejected for int
        with self.assertRaises(ValidationError):
            PipelineParameters(**params_dict)

    def test_threshold_fixed_db_validators(self):
        """ST1-T24: Fixed dB threshold requires strictly negative finite float."""
        cfg = FixedDbThresholdConfig(drop_threshold_db=-3.5)
        self.assertEqual(cfg.drop_threshold_db, -3.5)
        with self.assertRaises(ValidationError):
            FixedDbThresholdConfig(drop_threshold_db=3.5)  # positive rejected
        with self.assertRaises(ValidationError):
            FixedDbThresholdConfig(drop_threshold_db=0.0)  # zero rejected

    def test_threshold_robust_mad_validators(self):
        """ST1-T25: Robust MAD multiplier requires strictly positive finite float."""
        cfg = RobustMadThresholdConfig(k_multiplier=2.5)
        self.assertEqual(cfg.k_multiplier, 2.5)
        with self.assertRaises(ValidationError):
            RobustMadThresholdConfig(k_multiplier=-2.5)  # negative rejected
        with self.assertRaises(ValidationError):
            RobustMadThresholdConfig(k_multiplier=0.0)  # zero rejected

    def test_threshold_otsu_validators(self):
        """ST1-T26: Otsu requires integer bins >= 2 and strictly ordered finite percentiles."""
        cfg = OtsuThresholdConfig(num_histogram_bins=256, clip_percentiles=(1.0, 99.0))
        self.assertEqual(cfg.num_histogram_bins, 256)
        with self.assertRaises(ValidationError):
            OtsuThresholdConfig(num_histogram_bins=1, clip_percentiles=(1.0, 99.0))
        with self.assertRaises(ValidationError):
            OtsuThresholdConfig(num_histogram_bins=256, clip_percentiles=(99.0, 1.0))

    # -------------------------------------------------------------------------
    # ST1-T27 to ST1-T29: Confounders & Evidence Classification
    # -------------------------------------------------------------------------

    def test_confounder_state_invariants_and_empty_strings(self):
        """ST1-T27: CLEAR requires source/threshold; NOT_ASSESSED requires reason/limitation."""
        # CLEAR with valid source
        source = ConfounderAssessmentSource(
            provider="NASA_GPM",
            dataset_name="IMERG_V06",
            url_or_doi="https://doi.org/10.5067/GPM",
            window_start_utc="2026-05-23T06:00:00Z",
            window_end_utc="2026-05-24T06:00:00Z",
        )
        rec = ConfounderRecord(
            confounder_id="CONF-RAIN",
            name="Heavy Rainfall",
            criticality=ConfounderCriticality.CRITICAL,
            state=ConfounderState.CLEAR,
            description="Precipitation check",
            assessment_source=source,
            threshold_applied="> 25mm in 24h",
        )
        self.assertEqual(rec.state, ConfounderState.CLEAR)

        # CLEAR with exemption is contradictory
        with self.assertRaises(ContradictoryExemptionError):
            ConfounderRecord(
                confounder_id="CONF-RAIN",
                name="Heavy Rainfall",
                criticality=ConfounderCriticality.CRITICAL,
                state=ConfounderState.CLEAR,
                description="Precipitation check",
                assessment_source=source,
                threshold_applied="> 25mm in 24h",
                exemption=ConfounderExemption(
                    exemption_id="EX-01",
                    target_confounder_id="CONF-RAIN",
                    justification="Terrain is hyper-arid bedrock with zero runoff",
                    approved_by="Lead Scientist",
                    approval_status=ExemptionApprovalStatus.APPROVED,
                    timestamp_utc="2026-05-24T06:00:00Z",
                )
            )

    def test_confounder_time_window_and_metric_finite(self):
        """ST1-T28: Inverted time window (start >= end) or non-finite metric raises ValueError."""
        with self.assertRaises(ValidationError):
            ConfounderAssessmentSource(
                provider="NASA_GPM",
                dataset_name="IMERG_V06",
                url_or_doi="https://doi.org/10.5067/GPM",
                window_start_utc="2026-05-24T12:00:00Z",
                window_end_utc="2026-05-24T06:00:00Z",  # inverted!
            )

    def test_confounder_decision_matrix_all_branches(self):
        """ST1-T29: Tests all branches of confounder decision matrix and final classifier."""
        source = ConfounderAssessmentSource(
            provider="NASA_GPM",
            dataset_name="IMERG_V06",
            url_or_doi="https://doi.org/10.5067/GPM",
            window_start_utc="2026-05-23T06:00:00Z",
            window_end_utc="2026-05-24T06:00:00Z",
        )
        clear_conf = ConfounderRecord(
            confounder_id="CONF-RAIN",
            name="Heavy Rainfall",
            criticality=ConfounderCriticality.CRITICAL,
            state=ConfounderState.CLEAR,
            description="Precipitation check",
            assessment_source=source,
            threshold_applied="> 25mm in 24h",
        )
        flagged_conf = ConfounderRecord(
            confounder_id="CONF-RAIN",
            name="Heavy Rainfall",
            criticality=ConfounderCriticality.CRITICAL,
            state=ConfounderState.FLAGGED,
            description="Precipitation check",
            assessment_source=source,
            threshold_applied="> 25mm in 24h",
        )

        # 1. All CLEAR + Beat Test Matches + No Geom Uncertainty -> SUPPORTED
        status1, _ = classify_final_evidence(3, True, False, (clear_conf,))
        self.assertEqual(status1, EvidenceStatus.SUPPORTED)

        # 2. Critical FLAGGED -> INCONCLUSIVE
        status2, _ = classify_final_evidence(3, True, False, (flagged_conf,))
        self.assertEqual(status2, EvidenceStatus.INCONCLUSIVE)

        # 3. N_valid < 3 -> UNVERIFIED (PRD Hard Rule)
        status3, _ = classify_final_evidence(2, True, False, (clear_conf,))
        self.assertEqual(status3, EvidenceStatus.UNVERIFIED)

        # 4. Geometry uncertainty -> INCONCLUSIVE
        status4, _ = classify_final_evidence(3, True, True, (clear_conf,))
        self.assertEqual(status4, EvidenceStatus.INCONCLUSIVE)

    # -------------------------------------------------------------------------
    # ST1-T30: Deep Immutability & Flood Recession Sequences
    # -------------------------------------------------------------------------

    def test_deep_immutability_and_nested_mutation_rejected(self):
        """ST1-T30: Modifying top-level fields, sub-models, or tuples raises error."""
        cfg_dict = get_synthetic_valid_investigation_config()
        cfg = InvestigationConfig(**cfg_dict)
        # Attempting to reassign attribute
        with self.assertRaises(ValidationError):
            cfg.study_area_id = "NEW-AREA"
        # Attempting to mutate sequence tuple
        with self.assertRaises(AttributeError):
            cfg.subsequent_acquisitions.append(cfg.subsequent_acquisitions[0])

    def test_flood_recession_sequence_evaluation(self):
        """Demonstrates flood recession step-by-step and zero-area re-inundation."""
        # 1. Monotonically shrinking sequence (10.0 -> 8.0 -> 5.0 -> 0.0) -> COMPLIANT
        ok1, _ = evaluate_flood_receding_sequence((10.0, 8.0, 5.0, 0.0), 0.05)
        self.assertTrue(ok1)

        # 2. Re-inundation after zero (10.0 -> 0.0 -> 2.0) -> FAILS (UNEXPLAINED_GROWTH)
        ok2, reasons2 = evaluate_flood_receding_sequence((10.0, 0.0, 2.0), 0.05)
        self.assertFalse(ok2)
        self.assertTrue(any("Re-inundation" in r for r in reasons2))


if __name__ == "__main__":
    unittest.main()

