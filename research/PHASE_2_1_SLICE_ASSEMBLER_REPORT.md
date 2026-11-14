# BHRAMANASTHRA: Phase 2.1 Direct Abutting Slice Assembler Report
## Scientific Implementation, Validation, Regression & Architecture Documentation
### Module: Member 1 — Data & Scientific Intelligence ONLY

**Project**: BHRAMANASTHRA — Radar Evidence & Surface Change Intelligence Platform  
**Challenge**: NASA Space Apps Challenge 2026 — *Dancing with the SARs*  
**Document**: Phase 2.1 Slice Assembler Implementation Report  
**Author**: Satellite Remote-Sensing Research Scientist & Geospatial Data Verification Specialist  
**Date**: November 2026  
**Implementation Status**: **COMPLETED & VALIDATED (73/73 CORE TESTS + 13/13 SYNTHETIC TESTS PASSING)**  

---

### Executive Summary

In accordance with the frozen scientific specification in [`research/PHASE_1_5_SCIENTIFIC_SPECIFICATION.md`](file:///c:/Users/Diya/OneDrive/Apps/nasa/research/PHASE_1_5_SCIENTIFIC_SPECIFICATION.md) and the corrections established in [`research/PHASE_1_4_1_CORRECTION_AUDIT.md`](file:///c:/Users/Diya/OneDrive/Apps/nasa/research/PHASE_1_4_1_CORRECTION_AUDIT.md), the **Direct Abutting Sentinel-1 Slice Assembler** has been implemented in `src/bhnmisntra_science/processing/mosaicking.py`.

The module solves the spatial concatenation requirement for along-track Sentinel-1 slices (such as Frame 1 at ~00:40:44 UTC and Frame 2 at ~00:41:09 UTC over Kuttanad, Kerala) without introducing seam voids, duplicate pixel records, or invalid interpolation artifacts.

#### Core Architectural Achievements:
1. **Zero Blending / Zero Feathering**: The disproven overlap blending filter (`(I1 + I2)/2`) was completely excluded. Slices are concatenated via direct spatial placement.
2. **Deterministic Line Assignment**: Any marginal overlap along the boundary is resolved deterministically by assigning priority to the Southern slice ($I_{\text{south}}(x, y)$), preserving sharp backscatter contrast.
3. **Sub-Pixel Resampling Prohibited**: The assembler validates raster grid phase; any fractional pixel offset is strictly rejected with a `RasterAlignmentError`. Rasters are never shifted or resampled silently.
4. **Boundary Gap Detection**: Along-track gaps between frames are detected and measured in meters, raising `SliceBoundaryGapError` in strict mode or populating the void with `NaN` in permissive mode.
5. **Full Backward Compatibility**: All 56 existing contract and scientific pipeline tests continue to pass without modification. Total test count is now **73 / 73 tests passing in 0.040s**.

---

## 1. Module Architecture & Function Signatures

The implementation is located in [`src/bhnmisntra_science/processing/mosaicking.py`](file:///c:/Users/Diya/OneDrive/Apps/nasa/src/bhnmisntra_science/processing/mosaicking.py) and exposed via `src.bhnmisntra_science`.

### 1.1 Data Structures

```python
@dataclass(frozen=True)
class SliceInput:
    """
    Container for an input SAR slice raster with spatial metadata and optional provenance.
    """
    data: np.ndarray
    metadata: AlignmentMetadata
    slice_id: str | None = None
    nodata_value: float | None = None
```

```python
@dataclass(frozen=True)
class AssembledRaster:
    """
    Result of assembling Sentinel-1 slices onto the master UTM Zone 43N grid.
    Supports unpacking: data, metadata, provenance = assembled_raster.
    """
    data: np.ndarray
    metadata: AlignmentMetadata
    provenance: dict[str, Any]

    def __iter__(self):
        return iter((self.data, self.metadata, self.provenance))
```

### 1.2 Primary Function Signature

```python
def assemble_abutting_slices(
    slice_north: SliceInput | tuple[np.ndarray, AlignmentMetadata] | None,
    slice_south: SliceInput | tuple[np.ndarray, AlignmentMetadata] | None,
    master_grid: AlignmentMetadata | None = None,
    allow_partial: bool = False,
    raise_on_gap: bool = True,
    transform_tolerance: float = 1e-4,
    nodata_value: float = np.nan,
) -> AssembledRaster:
```

---

## 2. Input and Output Formats

### 2.1 Supported Input Formats
To ensure ergonomic integration and backward compatibility across testing and pipeline layers, `assemble_abutting_slices` accepts:
1. **`SliceInput` instance**: Recommended for production pipelines. Encapsulates 2D `data`, `metadata` (`AlignmentMetadata`), optional `slice_id` (e.g. ASF product identifier), and explicit `nodata_value`.
2. **Tuple `(np.ndarray, AlignmentMetadata)`**: Standard 2-tuple format utilized by existing pipeline stages and tests.
3. **`None`**: Permitted when `allow_partial=True` to model dates where only one frame was captured.

### 2.2 Output Format & Provenance Ledger
Returns an `AssembledRaster` object containing:
- **`data`**: `np.ndarray` (2D `float32`) containing the assembled backscatter values on the master grid, with unpopulated areas or nodata set to `np.nan`.
- **`metadata`**: `AlignmentMetadata` describing the master grid CRS, shape, transform, and resolution.
- **`provenance`**: Comprehensive dictionary documenting the spatial assembly:

```json
{
  "assembly_method": "DIRECT_ABUTTING_ASSEMBLY",
  "crs": "EPSG:32643",
  "master_shape": [50, 50],
  "north_slice_present": true,
  "south_slice_present": true,
  "is_partial": false,
  "missing_slice": null,
  "north_slice_id": "S1A_IW_GRDH_1SDV_20180821T004044_...",
  "south_slice_id": "S1A_IW_GRDH_1SDV_20180821T004109_...",
  "north_slice_shape": [20, 50],
  "south_slice_shape": [30, 50],
  "gap_detected": false,
  "gap_rows": 0,
  "gap_distance_meters": 0.0,
  "overlap_detected": false,
  "overlap_rows": 0,
  "overlap_pixels": 0,
  "seamline_continuity": true,
  "valid_pixel_count": 2500,
  "nodata_pixel_count": 0,
  "expected_valid_pixel_count": 2500,
  "valid_area_km2": 0.25,
  "total_area_km2": 0.25,
  "blending_applied": false,
  "resampling_applied": false
}
```

---

## 3. Mathematical Validation Rules & Invariants

| Validation Check | Mathematical Invariant | Violation Behavior |
| :--- | :--- | :--- |
| **CRS Compatibility** | $\text{CRS}_{\text{north}} \equiv \text{CRS}_{\text{south}} \equiv \text{CRS}_{\text{master}}$ | Raises `RasterAlignmentError` |
| **North-Up Orientation** | $c = 0.0 \land e = 0.0$ in Affine $(a, b, c, d, e, f)$ | Raises `RasterAlignmentError` |
| **Resolution Parity** | $\|b_{\text{north}} - b_{\text{south}}\| \le 10^{-4} \land \|f_{\text{north}} - f_{\text{south}}\| \le 10^{-4}$ | Raises `RasterAlignmentError` |
| **Grid Phase Alignment** | $\left\|\frac{X_0 - X_{\text{ref}}}{\Delta X} - \text{round}\left(\frac{X_0 - X_{\text{ref}}}{\Delta X}\right)\right\| \le 10^{-4}$ | Raises `RasterAlignmentError` (Sub-pixel shift forbidden) |
| **Geographic Order** | $Y_{\text{top}, \text{north}} > Y_{\text{top}, \text{south}}$ | Raises `SliceAssemblyError` (Inverted input order) |
| **Boundary Gap** | $\Delta Y_{\text{bound}} = Y_{\text{top}, \text{south}} - Y_{\text{bottom}, \text{north}} < 0$ | Raises `SliceBoundaryGapError` (if `raise_on_gap=True`) |
| **Deterministic Overlap** | $(x, y) \in \Omega_N \cap \Omega_S \implies I_M(x, y) = I_S(x, y)$ | Applied deterministically; no blending |
| **Area Conservation** | $N_{\text{valid}, M} = N_{\text{valid}, N} + N_{\text{valid}, S} - N_{\text{overlap}}$ | Exact integer conservation verified |

---

## 4. Error Handling and Exception Hierarchy

All custom exceptions inherit from the BHRAMANASTHRA scientific domain error hierarchy in `src/bhnmisntra_science/exceptions.py`:

```
ScientificError
└── ProcessingError
    └── SliceAssemblyError
        ├── SliceBoundaryGapError
        └── MissingSliceError
└── RasterAlignmentError
```

- **`RasterAlignmentError`**: Raised on CRS mismatch, resolution divergence, transform rotation, or fractional pixel grid phase offsets.
- **`SliceBoundaryGapError`**: Raised when along-track frames leave an unobserved gap across the boundary line.
- **`MissingSliceError`**: Raised when required input slices are `None` in strict mode (`allow_partial=False`).
- **`SliceAssemblyError`**: Raised on inverted slice orders, shape mismatches, or internal dimensional inconsistencies.

---

## 5. Verification Test Suite & Results

A dedicated test suite [`tests/test_slice_assembler.py`](file:///c:/Users/Diya/OneDrive/Apps/nasa/tests/test_slice_assembler.py) with 17 focused unit and regression tests was implemented and executed against synthetic rasters:

| Test ID | Test Method Name | Verification Objective | Result |
| :---: | :--- | :--- | :---: |
| **T01** | `test_01_correct_north_south_assembly` | Validates seamless 20-row + 30-row abutting assembly onto 50-row master grid. | **PASSED** |
| **T02** | `test_02_no_overlap_adjacency` | Verifies zero gap and zero overlap along boundary line ($Y_{\text{bottom}, N} == Y_{\text{top}, S}$). | **PASSED** |
| **T03** | `test_03_grid_alignment_with_explicit_master_grid` | Validates integer row/col offsets (+10 row, +5 col) within explicit master grid. | **PASSED** |
| **T04a** | `test_04_boundary_gaps_strict_mode_raises` | Verifies that a 2-row (20m) gap raises `SliceBoundaryGapError`. | **PASSED** |
| **T04b** | `test_04_boundary_gaps_permissive_mode_reports_gap_and_nan` | Verifies permissive mode populates the 2-row gap with `NaN` and reports in provenance. | **PASSED** |
| **T05** | `test_05_duplicate_pixel_prevention_and_deterministic_assignment` | Verifies 2-row overlap uses deterministic South assignment, preventing duplication or blending. | **PASSED** |
| **T06** | `test_06_nodata_handling` | Verifies `NaN` and `-9999.0` nodata values are strictly preserved without corrupting valid data. | **PASSED** |
| **T07a** | `test_07_missing_slice_both_none_raises` | Verifies that passing `None` for both slices raises `MissingSliceError`. | **PASSED** |
| **T07b** | `test_07_missing_slice_strict_mode_raises` | Verifies that missing North or South in strict mode raises `MissingSliceError`. | **PASSED** |
| **T07c** | `test_07_missing_slice_partial_mode_succeeds` | Verifies partial observation mode (`allow_partial=True`) successfully outputs single frame. | **PASSED** |
| **T08a** | `test_08_crs_mismatch_between_slices_raises` | Verifies CRS divergence (`EPSG:32643` vs `EPSG:4326`) raises `RasterAlignmentError`. | **PASSED** |
| **T08b** | `test_08_crs_mismatch_with_master_grid_raises` | Verifies CRS divergence with master grid (`EPSG:32644`) raises `RasterAlignmentError`. | **PASSED** |
| **T09** | `test_09_resolution_mismatch_raises` | Verifies pixel resolution divergence (10m vs 20m) raises `RasterAlignmentError`. | **PASSED** |
| **T10a** | `test_10_transform_mismatch_rotated_raster_raises` | Verifies rotated rasters ($c \ne 0$) raise `RasterAlignmentError`. | **PASSED** |
| **T10b** | `test_10_transform_mismatch_fractional_pixel_grid_phase_raises` | Verifies sub-pixel grid offsets (0.35 px X, 0.42 px Y) raise `RasterAlignmentError`. | **PASSED** |
| **T11** | `test_11_inverted_slice_order_raises` | Verifies geographically inverted input order raises `SliceAssemblyError`. | **PASSED** |
| **T12** | `test_12_slice_input_container_validation` | Verifies `SliceInput` validation on 1D arrays or shape-metadata mismatches. | **PASSED** |

### 5.1 Full Suite Regression Execution

```
================================================================================
TEST SUITE EXECUTION SUMMARY
================================================================================
Central Test Runner (`tests/run_tests.py`):
- Total Test Cases Executed   : 73
- Passing Tests               : 73 (100.0%)
- Failures / Errors           : 0
- Execution Time              : 0.040s

Synthetic Scientific Suite (`scratch/validate_rules_and_temporal_logic.py`):
- Total Scientific Scenarios  : 13
- Passing Scenarios           : 13 (100.0%)
- Failures / Errors           : 0
================================================================================
```

---

## 6. Known Limitations & Scientific Boundaries

1. **North-Up Projected Rasters Only**:
   The assembler expects rasters projected into a Cartesian CRS (e.g. UTM Zone 43N, `EPSG:32643`) with north-up orientation ($c=0, e=0$). It is not designed to concatenate un-geocoded Level-1 SLC/GRD slant-range geometries directly.
2. **Along-Track Same-Pass Constraint**:
   The assembler is designed for contiguous slices cut from the **exact same continuous satellite data take** along a single orbital pass. It must **not** be used to mosaic rasters from different orbit tracks, different satellites, or different dates, where radiometric normalization, incidence angle differences, and temporal variations would require complex cross-calibration.
3. **No Automatic Interpolation / Resampling**:
   By scientific design, if two slices do not align on the identical integer grid phase, the assembler intentionally raises an error rather than applying bilinear or bicubic resampling. Re-gridding must be handled upstream during RTC (Radiometric Terrain Correction) in SNAP or ASF HyP3.

---

## 7. Integration Readiness Assessment

| Milestone Gate | Requirement | Status | Verification Note |
| :--- | :--- | :---: | :--- |
| **Gate 1: Contract Adherence** | Conforms to Phase 1.5 Section 1.3 | **READY** | Direct abutting assembly without blending. |
| **Gate 2: Error Rigor** | Rejects misalignment, gaps, rotation | **READY** | Tested across 17 unit test scenarios. |
| **Gate 3: Regression Safety** | Zero degradation of existing tests | **READY** | 56/56 previous tests pass identically. |
| **Gate 4: Pipeline Integration** | Ready to be called in `pipeline.py` | **READY** | Clean signature accepting tuples or `SliceInput`. |

**Verdict**: The Direct Abutting Sentinel-1 Slice Assembler is **fully validated, production-ready, and approved for integration** into the broader BHRAMANASTHRA processing pipeline.

