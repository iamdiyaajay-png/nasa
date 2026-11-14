"""
BHnMISnTRA: Phase 2.3 Focused Pipeline Integration Tests.
Verifies end-to-end integration of Direct Abutting Slice Assembly and
Four-State Temporal Beat Test Tracker inside pipeline.py.
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
    TemporalState,
    UnavailableAnglePolicy,
)
from src.bhnmisntra_science.exceptions import (
    MissingSliceError,
    ProcessingError,
    RasterAlignmentError,
)
from src.bhnmisntra_science.pipeline import PipelineExecutionResult, run_scientific_pipeline
from src.bhnmisntra_science.processing.alignment import AlignmentMetadata
from src.bhnmisntra_science.processing.mosaicking import SliceInput, SlicePair


class TestPipelineIntegration(unittest.TestCase):
    """
    Focused integration tests for Phase 2.3:
      - Compatible slice assembly integration
      - Missing slice failure handling (no silent failure)
      - Invalid slice geometry handling
      - Incomplete / missing subsequent observations (hard PRD gate N >= 3)
      - Tracker failure on unexplained growth
      - Three-tier corroboration of flood surge
      - Structured results and evidence ledger completeness
    """

    def setUp(self) -> None:
        np.random.seed(42)
        self.crs_utm43n = "EPSG:32643"
        self.res_10m = (10.0, 10.0)

        # North slice: 20 rows x 50 cols (Top: 1100000.0 -> Bottom: 1099800.0)
        self.north_shape = (20, 50)
        self.north_transform = (700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0)
        self.north_meta = AlignmentMetadata(
            shape=self.north_shape,
            crs=self.crs_utm43n,
            transform=self.north_transform,
            resolution_meters=self.res_10m,
        )

        # South slice: 30 rows x 50 cols (Top: 1099800.0 -> Bottom: 1099500.0)
        self.south_shape = (30, 50)
        self.south_transform = (700000.0, 10.0, 0.0, 1099800.0, 0.0, -10.0)
        self.south_meta = AlignmentMetadata(
            shape=self.south_shape,
            crs=self.crs_utm43n,
            transform=self.south_transform,
            resolution_meters=self.res_10m,
        )

        # Master assembled grid: 50 rows x 50 cols
        self.master_shape = (50, 50)
        self.master_transform = (700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0)
        self.master_meta = AlignmentMetadata(
            shape=self.master_shape,
            crs=self.crs_utm43n,
            transform=self.master_transform,
            resolution_meters=self.res_10m,
        )

        # Common metadata
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

    def _create_slice_pair(self, val_north: float = -10.0, val_south: float = -10.0, flood_box: tuple[int, int, int, int] | None = None) -> SlicePair:
        """Helper to create a SlicePair. If flood_box (r0, r1, c0, c1) on master grid is set, fills -18.0 dB."""
        n_arr = np.full(self.north_shape, val_north, dtype=np.float32)
        s_arr = np.full(self.south_shape, val_south, dtype=np.float32)

        if flood_box is not None:
            r0, r1, c0, c1 = flood_box
            # North covers master rows [0:20]
            if r0 < 20:
                n_arr[r0:min(r1, 20), c0:c1] = -18.0
            # South covers master rows [20:50] (offset by 20)
            if r1 > 20:
                s_r0 = max(0, r0 - 20)
                s_r1 = r1 - 20
                s_arr[s_r0:s_r1, c0:c1] = -18.0

        return SlicePair(
            slice_north=SliceInput(data=n_arr, metadata=self.north_meta, slice_id="SLICE_N"),
            slice_south=SliceInput(data=s_arr, metadata=self.south_meta, slice_id="SLICE_S"),
        )

    def _build_investigation_config(self) -> InvestigationConfig:
        ref_meta = AcquisitionMetadata(
            product_id="S1A_20180728_REF",
            acquisition_utc="2018-07-28T00:30:00Z",
            sensor=self.sensor_common,
            orbit=self.orbit_common,
            calibration=self.cal_db,
            file_path="mock/ref.tif",
        )
        comp_meta = AcquisitionMetadata(
            product_id="S1A_20180821_COMP",
            acquisition_utc="2018-08-21T00:30:00Z",
            sensor=self.sensor_common,
            orbit=self.orbit_common,
            calibration=self.cal_db,
            file_path="mock/comp.tif",
        )
        sub_dates = [
            ("S1A_20180902_SUB1", "2018-09-02T00:30:00Z"),
            ("S1A_20180914_SUB2", "2018-09-14T00:30:00Z"),
            ("S1A_20180926_SUB3", "2018-09-26T00:30:00Z"),
        ]
        subs = [
            AcquisitionMetadata(
                product_id=pid,
                acquisition_utc=dt,
                sensor=self.sensor_common,
                orbit=self.orbit_common,
                calibration=self.cal_db,
                file_path=f"mock/{pid}.tif",
            )
            for pid, dt in sub_dates
        ]
        confounder = ConfounderRecord(
            confounder_id="CONF-WATER-001",
            name="standing_water_pre_flood",
            criticality=ConfounderCriticality.CRITICAL,
            state=ConfounderState.CLEAR,
            description="Pre-existing standing water bodies from historical baseline",
            assessment_source=ConfounderAssessmentSource(
                provider="European Commission JRC",
                dataset_name="Global Surface Water",
                url_or_doi="https://doi.org/10.1038/nature20584",
                window_start_utc="2018-07-01T00:00:00Z",
                window_end_utc="2018-07-02T00:00:00Z",
            ),
            threshold_applied="occurrence > 80%",
        )
        return InvestigationConfig(
            investigation_id="INV-KUTTANAD-2018-P23",
            study_area_id="KUTTANAD-DELTA",
            bbox=BoundingBoxWGS84(min_lon=76.33, min_lat=9.25, max_lon=76.55, max_lat=9.55, crosses_antimeridian=False),
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
                flood_growth_tolerance=0.15,
                sustained_overlap_ratio=0.5,
                min_spatial_coverage_ratio=0.8,
                min_valid_pixel_ratio=0.8,
                spatial_tuning_split_ratio=0.5,
                max_incidence_angle_divergence_deg=2.0,
                unavailable_incidence_angle_policy=UnavailableAnglePolicy.FAIL_VALIDATION,
            ),
            output_dir="outputs/kuttanad",
            confounders=(confounder,),
        )

    # =========================================================================
    # TEST 1: SLICE ASSEMBLY INTEGRATION
    # =========================================================================

    def test_pipeline_slice_assembly_integration(self) -> None:
        """
        Verifies that passing SlicePair objects to run_scientific_pipeline()
        successfully executes direct abutting slice assembly, tracks flood recession,
        records assembly provenance, and produces SUPPORTED.
        """
        config = self._build_investigation_config()

        # Build sequence using SlicePairs (straddling the seam at row 20)
        # Ref: dry (-10 dB)
        ref_pair = self._create_slice_pair()
        # Comp: Flood cluster rows 15-25 (straddles North [15:20] and South [20:25]!)
        comp_pair = self._create_slice_pair(flood_box=(15, 25, 10, 20))  # 10x10 = 100 pixels
        # Sub 1: Receding rows 16-24 (8x8 = 64 pixels)
        sub1_pair = self._create_slice_pair(flood_box=(16, 24, 11, 19))
        # Sub 2: Receding rows 18-22 (4x4 = 16 pixels)
        sub2_pair = self._create_slice_pair(flood_box=(18, 22, 13, 17))
        # Sub 3: Drained (0 pixels)
        sub3_pair = self._create_slice_pair()

        slice_data = {
            config.reference_acquisition.product_id: ref_pair,
            config.comparison_acquisition.product_id: comp_pair,
            config.subsequent_acquisitions[0].product_id: sub1_pair,
            config.subsequent_acquisitions[1].product_id: sub2_pair,
            config.subsequent_acquisitions[2].product_id: sub3_pair,
        }

        result = run_scientific_pipeline(config=config, slice_data=slice_data)

        self.assertIsInstance(result, PipelineExecutionResult)
        self.assertEqual(result.evidence_status, EvidenceStatus.SUPPORTED)
        self.assertTrue(result.spatial_alignment_verified)
        self.assertTrue(result.beat_test_summary.overall_beat_test_passed)
        self.assertEqual(result.beat_test_summary.compliant_regions, 1)

        # Verify slice assembly provenance was recorded for all 5 acquisitions
        self.assertEqual(len(result.slice_assembly_provenance), 5)
        for pid in result.slice_assembly_provenance:
            prov = result.slice_assembly_provenance[pid]
            self.assertEqual(prov["assembly_method"], "DIRECT_ABUTTING_ASSEMBLY")
            self.assertEqual(prov["crs"], self.crs_utm43n)
            self.assertEqual(prov["master_shape"], [50, 50])

        # Check structured results
        self.assertEqual(result.coverage_metrics["slices_assembled_count"], 5)
        self.assertEqual(result.coverage_metrics["subsequent_acquisitions_valid"], 3)
        self.assertEqual(result.structured_summary["beat_test_passed"], True)

    # =========================================================================
    # TEST 2: MISSING SLICE ERROR (NO SILENT FAILURE)
    # =========================================================================

    def test_pipeline_missing_slice_failure_raises(self) -> None:
        """
        Verifies that when allow_partial_slices=False and a required slice is None,
        MissingSliceError is raised without being silently swallowed.
        """
        config = self._build_investigation_config()

        # North slice is None!
        broken_pair = SlicePair(
            slice_north=None,
            slice_south=SliceInput(data=np.full(self.south_shape, -10.0, dtype=np.float32), metadata=self.south_meta),
            allow_partial=False,
        )

        slice_data = {
            config.reference_acquisition.product_id: broken_pair,
            config.comparison_acquisition.product_id: self._create_slice_pair(),
            config.subsequent_acquisitions[0].product_id: self._create_slice_pair(),
            config.subsequent_acquisitions[1].product_id: self._create_slice_pair(),
            config.subsequent_acquisitions[2].product_id: self._create_slice_pair(),
        }

        with self.assertRaises(MissingSliceError):
            run_scientific_pipeline(config=config, slice_data=slice_data, allow_partial_slices=False)

    # =========================================================================
    # TEST 3: INVALID SLICE GEOMETRY (RASTER ALIGNMENT ERROR)
    # =========================================================================

    def test_pipeline_slice_geometry_mismatch_raises(self) -> None:
        """
        Verifies that if slices have incompatible CRS (e.g. EPSG:4326 vs EPSG:32643),
        RasterAlignmentError is raised cleanly.
        """
        config = self._build_investigation_config()

        bad_meta = AlignmentMetadata(
            shape=self.north_shape,
            crs="EPSG:4326",  # Incompatible CRS!
            transform=self.north_transform,
            resolution_meters=self.res_10m,
        )
        bad_pair = SlicePair(
            slice_north=SliceInput(data=np.full(self.north_shape, -10.0, dtype=np.float32), metadata=bad_meta),
            slice_south=SliceInput(data=np.full(self.south_shape, -10.0, dtype=np.float32), metadata=self.south_meta),
        )

        slice_data = {
            config.reference_acquisition.product_id: bad_pair,
            config.comparison_acquisition.product_id: self._create_slice_pair(),
            config.subsequent_acquisitions[0].product_id: self._create_slice_pair(),
            config.subsequent_acquisitions[1].product_id: self._create_slice_pair(),
            config.subsequent_acquisitions[2].product_id: self._create_slice_pair(),
        }

        with self.assertRaises(RasterAlignmentError):
            run_scientific_pipeline(config=config, slice_data=slice_data)

    # =========================================================================
    # TEST 4: INCOMPLETE OBSERVATIONS FORCES UNVERIFIED (PRD HARD GATE N >= 3)
    # =========================================================================

    def test_pipeline_incomplete_observations_forces_unverified(self) -> None:
        """
        Verifies that when one subsequent observation is missing (allow_missing_subsequent=True),
        N_valid = 2 < 3 strictly forces final status to UNVERIFIED under the PRD hard gate.
        """
        config = self._build_investigation_config()

        # Build rasters on master grid
        ref_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        comp_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        comp_arr[15:25, 10:20] = -18.0  # Flood 100 px

        sub1_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        sub1_arr[16:24, 11:19] = -18.0  # Receding 64 px

        # Sub 2: MISSING (set to None)!
        sub2_arr = None

        # Sub 3: Drained (0 px)
        sub3_arr = np.full(self.master_shape, -10.0, dtype=np.float32)

        raster_data = {
            config.reference_acquisition.product_id: (ref_arr, self.master_meta),
            config.comparison_acquisition.product_id: (comp_arr, self.master_meta),
            config.subsequent_acquisitions[0].product_id: (sub1_arr, self.master_meta),
            config.subsequent_acquisitions[1].product_id: None,  # Missing!
            config.subsequent_acquisitions[2].product_id: (sub3_arr, self.master_meta),
        }

        result = run_scientific_pipeline(
            config=config,
            raster_data=raster_data,
            allow_missing_subsequent=True,
        )

        # PRD Hard Rule: N_valid = 2 forces UNVERIFIED!
        self.assertEqual(result.evidence_status, EvidenceStatus.UNVERIFIED)
        self.assertEqual(result.coverage_metrics["subsequent_acquisitions_valid"], 2)
        self.assertEqual(result.coverage_metrics["subsequent_acquisitions_missing"], 1)
        self.assertFalse(result.coverage_metrics["temporal_coverage_complete"])
        self.assertIn("Insufficient repeat observations (2 < 3)", result.classification_reasons[0])
        self.assertIn("MISSING", result.temporal_states)

    # =========================================================================
    # TEST 5: INVALID OBSERVATION HANDLING
    # =========================================================================

    def test_pipeline_invalid_observation_handling(self) -> None:
        """
        Verifies that observations flagged as invalid in environmental_context
        are excluded from valid count, forcing UNVERIFIED when valid < 3.
        """
        config = self._build_investigation_config()

        ref_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        comp_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        comp_arr[15:25, 10:20] = -18.0

        sub1_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        sub1_arr[16:24, 11:19] = -18.0

        sub2_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        sub2_arr[18:22, 13:17] = -18.0

        sub3_arr = np.full(self.master_shape, -10.0, dtype=np.float32)

        raster_data = {
            config.reference_acquisition.product_id: (ref_arr, self.master_meta),
            config.comparison_acquisition.product_id: (comp_arr, self.master_meta),
            config.subsequent_acquisitions[0].product_id: (sub1_arr, self.master_meta),
            config.subsequent_acquisitions[1].product_id: (sub2_arr, self.master_meta),
            config.subsequent_acquisitions[2].product_id: (sub3_arr, self.master_meta),
        }

        # Step 2 flagged invalid (geometric divergence)
        env_context = [
            {"is_valid": True},
            {"is_valid": False, "invalidation_reason": "Orbit state vector divergence"},
            {"is_valid": True},
        ]

        result = run_scientific_pipeline(
            config=config,
            raster_data=raster_data,
            environmental_context=env_context,
        )

        self.assertEqual(result.evidence_status, EvidenceStatus.UNVERIFIED)
        self.assertEqual(result.coverage_metrics["subsequent_acquisitions_valid"], 2)
        self.assertEqual(result.coverage_metrics["subsequent_acquisitions_invalid"], 1)
        self.assertIn("INVALID", result.temporal_states)

    # =========================================================================
    # TEST 6: TRACKER FAILURE (UNEXPLAINED SURGE YIELDS INCONCLUSIVE)
    # =========================================================================

    def test_pipeline_tracker_unexplained_surge_yields_inconclusive(self) -> None:
        """
        Verifies that an uncorroborated flood surge (> 15% expansion) without environmental
        forcing evaluates to INCONCLUSIVE.
        """
        config = self._build_investigation_config()

        ref_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        comp_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        comp_arr[15:25, 10:20] = -18.0  # 100 px

        sub1_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        sub1_arr[16:24, 11:19] = -18.0  # Recedes to 64 px

        sub2_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        sub2_arr[14:26, 8:22] = -18.0  # Surges to 12x14 = 168 px! (+162% surge)

        sub3_arr = np.full(self.master_shape, -10.0, dtype=np.float32)

        raster_data = {
            config.reference_acquisition.product_id: (ref_arr, self.master_meta),
            config.comparison_acquisition.product_id: (comp_arr, self.master_meta),
            config.subsequent_acquisitions[0].product_id: (sub1_arr, self.master_meta),
            config.subsequent_acquisitions[1].product_id: (sub2_arr, self.master_meta),
            config.subsequent_acquisitions[2].product_id: (sub3_arr, self.master_meta),
        }

        # Dry environmental context (rain = 2mm -> uncorroborated!)
        env_context = [
            {"rainfall_12d_mm": 5.0},
            {"rainfall_12d_mm": 2.0, "wind_speed_mps": 2.0},
            {"rainfall_12d_mm": 5.0},
        ]

        result = run_scientific_pipeline(
            config=config,
            raster_data=raster_data,
            environmental_context=env_context,
        )

        self.assertEqual(result.evidence_status, EvidenceStatus.INCONCLUSIVE)
        self.assertFalse(result.beat_test_summary.overall_beat_test_passed)
        self.assertEqual(result.beat_test_summary.failed_regions, 1)
        self.assertIn("RE_INUNDATED_UNEXPLAINED", result.temporal_states)

    # =========================================================================
    # TEST 7: THREE-TIER CORROBORATION OF SURGE (SUPPORTED)
    # =========================================================================

    def test_pipeline_tracker_explained_surge_with_three_tier_corroboration(self) -> None:
        """
        Verifies that a flood surge (+162%) is COMPLIANT (RE_INUNDATED_EXPLAINED)
        when all 3 tiers of the Three-Tier Physical Corroboration Framework concur,
        yielding SUPPORTED.
        """
        config = self._build_investigation_config()

        ref_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        comp_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        comp_arr[15:25, 10:20] = -18.0  # 100 px

        sub1_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        sub1_arr[16:24, 11:19] = -18.0  # 64 px

        sub2_arr = np.full(self.master_shape, -10.0, dtype=np.float32)
        sub2_arr[14:26, 8:22] = -18.0  # 168 px surge

        sub3_arr = np.full(self.master_shape, -10.0, dtype=np.float32)  # Drained

        raster_data = {
            config.reference_acquisition.product_id: (ref_arr, self.master_meta),
            config.comparison_acquisition.product_id: (comp_arr, self.master_meta),
            config.subsequent_acquisitions[0].product_id: (sub1_arr, self.master_meta),
            config.subsequent_acquisitions[1].product_id: (sub2_arr, self.master_meta),
            config.subsequent_acquisitions[2].product_id: (sub3_arr, self.master_meta),
        }

        # Step 2 corroborated: rain = 85mm, hydraulically plausible, calm wind (2.2 m/s)
        env_context = [
            {"rainfall_12d_mm": 5.0, "wind_speed_mps": 2.0, "hydraulically_plausible": True},
            {"rainfall_12d_mm": 85.0, "wind_speed_mps": 2.2, "hydraulically_plausible": True},
            {"rainfall_12d_mm": 5.0, "wind_speed_mps": 2.0, "hydraulically_plausible": True},
        ]

        result = run_scientific_pipeline(
            config=config,
            raster_data=raster_data,
            environmental_context=env_context,
        )

        self.assertEqual(result.evidence_status, EvidenceStatus.SUPPORTED)
        self.assertTrue(result.beat_test_summary.overall_beat_test_passed)
        self.assertIn("RE_INUNDATED_EXPLAINED", result.temporal_states)

    # =========================================================================
    # TEST 8: STRUCTURED RESULTS & EVIDENCE LEDGER COMPLETENESS
    # =========================================================================

    def test_pipeline_structured_results_compliance(self) -> None:
        """
        Verifies that structured results (dates, states, evidence status, coverage,
        provenance, limitations) are fully populated and JSON serializable.
        """
        config = self._build_investigation_config()

        ref_pair = self._create_slice_pair()
        comp_pair = self._create_slice_pair(flood_box=(15, 25, 10, 20))
        sub1_pair = self._create_slice_pair(flood_box=(16, 24, 11, 19))
        sub2_pair = self._create_slice_pair(flood_box=(18, 22, 13, 17))
        sub3_pair = self._create_slice_pair()

        slice_data = {
            config.reference_acquisition.product_id: ref_pair,
            config.comparison_acquisition.product_id: comp_pair,
            config.subsequent_acquisitions[0].product_id: sub1_pair,
            config.subsequent_acquisitions[1].product_id: sub2_pair,
            config.subsequent_acquisitions[2].product_id: sub3_pair,
        }

        result = run_scientific_pipeline(config=config, slice_data=slice_data)

        # Check dataclass fields
        self.assertEqual(len(result.acquisition_dates), 5)
        self.assertEqual(len(result.temporal_states), 4)  # Peak + 3 subsequent
        self.assertIn("DRAINED", result.temporal_states)
        self.assertEqual(result.coverage_metrics["subsequent_acquisitions_valid"], 3)
        self.assertGreater(len(result.scientific_limitations), 0)

        # Verify JSON serializability of Evidence Ledger
        ledger = result.evidence_ledger
        serialized = json.dumps(ledger, indent=2)
        self.assertIn('"structured_results"', serialized)
        self.assertIn('"acquisition_dates"', serialized)
        self.assertIn('"temporal_states"', serialized)
        self.assertIn('"coverage"', serialized)
        self.assertIn('"slice_assembly_provenance"', serialized)
        self.assertIn('"scientific_limitations"', serialized)


if __name__ == "__main__":
    unittest.main()
