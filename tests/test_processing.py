"""
BHnMISnTRA: Processing Pipeline & Scientific Verification Tests.
Phase E Acceptance Tests.
"""

import math
import unittest
import numpy as np

from src.bhnmisntra_science.enums import (
    CalibrationState,
    EvidenceStatus,
    ExpectedBehavior,
    PhenomenonType,
)
from src.bhnmisntra_science.exceptions import (
    ProcessingError,
    RasterAlignmentError,
)
from src.bhnmisntra_science.config import (
    CalibratedDbCalibration,
    CalibratedDbProvenance,
    CalibratedLinearCalibration,
    CalibratedLinearProvenance,
    FixedDbThresholdConfig,
    OtsuThresholdConfig,
    RawDnCalibration,
    RawDnProvenance,
    RobustMadThresholdConfig,
)
from src.bhnmisntra_science.policies import classify_final_evidence
from src.bhnmisntra_science.processing.alignment import AlignmentMetadata, validate_raster_alignment
from src.bhnmisntra_science.processing.calibration import (
    CalibrationStateConflictError,
    calibrate_sar_array,
)
from src.bhnmisntra_science.processing.log_ratio import (
    compute_log_ratio,
    compute_threshold,
    create_spatial_tuning_mask,
    generate_change_mask,
)
from src.bhnmisntra_science.processing.speckle import apply_speckle_filter
from src.bhnmisntra_science.beat_test.tracker import track_change_regions


