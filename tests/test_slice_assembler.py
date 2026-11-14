"""
BHnMISnTRA: Direct Abutting Sentinel-1 Slice Assembler Tests.
Phase 2.1 Acceptance and Regression Test Suite.
"""

import unittest
import numpy as np

from src.bhnmisntra_science.processing.alignment import AlignmentMetadata
from src.bhnmisntra_science.processing.mosaicking import (
    AssembledRaster,
    SliceInput,
    assemble_abutting_slices,
)
from src.bhnmisntra_science.exceptions import (
    MissingSliceError,
    RasterAlignmentError,
    SliceAssemblyError,
    SliceBoundaryGapError,
)


class TestSliceAssembler(unittest.TestCase):
    """
    Focused tests for the Direct Abutting Sentinel-1 Slice Assembler.
    Enforces all 10 requirements specified in Phase 1.5 & Phase 2 prompt.
    """

    def setUp(self) -> None:
        # Standard north-up 10m UTM Zone 43N parameters
        self.crs_utm43n = "EPSG:32643"
        self.res_10m = (10.0, 10.0)

        # Baseline coordinates for a contiguous scene
        # North slice: 20 rows x 50 cols (200m north-south x 500m east-west)
        # Top-left: (700000.0, 1100000.0) -> Bottom edge: 1100000.0 - 200.0 = 1099800.0
        self.north_shape = (20, 50)
        self.north_transform = (700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0)
        self.north_meta = AlignmentMetadata(
            shape=self.north_shape,
            crs=self.crs_utm43n,
            transform=self.north_transform,
            resolution_meters=self.res_10m,
        )
        self.north_data = np.full(self.north_shape, -12.0, dtype=np.float32)

        # South slice: 30 rows x 50 cols (300m north-south x 500m east-west)
        # Top-left exactly at North bottom: (700000.0, 1099800.0) -> Bottom edge: 1099500.0
        self.south_shape = (30, 50)
        self.south_transform = (700000.0, 10.0, 0.0, 1099800.0, 0.0, -10.0)
        self.south_meta = AlignmentMetadata(
            shape=self.south_shape,
            crs=self.crs_utm43n,
            transform=self.south_transform,
            resolution_meters=self.res_10m,
        )
        self.south_data = np.full(self.south_shape, -18.0, dtype=np.float32)

    # =========================================================================
    # 1. CORRECT NORTH / SOUTH ASSEMBLY
    # =========================================================================

    def test_01_correct_north_south_assembly(self) -> None:
        """Verifies seamless assembly of abutting North and South slices onto master grid."""
        result = assemble_abutting_slices(
            slice_north=(self.north_data, self.north_meta),
            slice_south=(self.south_data, self.south_meta),
        )

        self.assertIsInstance(result, AssembledRaster)
        data = result.data
        meta = result.metadata
        prov = result.provenance

        # Master grid dimensions: 20 + 30 = 50 rows, 50 cols
        self.assertEqual(data.shape, (50, 50))
        self.assertEqual(meta.shape, (50, 50))
        self.assertEqual(meta.crs, "EPSG:32643")
        self.assertEqual(meta.transform, (700000.0, 10.0, 0.0, 1100000.0, 0.0, -10.0))

        # Check Northern data in top 20 rows
        np.testing.assert_allclose(data[0:20, :], -12.0)
        # Check Southern data in bottom 30 rows
        np.testing.assert_allclose(data[20:50, :], -18.0)

        # Check provenance details
        self.assertEqual(prov["assembly_method"], "DIRECT_ABUTTING_ASSEMBLY")
        self.assertTrue(prov["north_slice_present"])
        self.assertTrue(prov["south_slice_present"])
        self.assertFalse(prov["is_partial"])
        self.assertFalse(prov["gap_detected"])
        self.assertFalse(prov["overlap_detected"])
        self.assertTrue(prov["seamline_continuity"])
        self.assertFalse(prov["blending_applied"])
        self.assertFalse(prov["resampling_applied"])
        self.assertEqual(prov["valid_pixel_count"], 2500)
        self.assertEqual(prov["nodata_pixel_count"], 0)

        # Verify tuple unpacking support
        arr_unpacked, meta_unpacked, prov_unpacked = result
        self.assertEqual(arr_unpacked.shape, (50, 50))
        self.assertEqual(meta_unpacked.crs, "EPSG:32643")

    # =========================================================================
    # 2. NO-OVERLAP ADJACENCY
    # =========================================================================

    def test_02_no_overlap_adjacency(self) -> None:
        """Verifies that strictly adjacent along-track slices have zero overlap and zero gap."""
        # Top of South matches Bottom of North exactly
        y_bottom_n = self.north_transform[3] + self.north_transform[5] * self.north_shape[0]
        y_top_s = self.south_transform[3]
        self.assertAlmostEqual(y_bottom_n, y_top_s, places=6)

        result = assemble_abutting_slices(
            slice_north=(self.north_data, self.north_meta),
            slice_south=(self.south_data, self.south_meta),
        )

        prov = result.provenance
        self.assertFalse(prov["gap_detected"])
        self.assertEqual(prov["gap_rows"], 0)
        self.assertEqual(prov["gap_distance_meters"], 0.0)
        self.assertFalse(prov["overlap_detected"])
        self.assertEqual(prov["overlap_rows"], 0)
        self.assertEqual(prov["overlap_pixels"], 0)

        # Verify exact line boundary transition between row 19 and row 20
        self.assertEqual(result.data[19, 25], -12.0)
        self.assertEqual(result.data[20, 25], -18.0)
        self.assertTrue(prov["seamline_continuity"])

    # =========================================================================
    # 3. GRID ALIGNMENT
    # =========================================================================

    def test_03_grid_alignment_with_explicit_master_grid(self) -> None:
        """Verifies integer grid placement within an explicit study area master grid."""
        # Master grid enclosing the scene with a 10-pixel top margin and 5-pixel left margin
        master_shape = (70, 60)
        master_transform = (699950.0, 10.0, 0.0, 1100100.0, 0.0, -10.0)
        master_meta = AlignmentMetadata(
            shape=master_shape,
            crs=self.crs_utm43n,
            transform=master_transform,
            resolution_meters=self.res_10m,
        )

        result = assemble_abutting_slices(
            slice_north=(self.north_data, self.north_meta),
            slice_south=(self.south_data, self.south_meta),
            master_grid=master_meta,
        )

        self.assertEqual(result.data.shape, (70, 60))
        # Top 10 rows (rows 0..9) should be NaN (margin)
        self.assertTrue(np.all(np.isnan(result.data[0:10, :])))
        # Left 5 cols (cols 0..4) should be NaN (margin)
        self.assertTrue(np.all(np.isnan(result.data[:, 0:5])))
        # North slice placed at row 10..29, col 5..54
        np.testing.assert_allclose(result.data[10:30, 5:55], -12.0)
        # South slice placed at row 30..59, col 5..54
        np.testing.assert_allclose(result.data[30:60, 5:55], -18.0)
        # Bottom 10 rows (rows 60..69) should be NaN (margin)
        self.assertTrue(np.all(np.isnan(result.data[60:70, :])))

    # =========================================================================
    # 4. BOUNDARY GAPS
    # =========================================================================

    def test_04_boundary_gaps_strict_mode_raises(self) -> None:
        """Verifies that an along-track boundary gap raises SliceBoundaryGapError by default."""
        # Shift South slice 20m (2 rows) southwards, creating an unobserved void
        gap_transform = (700000.0, 10.0, 0.0, 1099780.0, 0.0, -10.0)
        gap_south_meta = AlignmentMetadata(
            shape=self.south_shape,
            crs=self.crs_utm43n,
            transform=gap_transform,
            resolution_meters=self.res_10m,
        )

        with self.assertRaises(SliceBoundaryGapError) as ctx:
            assemble_abutting_slices(
                slice_north=(self.north_data, self.north_meta),
                slice_south=(self.south_data, gap_south_meta),
                raise_on_gap=True,
            )
        self.assertIn("Along-track boundary gap detected", str(ctx.exception))
        self.assertIn("2 unobserved row(s)", str(ctx.exception))
        self.assertIn("20.0 meters", str(ctx.exception))

    def test_04_boundary_gaps_permissive_mode_reports_gap_and_nan(self) -> None:
        """Verifies that with raise_on_gap=False, the gap is recorded and populated with NaN."""
        gap_transform = (700000.0, 10.0, 0.0, 1099780.0, 0.0, -10.0)
        gap_south_meta = AlignmentMetadata(
            shape=self.south_shape,
            crs=self.crs_utm43n,
            transform=gap_transform,
            resolution_meters=self.res_10m,
        )

        result = assemble_abutting_slices(
            slice_north=(self.north_data, self.north_meta),
            slice_south=(self.south_data, gap_south_meta),
            raise_on_gap=False,
        )

        prov = result.provenance
        self.assertTrue(prov["gap_detected"])
        self.assertEqual(prov["gap_rows"], 2)
        self.assertEqual(prov["gap_distance_meters"], 20.0)

        # Output height = 20 (North) + 2 (gap) + 30 (South) = 52 rows
        self.assertEqual(result.data.shape, (52, 50))
        # North rows 0..19 are -12.0
        np.testing.assert_allclose(result.data[0:20, :], -12.0)
        # Gap rows 20..21 are NaN
        self.assertTrue(np.all(np.isnan(result.data[20:22, :])))
        # South rows 22..51 are -18.0
        np.testing.assert_allclose(result.data[22:52, :], -18.0)

    # =========================================================================
    # 5. DUPLICATE PIXEL PREVENTION & DETERMINISTIC LINE ASSIGNMENT
    # =========================================================================

    def test_05_duplicate_pixel_prevention_and_deterministic_assignment(self) -> None:
        """
        Verifies that any overlapping rows enforce Deterministic Line Assignment (South priority)
        without pixel duplication or overlap blending / averaging.
        """
        # Create a 2-row overlap: South starts at 1099820.0 (2 rows above North bottom at 1099800.0)
        overlap_transform = (700000.0, 10.0, 0.0, 1099820.0, 0.0, -10.0)
        overlap_south_meta = AlignmentMetadata(
            shape=self.south_shape,
            crs=self.crs_utm43n,
            transform=overlap_transform,
            resolution_meters=self.res_10m,
        )

        result = assemble_abutting_slices(
            slice_north=(self.north_data, self.north_meta),
            slice_south=(self.south_data, overlap_south_meta),
        )

        prov = result.provenance
        # Total output rows = 20 + 30 - 2 = 48 rows (no duplication!)
        self.assertEqual(result.data.shape, (48, 50))
        self.assertTrue(prov["overlap_detected"])
        self.assertEqual(prov["overlap_rows"], 2)
        self.assertEqual(prov["overlap_pixels"], 100)
        self.assertFalse(prov["blending_applied"])

        # Deterministic Line Assignment: South slice (-18.0) wins on overlapping rows 18 and 19
        np.testing.assert_allclose(result.data[18:20, :], -18.0)
        # Verify blending was NOT applied: value must NOT be (-12.0 + -18.0) / 2 = -15.0
        self.assertFalse(np.isclose(result.data[18, 0], -15.0))

        # Area conservation: 20*50 + 30*50 - 100 = 2400 pixels
        self.assertEqual(prov["valid_pixel_count"], 2400)
        self.assertEqual(prov["expected_valid_pixel_count"], 2400)

    # =========================================================================
    # 6. NODATA HANDLING
    # =========================================================================

    def test_06_nodata_handling(self) -> None:
        """Verifies that NaNs and explicit nodata values are preserved as NaN without corrupting valid data."""
        # Inject NaNs into North slice
        north_with_nan = self.north_data.copy()
        north_with_nan[5, 5] = np.nan
        north_with_nan[5, 6] = np.nan

        # Inject -9999.0 nodata into South slice using SliceInput container
        south_with_nodata = self.south_data.copy()
        south_with_nodata[10, 10] = -9999.0
        south_with_nodata[10, 11] = -9999.0

        slice_s = SliceInput(
            data=south_with_nodata,
            metadata=self.south_meta,
            slice_id="FRAME_2_SOUTH",
            nodata_value=-9999.0,
        )

        result = assemble_abutting_slices(
            slice_north=(north_with_nan, self.north_meta),
            slice_south=slice_s,
        )

        # Preserved NaNs from North slice (row 5)
        self.assertTrue(np.isnan(result.data[5, 5]))
        self.assertTrue(np.isnan(result.data[5, 6]))
        # Preserved nodata (-9999.0 -> NaN) from South slice (row 20 + 10 = 30)
        self.assertTrue(np.isnan(result.data[30, 10]))
        self.assertTrue(np.isnan(result.data[30, 11]))

        # Check total nodata pixel count: 4 nodata pixels
        self.assertEqual(result.provenance["nodata_pixel_count"], 4)
        self.assertEqual(result.provenance["valid_pixel_count"], 2496)

    # =========================================================================
    # 7. MISSING SLICE
    # =========================================================================

    def test_07_missing_slice_both_none_raises(self) -> None:
        """Verifies that passing None for both slices raises MissingSliceError."""
        with self.assertRaises(MissingSliceError):
            assemble_abutting_slices(slice_north=None, slice_south=None)

    def test_07_missing_slice_strict_mode_raises(self) -> None:
        """Verifies that missing either slice in strict mode (allow_partial=False) raises MissingSliceError."""
        with self.assertRaises(MissingSliceError) as ctx_n:
            assemble_abutting_slices(
                slice_north=None,
                slice_south=(self.south_data, self.south_meta),
                allow_partial=False,
            )
        self.assertIn("Missing required North slice", str(ctx_n.exception))

        with self.assertRaises(MissingSliceError) as ctx_s:
            assemble_abutting_slices(
                slice_north=(self.north_data, self.north_meta),
                slice_south=None,
                allow_partial=False,
            )
        self.assertIn("Missing required South slice", str(ctx_s.exception))

    def test_07_missing_slice_partial_mode_succeeds(self) -> None:
        """Verifies partial single-slice observation support with allow_partial=True."""
        # Single South slice acquisition on master grid
        result = assemble_abutting_slices(
            slice_north=None,
            slice_south=(self.south_data, self.south_meta),
            allow_partial=True,
        )

        prov = result.provenance
        self.assertTrue(prov["is_partial"])
        self.assertEqual(prov["missing_slice"], "north")
        self.assertFalse(prov["north_slice_present"])
        self.assertTrue(prov["south_slice_present"])
        self.assertEqual(result.data.shape, (30, 50))
        np.testing.assert_allclose(result.data, -18.0)

    # =========================================================================
    # 8. CRS MISMATCH
    # =========================================================================

    def test_08_crs_mismatch_between_slices_raises(self) -> None:
        """Verifies that CRS mismatch between North and South slices raises RasterAlignmentError."""
        mismatched_meta = AlignmentMetadata(
            shape=self.south_shape,
            crs="EPSG:4326",  # Geographic WGS84 vs UTM Zone 43N
            transform=(76.0, 0.0001, 0.0, 9.5, 0.0, -0.0001),
            resolution_meters=self.res_10m,
        )

        with self.assertRaises(RasterAlignmentError) as ctx:
            assemble_abutting_slices(
                slice_north=(self.north_data, self.north_meta),
                slice_south=(self.south_data, mismatched_meta),
            )
        self.assertIn("Coordinate reference system mismatch", str(ctx.exception))

    def test_08_crs_mismatch_with_master_grid_raises(self) -> None:
        """Verifies that CRS mismatch between slices and master grid raises RasterAlignmentError."""
        mismatched_master = AlignmentMetadata(
            shape=(50, 50),
            crs="EPSG:32644",  # UTM Zone 44N vs UTM Zone 43N
            transform=self.north_transform,
            resolution_meters=self.res_10m,
        )

        with self.assertRaises(RasterAlignmentError) as ctx:
            assemble_abutting_slices(
                slice_north=(self.north_data, self.north_meta),
                slice_south=(self.south_data, self.south_meta),
                master_grid=mismatched_master,
            )
        self.assertIn("CRS mismatch with master grid", str(ctx.exception))

    # =========================================================================
    # 9. RESOLUTION MISMATCH
    # =========================================================================

    def test_09_resolution_mismatch_raises(self) -> None:
        """Verifies that resolution divergence between slices raises RasterAlignmentError."""
        mismatched_res_meta = AlignmentMetadata(
            shape=(15, 25),
            crs=self.crs_utm43n,
            transform=(700000.0, 20.0, 0.0, 1099800.0, 0.0, -20.0),  # 20m pixel spacing
            resolution_meters=(20.0, 20.0),
        )
        data_20m = np.full((15, 25), -18.0, dtype=np.float32)

        with self.assertRaises(RasterAlignmentError) as ctx:
            assemble_abutting_slices(
                slice_north=(self.north_data, self.north_meta),
                slice_south=(data_20m, mismatched_res_meta),
            )
        self.assertIn("Resolution mismatch", str(ctx.exception))

    # =========================================================================
    # 10. TRANSFORM MISMATCH
    # =========================================================================

    def test_10_transform_mismatch_rotated_raster_raises(self) -> None:
        """Verifies that non-zero shear/rotation terms raise RasterAlignmentError."""
        rotated_meta = AlignmentMetadata(
            shape=self.north_shape,
            crs=self.crs_utm43n,
            transform=(700000.0, 10.0, 0.5, 1100000.0, 0.0, -10.0),  # c=0.5 rotation
            resolution_meters=self.res_10m,
        )

        with self.assertRaises(RasterAlignmentError) as ctx:
            assemble_abutting_slices(
                slice_north=(self.north_data, rotated_meta),
                slice_south=(self.south_data, self.south_meta),
            )
        self.assertIn("Rotated raster detected", str(ctx.exception))

    def test_10_transform_mismatch_fractional_pixel_grid_phase_raises(self) -> None:
        """
        Verifies that sub-pixel coordinate shifts (fractional grid phase) are strictly rejected
        to prevent silent resampling or spatial distortion.
        """
        # Shift South slice by 3.5m (0.35 pixels) in X
        shifted_transform_x = (700003.5, 10.0, 0.0, 1099800.0, 0.0, -10.0)
        shifted_meta_x = AlignmentMetadata(
            shape=self.south_shape,
            crs=self.crs_utm43n,
            transform=shifted_transform_x,
            resolution_meters=self.res_10m,
        )

        with self.assertRaises(RasterAlignmentError) as ctx_x:
            assemble_abutting_slices(
                slice_north=(self.north_data, self.north_meta),
                slice_south=(self.south_data, shifted_meta_x),
            )
        self.assertIn("Grid phase mismatch", str(ctx_x.exception))
        self.assertIn("shifted by 0.3500 fractional pixels", str(ctx_x.exception))
        self.assertIn("Silent resampling or coordinate shifting is strictly forbidden", str(ctx_x.exception))

        # Shift South slice by 4.2m (0.42 pixels) in Y
        shifted_transform_y = (700000.0, 10.0, 0.0, 1099804.2, 0.0, -10.0)
        shifted_meta_y = AlignmentMetadata(
            shape=self.south_shape,
            crs=self.crs_utm43n,
            transform=shifted_transform_y,
            resolution_meters=self.res_10m,
        )

        with self.assertRaises(RasterAlignmentError) as ctx_y:
            assemble_abutting_slices(
                slice_north=(self.north_data, self.north_meta),
                slice_south=(self.south_data, shifted_meta_y),
            )
        self.assertIn("Grid phase mismatch", str(ctx_y.exception))
        self.assertIn("shifted by 0.4200 fractional pixels", str(ctx_y.exception))

    # =========================================================================
    # 11. ADDITIONAL STRUCTURAL & GEOMETRIC VERIFICATIONS
    # =========================================================================

    def test_11_inverted_slice_order_raises(self) -> None:
        """Verifies that passing slices in inverted geographic order raises SliceAssemblyError."""
        # Pass South slice as slice_north, and North slice as slice_south
        with self.assertRaises(SliceAssemblyError) as ctx:
            assemble_abutting_slices(
                slice_north=(self.south_data, self.south_meta),
                slice_south=(self.north_data, self.north_meta),
            )
        self.assertIn("Inverted slice order", str(ctx.exception))

    def test_12_slice_input_container_validation(self) -> None:
        """Verifies SliceInput validation rules."""
        # Shape mismatch between array and metadata
        with self.assertRaises(SliceAssemblyError):
            SliceInput(
                data=np.zeros((10, 10), dtype=np.float32),
                metadata=self.north_meta,  # shape is (20, 50)
            )

        # 1D array
        with self.assertRaises(ValueError):
            SliceInput(
                data=np.zeros(100, dtype=np.float32),
                metadata=self.north_meta,
            )


if __name__ == "__main__":
    unittest.main()

