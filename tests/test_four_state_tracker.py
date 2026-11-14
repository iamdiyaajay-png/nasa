"""
BHnMISnTRA: Four-State Temporal Beat Test Tracker Unit & Regression Tests.
Phase 2.2 Acceptance Test Suite.
"""

import unittest
import numpy as np

from src.bhnmisntra_science.enums import (
    EvidenceStatus,
    ExpectedBehavior,
    PhenomenonType,
    TemporalClusterState,
    TemporalState,
)
from src.bhnmisntra_science.beat_test.tracker import (
    RegionTrackingResult,
    TemporalStepEvaluation,
    TrajectoryEvaluationResult,
    evaluate_four_state_trajectory,
    evaluate_mixed_spatial_trajectories,
)


class TestFourStateTracker(unittest.TestCase):
    """
    Focused tests for the Four-State Temporal Model:
      PERSISTENT_STAGNATION, RECEDING, RE_INUNDATED, DRAINED.
    Enforces all requirements from Phase 1.5, Phase 1.4.1, and Phase 2.2 tasks.
    """

    # =========================================================================
    # 1. PERSISTENT STAGNATION (DELTAIC POLDER PHYSICS)
    # =========================================================================

    def test_01_persistent_stagnation_compliant(self) -> None:
        """
        Verifies that water trapped in below-sea-level polders with stable area
        (|ΔA| / A_prev <= 15%) is classified as PERSISTENT_STAGNATION and is COMPLIANT.
        Universal monotonic recession is NOT enforced.
        """
        timeline = [10.0, 9.8, 9.5, 9.6]  # 4 observations (t1 + s1, s2, s3)
        res = evaluate_four_state_trajectory(timeline, stagnation_tolerance=0.15)

        self.assertTrue(res.is_compliant)
        self.assertEqual(res.valid_observations_count, 3)
        self.assertEqual(
            res.state_timeline,
            (
                TemporalState.PEAK,
                TemporalState.PERSISTENT_STAGNATION,
                TemporalState.PERSISTENT_STAGNATION,
                TemporalState.PERSISTENT_STAGNATION,
            ),
        )
        self.assertEqual(res.evidence_status, EvidenceStatus.SUPPORTED)
        self.assertFalse(res.unexplained_change_detected)
        self.assertIn("PERSISTENT_STAGNATION", res.diagnostic_reasons[1])
        self.assertIn("Compliant for below-sea-level deltaic polders", res.diagnostic_reasons[1])

        # Test 3-tuple unpacking
        ok, states, msgs = res
        self.assertTrue(ok)
        self.assertEqual(len(states), 4)

    # =========================================================================
    # 2. GRADUAL RECESSION
    # =========================================================================

    def test_02_gradual_recession_compliant(self) -> None:
        """Verifies active gradual drainage (ΔA / A_prev < -15%) is classified as RECEDING."""
        timeline = [10.0, 7.5, 4.5, 2.0]  # shrinks continuously
        res = evaluate_four_state_trajectory(timeline, recession_tolerance=0.15)

        self.assertTrue(res.is_compliant)
        self.assertEqual(res.valid_observations_count, 3)
        self.assertEqual(
            res.state_timeline,
            (
                TemporalState.PEAK,
                TemporalState.RECEDING,
                TemporalState.RECEDING,
                TemporalState.RECEDING,
            ),
        )
        self.assertEqual(res.evidence_status, EvidenceStatus.SUPPORTED)
        self.assertFalse(res.unexplained_change_detected)

    # =========================================================================
    # 3. RE-INUNDATION EXPLAINED (THREE-TIER CORROBORATION)
    # =========================================================================

    def test_03_re_inundation_explained_under_three_tier_framework(self) -> None:
        """
        Verifies secondary flood surge (> 15% growth) is COMPLIANT WITH EXPLANATION
        when corroborated by the Three-Tier Physical Corroboration Framework:
          Tier 1 (Forcing: rain >= 50mm or stage rise >= 1m)
          Tier 2 (Hydraulic Plausibility: low elevation, contiguous to waterways)
          Tier 3 (Artifact Exclusion: wind < 4.0 m/s)
        """
        timeline = [10.0, 4.0, 8.5, 2.0]  # Step 2 surges +112% from 4.0 to 8.5 km²
        env_context = [
            {"rainfall_12d_mm": 10.0, "wind_speed_mps": 2.0, "hydraulically_plausible": True},
            {"rainfall_12d_mm": 85.0, "wind_speed_mps": 2.5, "hydraulically_plausible": True},  # Step 2: Corroborated!
            {"rainfall_12d_mm": 15.0, "wind_speed_mps": 2.0, "hydraulically_plausible": True},
        ]
        res = evaluate_four_state_trajectory(timeline, environmental_context=env_context)

        self.assertTrue(res.is_compliant)
        self.assertEqual(res.state_timeline[2], TemporalState.RE_INUNDATED_EXPLAINED)
        self.assertFalse(res.unexplained_change_detected)
        self.assertEqual(res.evidence_status, EvidenceStatus.SUPPORTED)
        # Verify contextual corroboration language
        self.assertIn("Corroborating environmental context only, not isolated causation", res.diagnostic_reasons[2])

    # =========================================================================
    # 4. EVENTUAL DRAINAGE
    # =========================================================================

    def test_04_eventual_drainage(self) -> None:
        """Verifies that area falling below MMU threshold (0.001 km² = 10 px) transitions to DRAINED."""
        timeline = [10.0, 9.8, 3.5, 0.0005, 0.0]  # MMU = 0.001 km²
        res = evaluate_four_state_trajectory(timeline, mmu_km2=0.001)

        self.assertTrue(res.is_compliant)
        self.assertEqual(
            res.state_timeline,
            (
                TemporalState.PEAK,
                TemporalState.PERSISTENT_STAGNATION,
                TemporalState.RECEDING,
                TemporalState.DRAINED,
                TemporalState.DRAINED,
            ),
        )
        self.assertEqual(res.evidence_status, EvidenceStatus.SUPPORTED)

    # =========================================================================
    # 5. MIXED SPATIAL TRAJECTORIES
    # =========================================================================

    def test_05_mixed_spatial_trajectories(self) -> None:
        """
        Verifies that multiple independent spatial clusters across a scene can exhibit
        different, heterogeneous hydrological behaviors simultaneously.
        """
        c1 = [10.0, 9.8, 4.0, 0.0]  # Polder: Stagnation -> Receding -> Drained
        c2 = [8.0, 3.0, 0.5, 0.0]   # Riverbank: Receding -> Receding -> Drained
        c3 = [12.0, 5.0, 9.0, 3.0]  # Canal: Receding -> Surge (Explained) -> Receding
        c4 = [6.0, 2.0, 5.0, 1.0]   # Anomaly: Receding -> Surge (Unexplained) -> Receding

        env_context = [
            {"rainfall_12d_mm": 5.0, "wind_speed_mps": 2.0, "hydraulically_plausible": True},
            {"rainfall_12d_mm": 75.0, "wind_speed_mps": 2.2, "hydraulically_plausible": True},
            {"rainfall_12d_mm": 10.0, "wind_speed_mps": 2.0, "hydraulically_plausible": True},
        ]

        # For cluster 4, override step 2 to zero rain (unexplained)
        c4_env = [
            {"rainfall_12d_mm": 5.0, "wind_speed_mps": 2.0, "hydraulically_plausible": True},
            {"rainfall_12d_mm": 2.0, "wind_speed_mps": 2.0, "hydraulically_plausible": True},
            {"rainfall_12d_mm": 10.0, "wind_speed_mps": 2.0, "hydraulically_plausible": True},
        ]

        r1 = evaluate_four_state_trajectory(c1, environmental_context=env_context)
        r2 = evaluate_four_state_trajectory(c2, environmental_context=env_context)
        r3 = evaluate_four_state_trajectory(c3, environmental_context=env_context)
        r4 = evaluate_four_state_trajectory(c4, environmental_context=c4_env)

        self.assertTrue(r1.is_compliant)
        self.assertEqual(r1.state_timeline[-1], TemporalState.DRAINED)

        self.assertTrue(r2.is_compliant)
        self.assertEqual(r2.state_timeline[-1], TemporalState.DRAINED)

        self.assertTrue(r3.is_compliant)
        self.assertEqual(r3.state_timeline[2], TemporalState.RE_INUNDATED_EXPLAINED)

        self.assertFalse(r4.is_compliant)
        self.assertEqual(r4.state_timeline[2], TemporalState.RE_INUNDATED_UNEXPLAINED)
        self.assertEqual(r4.evidence_status, EvidenceStatus.INCONCLUSIVE)

        # Evaluate aggregate mixed multi-cluster function
        counts, multi_res = evaluate_mixed_spatial_trajectories([c1, c2, c3])
        self.assertEqual(counts["drained"], 2)
        self.assertEqual(counts["receding"], 1)

    # =========================================================================
    # 6. MISSING OBSERVATIONS (NOT INTERPRETED AS DRAINAGE)
    # =========================================================================

    def test_06_missing_observations_not_interpreted_as_drainage(self) -> None:
        """
        Verifies that missing satellite acquisitions (None / NaN) are classified as MISSING
        and NEVER falsely interpreted as 0.0 or DRAINED.
        Subsequent valid steps compare against the last known valid observation.
        """
        # Timeline: 10.0 (t1), 8.0 (s1), MISSING (s2), 4.0 (s3), 0.0 (s4)
        timeline = [10.0, 8.0, None, 4.0, 0.0]
        res = evaluate_four_state_trajectory(timeline)

        self.assertTrue(res.is_compliant)
        self.assertEqual(res.missing_observations_count, 1)
        self.assertEqual(res.valid_observations_count, 3)  # Steps 1, 3, 4 are valid (>= 3!)
        self.assertEqual(res.state_timeline[2], TemporalState.MISSING)
        self.assertNotEqual(res.state_timeline[2], TemporalState.DRAINED)

        # Step 3 evaluates recession against step 1 (4.0 < 8.0)
        self.assertEqual(res.state_timeline[3], TemporalState.RECEDING)
        # Step 4 evaluates drainage
        self.assertEqual(res.state_timeline[4], TemporalState.DRAINED)
        # Since 3 valid steps exist, evidence status is SUPPORTED
        self.assertEqual(res.evidence_status, EvidenceStatus.SUPPORTED)

    # =========================================================================
    # 7. INVALID OBSERVATIONS (EXCLUDED FROM VALID COUNT)
    # =========================================================================

    def test_07_invalid_observations_do_not_count_as_valid(self) -> None:
        """
        Verifies that observations flagged invalid (e.g. geometric failure, RF distortion)
        are classified as INVALID, do not increment valid_observations_count, and are
        NOT interpreted as drainage.
        """
        timeline = [10.0, 8.0, 7.5, 4.0]
        env_context = [
            {"is_valid": True},
            {"is_valid": False, "invalidation_reason": "Missing orbit state vectors / geometric divergence"},
            {"is_valid": True},
        ]
        res = evaluate_four_state_trajectory(timeline, environmental_context=env_context)

        self.assertEqual(res.invalid_observations_count, 1)
        self.assertEqual(res.valid_observations_count, 2)  # Only steps 1 and 3 are valid!
        self.assertEqual(res.state_timeline[2], TemporalState.INVALID)
        self.assertNotEqual(res.state_timeline[2], TemporalState.DRAINED)

        # Hard PRD Gate: valid count = 2 < 3 forces UNVERIFIED!
        self.assertEqual(res.evidence_status, EvidenceStatus.UNVERIFIED)
        self.assertIn("PRD Hard Invariant: Insufficient valid repeat acquisitions (2 < 3)", res.diagnostic_summary)

    # =========================================================================
    # 8. INSUFFICIENT ACQUISITIONS (N < 3 FORCES UNVERIFIED)
    # =========================================================================

    def test_08_insufficient_acquisitions_forces_unverified(self) -> None:
        """
        Verifies the non-negotiable PRD Hard Invariant:
        Fewer than 3 valid subsequent acquisitions strictly results in UNVERIFIED,
        even if the sequence displays 100% compliant recession.
        """
        # Only 2 subsequent observations (N = 2)
        timeline = [10.0, 5.0, 0.0]
        res = evaluate_four_state_trajectory(timeline)

        self.assertTrue(res.is_compliant)
        self.assertEqual(res.valid_observations_count, 2)
        self.assertEqual(res.evidence_status, EvidenceStatus.UNVERIFIED)
        self.assertNotEqual(res.evidence_status, EvidenceStatus.SUPPORTED)
        self.assertIn("Insufficient valid repeat acquisitions (2 < 3)", res.diagnostic_summary)

    # =========================================================================
    # 9. UNEXPLAINED CHANGES YIELD INCONCLUSIVE
    # =========================================================================

    def test_09_unexplained_changes_yield_inconclusive(self) -> None:
        """
        Verifies that an uncorroborated area surge (> 15%) without meteorological
        or tidal forcing evaluates to RE_INUNDATED_UNEXPLAINED, marks the trajectory
        non-compliant, and yields INCONCLUSIVE.
        """
        timeline = [10.0, 4.0, 8.5, 2.0]
        env_context = [
            {"rainfall_12d_mm": 5.0},
            {"rainfall_12d_mm": 2.0, "river_stage_rise_m": 0.05, "wind_speed_mps": 2.0},  # Low rain: Unexplained!
            {"rainfall_12d_mm": 5.0},
        ]
        res = evaluate_four_state_trajectory(timeline, environmental_context=env_context)

        self.assertFalse(res.is_compliant)
        self.assertTrue(res.unexplained_change_detected)
        self.assertEqual(res.state_timeline[2], TemporalState.RE_INUNDATED_UNEXPLAINED)
        self.assertEqual(res.evidence_status, EvidenceStatus.INCONCLUSIVE)
        self.assertIn("UNEXPLAINED_GROWTH", res.diagnostic_reasons[2])

    # =========================================================================
    # 10. ENVIRONMENTAL CONTEXT WITHOUT CAUSAL ATTRIBUTION
    # =========================================================================

    def test_10_environmental_context_without_causal_attribution(self) -> None:
        """
        Verifies that rainfall >= 50mm alone does NOT automatically cause or explain
        a surge if Tier 2 (Hydraulic Plausibility) or Tier 3 (Artifact Check) fails.
        """
        timeline = [10.0, 4.0, 8.5, 2.0]

        # Case 10a: Heavy rainfall (85mm) on an isolated high elevation ridge (Tier 2 fails)
        env_high_ridge = [
            {"rainfall_12d_mm": 5.0},
            {"rainfall_12d_mm": 85.0, "hydraulically_plausible": False},  # Ridge cannot retain delta floodwaters!
            {"rainfall_12d_mm": 5.0},
        ]
        res_ridge = evaluate_four_state_trajectory(timeline, environmental_context=env_high_ridge)
        self.assertFalse(res_ridge.is_compliant)
        self.assertEqual(res_ridge.state_timeline[2], TemporalState.RE_INUNDATED_UNEXPLAINED)
        self.assertTrue(any("Tier 2 Hydraulic Plausibility: False" in r for r in res_ridge.diagnostic_reasons))

        # Case 10b: Heavy rainfall (85mm) under strong surface wind (6.5 m/s, Tier 3 fails)
        env_wind_chop = [
            {"rainfall_12d_mm": 5.0},
            {"rainfall_12d_mm": 85.0, "hydraulically_plausible": True, "wind_speed_mps": 6.5},  # Wind artifact risk!
            {"rainfall_12d_mm": 5.0},
        ]
        res_wind = evaluate_four_state_trajectory(timeline, environmental_context=env_wind_chop)
        self.assertFalse(res_wind.is_compliant)
        self.assertEqual(res_wind.state_timeline[2], TemporalState.RE_INUNDATED_UNEXPLAINED)
        self.assertTrue(any("Tier 3 Artifact Exclusion: False" in r for r in res_wind.diagnostic_reasons))

    # =========================================================================
    # 11. REFERENCE AGREEMENT INDEPENDENT OF EVIDENCE STATUS
    # =========================================================================

    def test_11_reference_agreement_independent_of_evidence_status(self) -> None:
        """
        Verifies that independent reference evidence (e.g. Sentinel-2 optical data on 26-Sep)
        is recorded in provenance but CANNOT independently override SAR temporal failure.
        """
        # Case 11a: SAR has unexplained failure (INCONCLUSIVE). Optical claims agreement (agreed = True).
        # Evidence status must REMAIN INCONCLUSIVE (optical cannot whitewash SAR failure).
        timeline_fail = [10.0, 4.0, 8.5, 2.0]
        env_low_rain = [{"rainfall_12d_mm": 2.0} for _ in range(3)]
        s2_evidence = {
            "source": "Sentinel-2 Tile T43PFL",
            "date": "2018-09-26T05:06:00Z",
            "agreed": True,
            "agreement_score": 0.94,
            "optical_cloud_cover_pct": 0.8,
        }
        res_fail = evaluate_four_state_trajectory(
            timeline_fail,
            environmental_context=env_low_rain,
            reference_evidence=s2_evidence,
        )
        self.assertEqual(res_fail.evidence_status, EvidenceStatus.INCONCLUSIVE)
        self.assertEqual(res_fail.provenance["reference_evidence_agreement"], True)
        self.assertEqual(res_fail.provenance["reference_evidence_source"], "Sentinel-2 Tile T43PFL")

        # Case 11b: SAR has compliant recession (SUPPORTED). Optical data unavailable or missing.
        # Evidence status remains SUPPORTED.
        timeline_ok = [10.0, 7.5, 4.0, 0.0]
        res_ok = evaluate_four_state_trajectory(timeline_ok, reference_evidence=None)
        self.assertEqual(res_ok.evidence_status, EvidenceStatus.SUPPORTED)
        self.assertIsNone(res_ok.provenance.get("reference_evidence"))

    # =========================================================================
    # 12. N < 3 NEVER PRODUCING SUPPORTED
    # =========================================================================

    def test_12_n_less_than_three_never_produces_supported(self) -> None:
        """
        Validates the strict pilot invariant:
        A 3-date, 1-subsequent pilot (N = 1) can NEVER produce SUPPORTED.
        """
        # Minimal Pilot: t1 = 10.0 km², s1 = 4.0 km² (N = 1)
        pilot_timeline = [10.0, 4.0]
        res_pilot = evaluate_four_state_trajectory(pilot_timeline)

        self.assertTrue(res_pilot.is_compliant)
        self.assertEqual(res_pilot.valid_observations_count, 1)
        self.assertEqual(res_pilot.evidence_status, EvidenceStatus.UNVERIFIED)
        self.assertNotEqual(res_pilot.evidence_status, EvidenceStatus.SUPPORTED)

        # N = 2
        pilot_n2 = [10.0, 5.0, 1.0]
        res_n2 = evaluate_four_state_trajectory(pilot_n2)
        self.assertEqual(res_n2.valid_observations_count, 2)
        self.assertEqual(res_n2.evidence_status, EvidenceStatus.UNVERIFIED)
        self.assertNotEqual(res_n2.evidence_status, EvidenceStatus.SUPPORTED)

    # =========================================================================
    # 13. SYNTHETIC PROVENANCE DISCLAIMER
    # =========================================================================

    def test_13_synthetic_provenance_disclaimer(self) -> None:
        """
        Verifies that running with is_synthetic=True records explicit provenance
        disclaimers and prohibits claiming empirical scientific validation.
        """
        timeline = [10.0, 7.0, 4.0, 1.0]
        res = evaluate_four_state_trajectory(timeline, is_synthetic=True)

        prov = res.provenance
        self.assertEqual(prov["data_authenticity_tier"], "TIER 3 - SYNTHETIC FIXTURE")
        self.assertFalse(prov["scientific_validation_claimed"])
        self.assertIn("Synthetic test execution confirms algorithmic correctness only", prov["synthetic_disclaimer"])


if __name__ == "__main__":
    unittest.main()