class TestScientificProcessingPipeline(unittest.TestCase):
    """Rigorous scientific verification of Member 1 processing pipeline."""

    def setUp(self) -> None:
        np.random.seed(42)

    # =========================================================================
    # A. CALIBRATION TESTS & DOUBLE-CALIBRATION PREVENTION
    # =========================================================================

    def test_calibration_raw_dn_to_db(self) -> None:
        """Verifies RAW_DN conversion to calibrated dB: 10 * log10(DN^2)."""
        raw_cal = RawDnCalibration(
            calibration_state=CalibrationState.RAW_DN,
            provenance=RawDnProvenance(
                calibration_source_doc="Sentinel-1 Radiometric Calibration Technical Note",
                lut_or_aux_file="s1a-aux-cal.xml",
                applied_scale="dn_squared",
            ),
        )
        # 100.0^2 = 10000.0 -> 10 * log10(10000) = 40.0 dB
        # 10.0^2 = 100.0 -> 10 * log10(100) = 20.0 dB
        arr = np.array([[100.0, 10.0], [10.0, 100.0]], dtype=np.float32)
        calibrated_db, prov = calibrate_sar_array(arr, raw_cal)

        self.assertAlmostEqual(calibrated_db[0, 0], 40.0, places=3)
        self.assertAlmostEqual(calibrated_db[0, 1], 20.0, places=3)
        self.assertEqual(prov["calibration_state"], "raw_dn")
        self.assertIn("DN^2", prov["applied_equation"])

    def test_calibration_linear_power_to_db(self) -> None:
        """Verifies CALIBRATED_LINEAR_POWER conversion to dB with scale factor."""
        linear_cal = CalibratedLinearCalibration(
            calibration_state=CalibrationState.CALIBRATED_LINEAR_POWER,
            provenance=CalibratedLinearProvenance(
                calibration_source_doc="ASF Radiometric Terrain Correction Guide",
                calibration_factor=1.0,
                declared_linear_scale="sigma0",
            ),
        )
        # Linear power 0.01 -> 10 * log10(0.01) = -20.0 dB
        # Linear power 0.1 -> 10 * log10(0.1) = -10.0 dB
        arr = np.array([[0.01, 0.1], [0.1, 0.01]], dtype=np.float32)
        calibrated_db, prov = calibrate_sar_array(arr, linear_cal)

        self.assertAlmostEqual(calibrated_db[0, 0], -20.0, places=3)
        self.assertAlmostEqual(calibrated_db[0, 1], -10.0, places=3)
        self.assertEqual(prov["calibration_state"], "calibrated_linear_power")

    def test_calibration_calibrated_db_pass_through(self) -> None:
        """Verifies CALIBRATED_DB is passed through without double logarithm."""
        db_cal = CalibratedDbCalibration(
            calibration_state=CalibrationState.CALIBRATED_DB,
            provenance=CalibratedDbProvenance(
                calibration_source_doc="Copernicus Sentinel-1 GRD Product Specification",
                decibel_reference_scale="10*log10(sigma0)",
            ),
        )
        arr = np.array([[-15.5, -12.3], [-18.0, -9.1]], dtype=np.float32)
        calibrated_db, prov = calibrate_sar_array(arr, db_cal)

        np.testing.assert_allclose(calibrated_db, arr)
        self.assertEqual(prov["calibration_state"], "calibrated_db")
        self.assertIn("pass_through", prov["applied_equation"])

    def test_double_calibration_prevention_linear_power_with_negatives(self) -> None:
        """Rejects CALIBRATED_LINEAR_POWER if data contains negative values (already dB)."""
        linear_cal = CalibratedLinearCalibration(
            calibration_state=CalibrationState.CALIBRATED_LINEAR_POWER,
            provenance=CalibratedLinearProvenance(
                calibration_source_doc="ASF Documentation",
                calibration_factor=1.0,
                declared_linear_scale="sigma0",
            ),
        )
        # An array with negative values cannot be physical linear power (sigma0 >= 0)
        arr = np.array([[-12.0, -15.0], [-10.0, -14.0]], dtype=np.float32)
        with self.assertRaises(CalibrationStateConflictError):
            calibrate_sar_array(arr, linear_cal)

    def test_double_calibration_prevention_db_with_raw_dn_values(self) -> None:
        """Rejects CALIBRATED_DB if data contains excessively high DN values (> 50 dB mean)."""
        db_cal = CalibratedDbCalibration(
            calibration_state=CalibrationState.CALIBRATED_DB,
            provenance=CalibratedDbProvenance(
                calibration_source_doc="Copernicus Spec",
                decibel_reference_scale="10*log10(sigma0)",
            ),
        )
        # Raw DN amplitudes typically 200 - 2000
        arr = np.full((10, 10), 500.0, dtype=np.float32)
        with self.assertRaises(CalibrationStateConflictError):
            calibrate_sar_array(arr, db_cal)

    def test_calibration_preserves_nodata_mask(self) -> None:
        """Nodata pixels must remain NaN and not corrupt valid pixel statistics."""
        db_cal = CalibratedDbCalibration(
            calibration_state=CalibrationState.CALIBRATED_DB,
            provenance=CalibratedDbProvenance(
                calibration_source_doc="Copernicus Spec",
                decibel_reference_scale="10*log10(sigma0)",
            ),
        )
        arr = np.array([[-10.0, -12.0], [-14.0, 9999.0]], dtype=np.float32)
        mask = np.array([[False, False], [False, True]])
        calibrated_db, prov = calibrate_sar_array(arr, db_cal, nodata_mask=mask)

        self.assertTrue(np.isnan(calibrated_db[1, 1]))
        self.assertAlmostEqual(prov["output_stats_db"]["mean"], -12.0, places=2)

    # =========================================================================
    # B. ALIGNMENT & CO-REGISTRATION TESTS
    # =========================================================================

    def test_raster_alignment_matching_succeeds(self) -> None:
        """Identical grids and CRS pass alignment verification."""
        meta1 = AlignmentMetadata(
            shape=(512, 512),
            crs="EPSG:32643",
            transform=(700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0),
            resolution_meters=(10.0, 10.0),
        )
        meta2 = AlignmentMetadata(
            shape=(512, 512),
            crs="EPSG:32643",
            transform=(700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0),
            resolution_meters=(10.0, 10.0),
        )
        self.assertTrue(validate_raster_alignment([meta1, meta2]))

    def test_raster_alignment_shape_mismatch_raises(self) -> None:
        """Different grid dimensions raise RasterAlignmentError."""
        meta1 = AlignmentMetadata(
            shape=(512, 512),
            crs="EPSG:32643",
            transform=(700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0),
            resolution_meters=(10.0, 10.0),
        )
        meta2 = AlignmentMetadata(
            shape=(512, 514),  # Mismatch
            crs="EPSG:32643",
            transform=(700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0),
            resolution_meters=(10.0, 10.0),
        )
        with self.assertRaises(RasterAlignmentError):
            validate_raster_alignment([meta1, meta2])

    def test_raster_alignment_crs_mismatch_raises(self) -> None:
        """Different CRS raises RasterAlignmentError."""
        meta1 = AlignmentMetadata(
            shape=(512, 512),
            crs="EPSG:32643",
            transform=(700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0),
            resolution_meters=(10.0, 10.0),
        )
        meta2 = AlignmentMetadata(
            shape=(512, 512),
            crs="EPSG:4326",  # Mismatch
            transform=(700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0),
            resolution_meters=(10.0, 10.0),
        )
        with self.assertRaises(RasterAlignmentError):
            validate_raster_alignment([meta1, meta2])

    def test_raster_alignment_geotransform_offset_raises(self) -> None:
        """Transform shift > tolerance raises RasterAlignmentError."""
        meta1 = AlignmentMetadata(
            shape=(512, 512),
            crs="EPSG:32643",
            transform=(700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0),
            resolution_meters=(10.0, 10.0),
        )
        meta2 = AlignmentMetadata(
            shape=(512, 512),
            crs="EPSG:32643",
            transform=(700005.0, 10.0, 0.0, 1100000.0, 0.0, -10.0),  # 5m shift
            resolution_meters=(10.0, 10.0),
        )
        with self.assertRaises(RasterAlignmentError):
            validate_raster_alignment([meta1, meta2], transform_tolerance=1e-3)

    # =========================================================================
    # C. SPECKLE FILTERING & LOGARITHMIC BIAS PREVENTION
    # =========================================================================

    def test_speckle_filter_window_size_invariants(self) -> None:
        """Speckle filter rejects even window sizes and sizes < 3."""
        arr = np.full((20, 20), -12.0, dtype=np.float32)
        with self.assertRaises(ProcessingError):
            apply_speckle_filter(arr, filter_name="boxcar", window_size=4)  # Even
        with self.assertRaises(ProcessingError):
            apply_speckle_filter(arr, filter_name="boxcar", window_size=1)  # < 3
        with self.assertRaises(ProcessingError):
            apply_speckle_filter(arr, filter_name="boxcar", window_size="3")  # Not int

    def test_speckle_filter_logarithmic_bias_prevention(self) -> None:
        """
        Demonstrates that filtering in linear space avoids the downward logarithmic bias.
        For two values with high variance in dB (-20 dB and 0 dB):
        Linear average: (0.01 + 1.0) / 2 = 0.505 -> 10*log10(0.505) = -2.967 dB
        dB average: (-20 + 0) / 2 = -10.0 dB (severe 7 dB downward bias!)
        The filter must produce the linear average ~ -2.97 dB, NOT -10 dB!
        """
        arr = np.array([
            [-20.0, 0.0, -20.0],
            [0.0, -20.0, 0.0],
            [-20.0, 0.0, -20.0],
        ], dtype=np.float32)

        # Center pixel has 4 zeros (linear 1.0) and 5 -20s (linear 0.01)
        # Sum = 4 * 1.0 + 5 * 0.01 = 4.05
        # Mean = 4.05 / 9 = 0.45
        # dB = 10 * log10(0.45) = -3.468 dB
        filtered = apply_speckle_filter(arr, filter_name="boxcar", window_size=3, is_db=True)
        center_val = filtered[1, 1]

        self.assertAlmostEqual(center_val, -3.468, places=2)
        # Ensure it did NOT calculate arithmetic mean in dB (-20*5 + 0*4)/9 = -11.11 dB
        self.assertNotAlmostEqual(center_val, -11.11, places=0)

    def test_speckle_lee_filter_execution(self) -> None:
        """Lee filter executes and preserves homogeneous areas."""
        arr = np.full((30, 30), -15.0, dtype=np.float32)
        filtered = apply_speckle_filter(arr, filter_name="lee", window_size=5, is_db=True)
        np.testing.assert_allclose(filtered, arr, atol=1e-3)

    # =========================================================================
    # D. LOG-RATIO & THRESHOLDING TESTS
    # =========================================================================

    def test_log_ratio_exactness(self) -> None:
        """compute_log_ratio returns exact Delta sigma0 in dB."""
        comp = np.array([[-18.0, -12.0], [-10.0, -6.0]], dtype=np.float32)
        ref = np.array([[-12.0, -12.0], [-8.0, -12.0]], dtype=np.float32)

        diff = compute_log_ratio(comp, ref)
        expected = np.array([[-6.0, 0.0], [-2.0, 6.0]], dtype=np.float32)
        np.testing.assert_allclose(diff, expected, atol=1e-5)

    def test_spatial_tuning_mask_disjoint(self) -> None:
        """Spatial tuning and evaluation masks are strictly disjoint."""
        shape = (100, 100)
        t_mask, e_mask = create_spatial_tuning_mask(shape, split_ratio=0.5, axis=1)

        self.assertEqual(t_mask.shape, shape)
        self.assertEqual(e_mask.shape, shape)
        self.assertFalse(np.any(t_mask & e_mask))
        self.assertTrue(np.all(t_mask | e_mask))
        self.assertEqual(int(np.sum(t_mask)), 5000)
        self.assertEqual(int(np.sum(e_mask)), 5000)

    def test_compute_threshold_fixed_db(self) -> None:
        """Fixed dB threshold strategy returns registered constant."""
        cfg = FixedDbThresholdConfig(drop_threshold_db=-3.5)
        diff = np.zeros((20, 20), dtype=np.float32)
        t_val = compute_threshold(diff, cfg)
        self.assertEqual(t_val, -3.5)

    def test_compute_threshold_robust_mad(self) -> None:
        """Robust MAD uses median and normal-scaled 1.4826 MAD."""
        # Baseline difference normal distribution around 0 dB with std 1.0 dB
        # + Water cluster with -8 dB drop
        np.random.seed(123)
        diff = np.random.normal(loc=0.0, scale=1.0, size=(100, 100)).astype(np.float32)
        diff[10:30, 10:30] = -8.0  # Inundation cluster

        cfg = RobustMadThresholdConfig(k_multiplier=2.5)
        t_val = compute_threshold(diff, cfg, phenomenon=PhenomenonType.FLOOD)

        # For median ~ 0.0 and MAD ~ 1.0, normal_mad ~ 1.4826, threshold ~ -3.7 dB
        self.assertTrue(t_val < -2.0)
        self.assertTrue(t_val > -6.0)

    def test_compute_threshold_otsu(self) -> None:
        """Otsu threshold identifies bimodal separation between water and land."""
        # Bimodal distribution: Land mode around 0 dB, Water mode around -10 dB
        np.random.seed(42)
        diff = np.zeros((100, 100), dtype=np.float32)
        diff[:50, :] = np.random.normal(-10.0, 1.0, (50, 100))  # Water mode
        diff[50:, :] = np.random.normal(0.0, 1.0, (50, 100))   # Land mode

        cfg = OtsuThresholdConfig(num_histogram_bins=128, clip_percentiles=(1.0, 99.0))
        t_val = compute_threshold(diff, cfg)

        # Otsu threshold must lie neatly between the two peaks (-10 and 0) -> roughly -5 dB
        self.assertTrue(-7.0 <= t_val <= -3.0)

    def test_generate_change_mask_and_sieving(self) -> None:
        """Morphological sieving eliminates isolated noise pixels below MMU."""
        diff = np.zeros((50, 50), dtype=np.float32)
        # 1. Single isolated noise pixels (< MMU)
        diff[5, 5] = -8.0
        diff[10, 10] = -8.0
        diff[20, 25] = -8.0

        # 2. Real contiguous flood cluster (16 pixels >= MMU 10)
        diff[30:34, 30:34] = -8.0

        mask, summary = generate_change_mask(
            diff_db=diff,
            threshold_db=-3.0,
            min_mapping_unit_pixels=10,
            phenomenon=PhenomenonType.FLOOD,
            pixel_area_km2=0.0001,
        )

        # Raw candidates = 3 + 16 = 19
        self.assertEqual(summary["raw_candidate_pixels"], 19)
        # Sieved change pixels = 16 (the 3 isolated noise pixels were sieved out)
        self.assertEqual(summary["sieved_change_pixels"], 16)
        self.assertEqual(summary["filtered_noise_pixels"], 3)
        self.assertEqual(summary["surviving_cluster_count"], 1)

        # Verify mask spatial contents
        self.assertFalse(mask[5, 5])
        self.assertFalse(mask[10, 10])
        self.assertTrue(mask[32, 32])

    # =========================================================================
    # E. BEAT TEST TRACKER & MULTI-TEMPORAL RE-INUNDATION TESTS
    # =========================================================================

    def test_beat_test_tracker_receding_flood_compliant(self) -> None:
        """Monotonically shrinking flood cluster passes Beat Test."""
        shape = (40, 40)
        ref_db = np.full(shape, -10.0, dtype=np.float32)

        # Baseline detection: 16-pixel cluster (4x4)
        baseline_mask = np.zeros(shape, dtype=bool)
        baseline_mask[10:14, 10:14] = True

        # Subsequent 1: 9-pixel cluster (3x3)
        sub1_db = np.full(shape, -10.0, dtype=np.float32)
        sub1_db[10:13, 10:13] = -18.0  # -8 dB drop

        # Subsequent 2: 4-pixel cluster (2x2)
        sub2_db = np.full(shape, -10.0, dtype=np.float32)
        sub2_db[10:12, 10:12] = -18.0

        # Subsequent 3: 0-pixel cluster (fully drained)
        sub3_db = np.full(shape, -10.0, dtype=np.float32)

        summary = track_change_regions(
            baseline_change_mask=baseline_mask,
            reference_raster_db=ref_db,
            subsequent_rasters_db=[sub1_db, sub2_db, sub3_db],
            threshold_db=-4.0,
            pixel_area_km2=0.01,
            phenomenon=PhenomenonType.FLOOD,
            expected_behavior=ExpectedBehavior.RECEDING,
            min_region_pixels=10,
        )

        self.assertEqual(summary.total_regions_tracked, 1)
        self.assertEqual(summary.compliant_regions, 1)
        self.assertEqual(summary.failed_regions, 0)
        self.assertTrue(summary.overall_beat_test_passed)

        r = summary.region_results[0]
        self.assertTrue(r.is_compliant)
        self.assertEqual(r.pixel_timeline, (16, 9, 4, 0))

    def test_beat_test_tracker_re_inundation_failure(self) -> None:
        """Unexplained growth (re-inundation) after drainage fails Beat Test."""
        shape = (40, 40)
        ref_db = np.full(shape, -10.0, dtype=np.float32)

        # Baseline detection: 16-pixel cluster
        baseline_mask = np.zeros(shape, dtype=bool)
        baseline_mask[10:14, 10:14] = True

        # Subsequent 1: 9 pixels (drained)
        sub1_db = np.full(shape, -10.0, dtype=np.float32)
        sub1_db[10:13, 10:13] = -18.0

        # Subsequent 2: 0 pixels (fully drained)
        sub2_db = np.full(shape, -10.0, dtype=np.float32)

        # Subsequent 3: 12 pixels (unexplained surge / re-inundation!)
        sub3_db = np.full(shape, -10.0, dtype=np.float32)
        sub3_db[10:14, 10:13] = -18.0

        summary = track_change_regions(
            baseline_change_mask=baseline_mask,
            reference_raster_db=ref_db,
            subsequent_rasters_db=[sub1_db, sub2_db, sub3_db],
            threshold_db=-4.0,
            pixel_area_km2=0.01,
            phenomenon=PhenomenonType.FLOOD,
            expected_behavior=ExpectedBehavior.RECEDING,
            min_region_pixels=10,
        )

        self.assertEqual(summary.total_regions_tracked, 1)
        self.assertEqual(summary.compliant_regions, 0)
        self.assertEqual(summary.failed_regions, 1)
        self.assertFalse(summary.overall_beat_test_passed)

        r = summary.region_results[0]
        self.assertFalse(r.is_compliant)
        self.assertIn("UNEXPLAINED_GROWTH", r.diagnostic_details)

    def test_beat_test_tracker_sustained_change_evaluation(self) -> None:
        """Sustained change requires >= 2/3 re-detections."""
        shape = (30, 30)
        ref_db = np.full(shape, -10.0, dtype=np.float32)

        baseline_mask = np.zeros(shape, dtype=bool)
        baseline_mask[5:10, 5:10] = True  # 25 pixels

        # 3 subsequent rasters: 2 re-detections, 1 non-detection -> 2/3 passes
        sub1_db = np.full(shape, -10.0, dtype=np.float32)
        sub1_db[5:10, 5:10] = -18.0  # re-detection 1

        sub2_db = np.full(shape, -10.0, dtype=np.float32)
        sub2_db[5:10, 5:10] = -18.0  # re-detection 2

        sub3_db = np.full(shape, -10.0, dtype=np.float32)  # non-detection

        summary = track_change_regions(
            baseline_change_mask=baseline_mask,
            reference_raster_db=ref_db,
            subsequent_rasters_db=[sub1_db, sub2_db, sub3_db],
            threshold_db=-4.0,
            pixel_area_km2=0.01,
            phenomenon=PhenomenonType.CLEARING,
            expected_behavior=ExpectedBehavior.SUSTAINED,
            min_region_pixels=10,
        )

        self.assertTrue(summary.overall_beat_test_passed)
        self.assertTrue(summary.region_results[0].is_compliant)


if __name__ == "__main__":
    unittest.main()
