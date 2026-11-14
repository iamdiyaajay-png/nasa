"""
BHnMISnTRA: End-to-End Scientific Pipeline Integration Tests.
Phase E & F Full-Stack Scientific Verification.
"""

import json
import unittest
import numpy as np

from src.bhnmisntra_science.config import (
    AcquisitionMetadata,
    BoundingBoxWGS84,
    CalibratedDbCalibration,
    CalibratedDbProvenance,
    ConfounderAssessmentSource,
    ConfounderRecord,
    FixedDbThresholdConfig,
    IncidenceAngleMetadata,
    InvestigationConfig,
    OrbitParameters,
    PipelineParameters,
    SensorMetadata,
)
from src.bhnmisntra_science.enums import (
    CalibrationState,
    ConfounderCriticality,
    ConfounderState,
    EvidenceStatus,
    IncidenceAngleQuality,
    UnavailableAnglePolicy,
)
from src.bhnmisntra_science.pipeline import run_scientific_pipeline
from src.bhnmisntra_science.processing.alignment import AlignmentMetadata


class TestPipelineE2E(unittest.TestCase):
    """End-to-End scientific pipeline integration tests."""

    def setUp(self) -> None:
        np.random.seed(100)
        self.shape = (60, 60)
        self.align_meta = AlignmentMetadata(
            shape=self.shape,
            crs="EPSG:32643",
            transform=(700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0),
            resolution_meters=(10.0, 10.0),
        )

        # Baseline calibration
        self.cal_db = CalibratedDbCalibration(
            calibration_state=CalibrationState.CALIBRATED_DB,
            provenance=CalibratedDbProvenance(
                calibration_source_doc="Copernicus Sentinel-1 Spec",
                decibel_reference_scale="10*log10(sigma0)",
            ),
        )

        self.orbit_common = OrbitParameters(
            orbit_direction="descending",
            pass_type="descending",
            relative_orbit=165,
        )

        self.sensor_common = SensorMetadata(
            mission="SENTINEL-1",
            sensor_name="C-SAR",
            sensor_mode="IW",
            polarization="VV",
            frequency_band="C",
            look_direction="right",
            incidence_angle=IncidenceAngleMetadata(
                quality=IncidenceAngleQuality.AVAILABLE,
                angle_deg=38.5,
            ),
        )

    def _build_test_investigation(
        self,
        confounder_state: ConfounderState = ConfounderState.CLEAR,
        re_inundate: bool = False,
    ) -> tuple[InvestigationConfig, dict[str, tuple[np.ndarray, AlignmentMetadata]]]:
        """Builds a complete, realistic 5-acquisition flood sequence (ref, comp, sub1, sub2, sub3)."""
        ref_meta = AcquisitionMetadata(
            product_id="S1A_IW_GRDH_1SDV_20240701T003000_REF",
            acquisition_utc="2024-07-01T00:30:00Z",
            sensor=self.sensor_common,
            orbit=self.orbit_common,
            calibration=self.cal_db,
            file_path="mock/ref.tif",
        )

        comp_meta = AcquisitionMetadata(
            product_id="S1A_IW_GRDH_1SDV_20240713T003000_COMP",
            acquisition_utc="2024-07-13T00:30:00Z",
            sensor=self.sensor_common,
            orbit=self.orbit_common,
            calibration=self.cal_db,
            file_path="mock/comp.tif",
        )

        sub_dates = [
            "2024-07-25T00:30:00Z",  # Subsequent 1 (receding step 1)
            "2024-08-06T00:30:00Z",  # Subsequent 2 (receding step 2)
            "2024-08-18T00:30:00Z",  # Subsequent 3 (receding step 3 / drained)
        ]

        subs = []
        for i, dt in enumerate(sub_dates, start=1):
            subs.append(
                AcquisitionMetadata(
                    product_id=f"S1A_IW_GRDH_1SDV_202408{i*6:02d}T003000_SUB{i}",
                    acquisition_utc=dt,
                    sensor=self.sensor_common,
                    orbit=self.orbit_common,
                    calibration=self.cal_db,
                    file_path=f"mock/sub{i}.tif",
                )
            )

        confounder = ConfounderRecord(
            confounder_id="CONF-WATER-001",
            name="standing_water_pre_flood",
            criticality=ConfounderCriticality.CRITICAL,
            state=confounder_state,
            description="Pre-existing standing water bodies from historical baseline",
            assessment_source=ConfounderAssessmentSource(
                provider="European Commission JRC",
                dataset_name="Global Surface Water",
                url_or_doi="https://doi.org/10.1038/nature20584",
                window_start_utc="2024-07-01T00:00:00Z",
                window_end_utc="2024-07-02T00:00:00Z",
            ),
            threshold_applied="occurrence > 80%",
        )

        config = InvestigationConfig(
            investigation_id="INV-KERALA-2024-001",
            study_area_id="KERALA-WAYANAD",
            bbox=BoundingBoxWGS84(
                min_lon=76.0,
                min_lat=9.5,
                max_lon=76.5,
                max_lat=10.0,
                crosses_antimeridian=False,
            ),
            phenomenon_type="flood",
            expected_behavior="receding",
            reference_acquisition=ref_meta,
            comparison_acquisition=comp_meta,
            subsequent_acquisitions=tuple(subs),
            parameters=PipelineParameters(
                speckle_filter_name="boxcar",
                speckle_window_size=3,
                threshold_strategy=FixedDbThresholdConfig(drop_threshold_db=-3.5),
                min_mapping_unit_pixels=10,
                flood_growth_tolerance=0.05,
                sustained_overlap_ratio=0.5,
                min_spatial_coverage_ratio=0.8,
                min_valid_pixel_ratio=0.8,
                spatial_tuning_split_ratio=0.5,
                max_incidence_angle_divergence_deg=2.0,
                unavailable_incidence_angle_policy=UnavailableAnglePolicy.FAIL_VALIDATION,
            ),
            output_dir="outputs/kerala",
            confounders=(confounder,),
        )

        # Build rasters
        ref_arr = np.full(self.shape, -10.0, dtype=np.float32)

        # Comp: Peak flood event (6x6 = 36 pixels inundation, -8 dB drop)
        comp_arr = np.full(self.shape, -10.0, dtype=np.float32)
        comp_arr[20:26, 20:26] = -18.0

        # Sub 1: Receding step 1 (4x4 = 16 pixels inundation)
        sub1_arr = np.full(self.shape, -10.0, dtype=np.float32)
        sub1_arr[20:24, 20:24] = -18.0

        # Sub 2: Receding step 2 (2x2 = 4 pixels inundation)
        sub2_arr = np.full(self.shape, -10.0, dtype=np.float32)
        sub2_arr[20:22, 20:22] = -18.0

        # Sub 3: Drainage or re-inundation
        sub3_arr = np.full(self.shape, -10.0, dtype=np.float32)
        if re_inundate:
            # Re-inundate with 7x7 = 49 pixels surge!
            sub3_arr[20:27, 20:27] = -18.0
        else:
            # Drained completely (0 pixels)
            pass

        rasters = {
            ref_meta.product_id: (ref_arr, self.align_meta),
            comp_meta.product_id: (comp_arr, self.align_meta),
            subs[0].product_id: (sub1_arr, self.align_meta),
            subs[1].product_id: (sub2_arr, self.align_meta),
            subs[2].product_id: (sub3_arr, self.align_meta),
        }

        return config, rasters

    def test_full_pipeline_success_supported(self) -> None:
        """Full pipeline with valid geometry, receding flood, and clear confounders yields SUPPORTED."""
        config, rasters = self._build_test_investigation(
            confounder_state=ConfounderState.CLEAR,
            re_inundate=False,
        )

        result = run_scientific_pipeline(config, rasters)

        self.assertEqual(result.evidence_status, EvidenceStatus.SUPPORTED)
        self.assertTrue(result.spatial_alignment_verified)
        self.assertTrue(result.beat_test_summary.overall_beat_test_passed)
        self.assertEqual(result.beat_test_summary.compliant_regions, 1)
        self.assertEqual(result.beat_test_summary.failed_regions, 0)
        self.assertGreaterEqual(result.baseline_change_stats["sieved_change_pixels"], 25)

        # Inspect Evidence Ledger
        ledger = result.evidence_ledger
        self.assertEqual(ledger["evidence_label"], "supported")
        self.assertEqual(ledger["audit_checks"]["beat_test_passed"], True)
        self.assertEqual(ledger["audit_checks"]["has_geometry_uncertainty"], False)

        # Verify JSON serializability of Evidence Ledger
        serialized_json = json.dumps(ledger, indent=2)
        self.assertIn('"evidence_label": "supported"', serialized_json)

    def test_full_pipeline_re_inundation_failure_yields_inconclusive(self) -> None:
        """Re-inundation surge violates Beat Test recession profile, yielding INCONCLUSIVE."""
        config, rasters = self._build_test_investigation(
            confounder_state=ConfounderState.CLEAR,
            re_inundate=True,  # Triggers re-inundation surge
        )

        result = run_scientific_pipeline(config, rasters)

        self.assertEqual(result.evidence_status, EvidenceStatus.INCONCLUSIVE)
        self.assertFalse(result.beat_test_summary.overall_beat_test_passed)
        self.assertEqual(result.beat_test_summary.failed_regions, 1)
        self.assertEqual(result.evidence_ledger["evidence_label"], "inconclusive")

    def test_full_pipeline_critical_confounder_flagged_yields_inconclusive(self) -> None:
        """Critical confounder FLAGGED forces evidence label to INCONCLUSIVE."""
        config, rasters = self._build_test_investigation(
            confounder_state=ConfounderState.FLAGGED,
            re_inundate=False,
        )

        result = run_scientific_pipeline(config, rasters)

        self.assertEqual(result.evidence_status, EvidenceStatus.INCONCLUSIVE)
        self.assertTrue(result.beat_test_summary.overall_beat_test_passed)
        self.assertIn("CRITICAL FLAGGED", result.classification_reasons[0])


if __name__ == "__main__":
    unittest.main()
