"""
BHnMISnTRA: Direct Abutting Sentinel-1 Slice Assembler.
Implementation of along-track direct spatial concatenation without overlap feathering.
Compliant with Phase 1.5 Scientific Specification and Phase 1.4.1 Correction Audit.
"""

from dataclasses import dataclass
import math
from typing import Any, Sequence
import numpy as np

from .alignment import AlignmentMetadata
from ..exceptions import (
    MissingSliceError,
    RasterAlignmentError,
    SliceAssemblyError,
    SliceBoundaryGapError,
)


@dataclass(frozen=True)
class SliceInput:
    """
    Container for an input SAR slice raster with spatial metadata and optional provenance.
    """
    data: np.ndarray
    metadata: AlignmentMetadata
    slice_id: str | None = None
    nodata_value: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, np.ndarray):
            raise TypeError(f"Slice data must be a numpy ndarray, got {type(self.data).__name__}")
        if self.data.ndim != 2:
            raise ValueError(f"Slice data must be a 2D array (height, width), got shape {self.data.shape}")
        if self.data.shape != self.metadata.shape:
            raise SliceAssemblyError(
                f"Slice data shape {self.data.shape} does not match metadata shape {self.metadata.shape}"
            )
        if not isinstance(self.metadata, AlignmentMetadata):
            raise TypeError(f"metadata must be an AlignmentMetadata instance, got {type(self.metadata).__name__}")


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


@dataclass(frozen=True)
class SlicePair:
    """
    Container for an along-track Sentinel-1 slice pair (North and South).
    Supports either SliceInput or (data, metadata) tuples for each slice.
    """
    slice_north: SliceInput | tuple[np.ndarray, AlignmentMetadata] | None
    slice_south: SliceInput | tuple[np.ndarray, AlignmentMetadata] | None
    allow_partial: bool = False
    raise_on_gap: bool = True


def _extract_slice_components(
    slice_item: SliceInput | tuple[np.ndarray, AlignmentMetadata] | None,
    name: str,
) -> tuple[np.ndarray, AlignmentMetadata, str | None, float | None] | None:
    """Extracts and verifies raw components from SliceInput, tuple, or None."""
    if slice_item is None:
        return None

    if isinstance(slice_item, SliceInput):
        return slice_item.data, slice_item.metadata, slice_item.slice_id, slice_item.nodata_value

    if isinstance(slice_item, tuple):
        if len(slice_item) != 2:
            raise TypeError(
                f"Expected 2-tuple (data, metadata) for {name}, got tuple of length {len(slice_item)}"
            )
        data, meta = slice_item
        if not isinstance(data, np.ndarray):
            raise TypeError(f"Expected numpy ndarray for {name} data, got {type(data).__name__}")
        if not isinstance(meta, AlignmentMetadata):
            raise TypeError(f"Expected AlignmentMetadata for {name} metadata, got {type(meta).__name__}")
        if data.ndim != 2:
            raise ValueError(f"{name} array must be 2D, got shape {data.shape}")
        if data.shape != meta.shape:
            raise SliceAssemblyError(
                f"{name} array shape {data.shape} does not match metadata shape {meta.shape}"
            )
        return data, meta, None, None

    raise TypeError(
        f"Invalid input type for {name}: expected SliceInput, tuple (data, metadata), or None; "
        f"got {type(slice_item).__name__}"
    )


def assemble_abutting_slices(
    slice_north: SliceInput | tuple[np.ndarray, AlignmentMetadata] | None,
    slice_south: SliceInput | tuple[np.ndarray, AlignmentMetadata] | None,
    master_grid: AlignmentMetadata | None = None,
    allow_partial: bool = False,
    raise_on_gap: bool = True,
    transform_tolerance: float = 1e-4,
    nodata_value: float = np.nan,
) -> AssembledRaster:
    """
    Assembles contiguous along-track Sentinel-1 North and South slices onto the master grid
    via Direct Abutting Spatial Assignment.

    Key Invariants:
      1. Slices must be in the identical CRS (e.g. EPSG:32643).
      2. Slices must share identical pixel resolution (e.g. 10m x 10m).
      3. Raster transforms must be north-up (no rotation or shear: c=0, e=0).
      4. Pixel grids must align on integer grid steps relative to the master grid.
         Sub-pixel shifts or silent resampling are strictly rejected.
      5. Slices must be strictly adjacent: gaps between slices are detected and reported
         (raises SliceBoundaryGapError if raise_on_gap=True).
      6. Overlap feathering / blending is NEVER applied. On any overlapping rows,
         Deterministic Line Assignment is enforced where South slice takes precedence.
      7. Output pixel duplication is prevented: each cell on the master grid is assigned once.

    Args:
        slice_north: Northern slice (SliceInput, (data, metadata) tuple, or None).
        slice_south: Southern slice (SliceInput, (data, metadata) tuple, or None).
        master_grid: Optional explicit AlignmentMetadata for target UTM grid. If None,
                     the tightest integer-aligned bounding grid enclosing active slices is deduced.
        allow_partial: If True, permits single-slice observation (marking missing slice as NaN).
                       If False, raises MissingSliceError if either slice is None.
        raise_on_gap: If True, raises SliceBoundaryGapError when an along-track boundary gap is detected.
        transform_tolerance: Maximum allowed floating point divergence for alignment checks.
        nodata_value: Value to treat as nodata in output (defaults to np.nan).

    Returns:
        AssembledRaster with assembled 2D array, master AlignmentMetadata, and detailed provenance.
    """
    # 1. Extract and validate components
    n_comp = _extract_slice_components(slice_north, "slice_north")
    s_comp = _extract_slice_components(slice_south, "slice_south")

    if n_comp is None and s_comp is None:
        raise MissingSliceError("Both North and South slices are None; cannot assemble empty inputs.")

    if not allow_partial:
        if n_comp is None:
            raise MissingSliceError("Missing required North slice in strict assembly mode (allow_partial=False).")
        if s_comp is None:
            raise MissingSliceError("Missing required South slice in strict assembly mode (allow_partial=False).")

    # 2. Extract arrays, metadata, and slice identities
    arr_n, meta_n, id_n, nodata_n = n_comp if n_comp is not None else (None, None, None, None)
    arr_s, meta_s, id_s, nodata_s = s_comp if s_comp is not None else (None, None, None, None)

    # 3. Coordinate Reference System (CRS) Validation
    active_metas = [m for m in (meta_n, meta_s) if m is not None]
    ref_crs = active_metas[0].crs.strip().upper()

    for idx, m in enumerate(active_metas[1:], start=1):
        if m.crs.strip().upper() != ref_crs:
            raise RasterAlignmentError(
                f"Coordinate reference system mismatch: North slice is '{meta_n.crs}', "
                f"while South slice is '{meta_s.crs}'. Input rasters must share identical CRS."
            )

    if master_grid is not None:
        if master_grid.crs.strip().upper() != ref_crs:
            raise RasterAlignmentError(
                f"CRS mismatch with master grid: input slice CRS is '{ref_crs}', "
                f"while master grid CRS is '{master_grid.crs}'."
            )

    # 4. Transform Rotation & Orientation Validation
    for m, label in zip((meta_n, meta_s), ("North slice", "South slice")):
        if m is not None:
            # Check shear/rotation terms c (transform[2]) and e (transform[4])
            if abs(m.transform[2]) > transform_tolerance or abs(m.transform[4]) > transform_tolerance:
                raise RasterAlignmentError(
                    f"Rotated raster detected in {label}: transform has shear/rotation terms "
                    f"(c={m.transform[2]:.6f}, e={m.transform[4]:.6f}). Only strict north-up rasters supported."
                )
            # Check orientation: b > 0 (east-west positive), f < 0 (north-south negative)
            if m.transform[1] <= 0.0 or m.transform[5] >= 0.0:
                raise RasterAlignmentError(
                    f"Invalid transform orientation in {label}: pixel_width must be > 0 (got {m.transform[1]}) "
                    f"and pixel_height must be < 0 (got {m.transform[5]})."
                )

    # 5. Resolution Matching Validation
    if meta_n is not None and meta_s is not None:
        diff_res_x = abs(meta_n.transform[1] - meta_s.transform[1])
        diff_res_y = abs(meta_n.transform[5] - meta_s.transform[5])
        if diff_res_x > transform_tolerance or diff_res_y > transform_tolerance:
            raise RasterAlignmentError(
                f"Resolution mismatch: North slice pixel size ({meta_n.transform[1]:.4f}, {meta_n.transform[5]:.4f}) "
                f"!= South slice pixel size ({meta_s.transform[1]:.4f}, {meta_s.transform[5]:.4f})."
            )
        diff_meta_rx = abs(meta_n.resolution_meters[0] - meta_s.resolution_meters[0])
        diff_meta_ry = abs(meta_n.resolution_meters[1] - meta_s.resolution_meters[1])
        if diff_meta_rx > transform_tolerance or diff_meta_ry > transform_tolerance:
            raise RasterAlignmentError(
                f"Resolution meters mismatch: North {meta_n.resolution_meters} != South {meta_s.resolution_meters}."
            )

    px_w = active_metas[0].transform[1]
    px_h = abs(active_metas[0].transform[5])

    # 6. Master Grid Resolution & Orientation Validation
    if master_grid is not None:
        if abs(master_grid.transform[2]) > transform_tolerance or abs(master_grid.transform[4]) > transform_tolerance:
            raise RasterAlignmentError(
                f"Master grid contains rotation/shear terms (c={master_grid.transform[2]}, e={master_grid.transform[4]})."
            )
        if abs(master_grid.transform[1] - px_w) > transform_tolerance or abs(abs(master_grid.transform[5]) - px_h) > transform_tolerance:
            raise RasterAlignmentError(
                f"Resolution mismatch with master grid: master grid pixel size is "
                f"({master_grid.transform[1]:.4f}, {master_grid.transform[5]:.4f}), while slice pixel size is "
                f"({px_w:.4f}, {-px_h:.4f})."
            )

    # 7. Grid Phase / Sub-pixel Alignment Verification
    # Ensure all pixel origins lie on integer multiples of (px_w, px_h) relative to reference
    ref_grid = master_grid if master_grid is not None else active_metas[0]
    ref_x0 = ref_grid.transform[0]
    ref_y0 = ref_grid.transform[3]

    for m, label in zip((meta_n, meta_s), ("North slice", "South slice")):
        if m is not None:
            col_shift = (m.transform[0] - ref_x0) / px_w
            row_shift = (ref_y0 - m.transform[3]) / px_h

            frac_col = abs(col_shift - round(col_shift))
            frac_row = abs(row_shift - round(row_shift))

            if frac_col > transform_tolerance:
                raise RasterAlignmentError(
                    f"Grid phase mismatch in {label}: X-origin {m.transform[0]:.4f} is shifted by "
                    f"{frac_col:.4f} fractional pixels relative to reference grid ({ref_x0:.4f}). "
                    f"Silent resampling or coordinate shifting is strictly forbidden."
                )
            if frac_row > transform_tolerance:
                raise RasterAlignmentError(
                    f"Grid phase mismatch in {label}: Y-origin {m.transform[3]:.4f} is shifted by "
                    f"{frac_row:.4f} fractional pixels relative to reference grid ({ref_y0:.4f}). "
                    f"Silent resampling or coordinate shifting is strictly forbidden."
                )

    # 8. North vs South Spatial Relationship Analysis
    gap_detected = False
    gap_rows = 0
    gap_distance_meters = 0.0
    overlap_detected = False
    overlap_rows = 0

    if meta_n is not None and meta_s is not None:
        y_top_n = meta_n.transform[3]
        y_bottom_n = y_top_n + meta_n.transform[5] * meta_n.shape[0]  # transform[5] is negative

        y_top_s = meta_s.transform[3]
        y_bottom_s = y_top_s + meta_s.transform[5] * meta_s.shape[0]

        # Inverted slice verification
        if y_top_n < y_top_s:
            raise SliceAssemblyError(
                f"Inverted slice order: North slice top ({y_top_n:.2f}) is south of South slice top ({y_top_s:.2f}). "
                f"Slices must be ordered North to South."
            )

        # Along-track boundary evaluation:
        # Distance = y_top_s - y_bottom_n
        # If distance < 0: North bottom is higher than South top -> GAP exists!
        # If distance > 0: South top is higher than North bottom -> OVERLAP exists!
        # If distance == 0: Perfect direct abutting adjacency.
        bound_diff_y = y_top_s - y_bottom_n
        bound_row_delta = bound_diff_y / px_h

        if abs(bound_row_delta) <= transform_tolerance:
            # Perfectly abutting
            gap_detected = False
            overlap_detected = False
        elif bound_diff_y < -transform_tolerance * px_h:
            # Unobserved void between North bottom and South top
            gap_detected = True
            gap_rows = int(round(abs(bound_diff_y) / px_h))
            gap_distance_meters = float(gap_rows * px_h)
            if raise_on_gap:
                raise SliceBoundaryGapError(
                    f"Along-track boundary gap detected: {gap_rows} unobserved row(s) "
                    f"({gap_distance_meters:.1f} meters) between North slice bottom ({y_bottom_n:.2f}) "
                    f"and South slice top ({y_top_s:.2f})."
                )
        else:
            # Overlap between North bottom and South top
            overlap_detected = True
            overlap_rows = int(round(bound_diff_y / px_h))

    # 9. Deduce Master Grid if not provided
    if master_grid is None:
        # Bounding box of all present slices
        x_min_all = min(m.transform[0] for m in active_metas)
        x_max_all = max(m.transform[0] + m.transform[1] * m.shape[1] for m in active_metas)
        y_max_all = max(m.transform[3] for m in active_metas)
        y_min_all = min(m.transform[3] + m.transform[5] * m.shape[0] for m in active_metas)

        m_width = int(round((x_max_all - x_min_all) / px_w))
        m_height = int(round((y_max_all - y_min_all) / px_h))
        m_transform = (x_min_all, px_w, 0.0, y_max_all, 0.0, -px_h)

        master_grid = AlignmentMetadata(
            shape=(m_height, m_width),
            crs=ref_crs,
            transform=m_transform,
            resolution_meters=(px_w, px_h),
        )

    # 10. Allocate Master Output Array (NaN initialized)
    master_h, master_w = master_grid.shape
    master_x0 = master_grid.transform[0]
    master_y0 = master_grid.transform[3]
    master_data = np.full((master_h, master_w), np.nan, dtype=np.float32)

    # Helper function to place a slice into master array
    def _place_slice_on_master(
        slice_arr: np.ndarray,
        slice_meta: AlignmentMetadata,
        slice_nodata: float | None,
        overwrite_existing: bool,
    ) -> tuple[int, int]:
        """Places a slice on the master grid, returning (valid_assigned_count, overlap_count)."""
        r_offset = int(round((master_y0 - slice_meta.transform[3]) / px_h))
        c_offset = int(round((slice_meta.transform[0] - master_x0) / px_w))

        # Master grid bounding window
        r_dst_start = max(0, r_offset)
        r_dst_end = min(master_h, r_offset + slice_meta.shape[0])
        c_dst_start = max(0, c_offset)
        c_dst_end = min(master_w, c_offset + slice_meta.shape[1])

        # Slice source bounding window
        r_src_start = r_dst_start - r_offset
        r_src_end = r_src_start + (r_dst_end - r_dst_start)
        c_src_start = c_dst_start - c_offset
        c_src_end = c_src_start + (c_dst_end - c_dst_start)

        if r_dst_start >= r_dst_end or c_dst_start >= c_dst_end:
            # Slice falls entirely outside master grid window
            return 0, 0

        sub_src = slice_arr[r_src_start:r_src_end, c_src_start:c_src_end].astype(np.float32)
        valid_src = np.isfinite(sub_src)
        if slice_nodata is not None:
            valid_src &= ~np.isclose(sub_src, slice_nodata, equal_nan=True)

        dst_sub = master_data[r_dst_start:r_dst_end, c_dst_start:c_dst_end]
        overlap_mask = valid_src & np.isfinite(dst_sub)
        num_overlap = int(np.count_nonzero(overlap_mask))

        if overwrite_existing:
            # Deterministic Assignment: Overwrite with valid pixels
            dst_sub[valid_src] = sub_src[valid_src]
        else:
            # Only assign where destination is not already valid
            assign_mask = valid_src & ~np.isfinite(dst_sub)
            dst_sub[assign_mask] = sub_src[assign_mask]

        num_assigned = int(np.count_nonzero(valid_src))
        return num_assigned, num_overlap

    # 11. Spatial Assignment
    # First place North slice (initial baseline for its region)
    num_assigned_n = 0
    if arr_n is not None and meta_n is not None:
        num_assigned_n, _ = _place_slice_on_master(
            arr_n, meta_n, nodata_n, overwrite_existing=True
        )

    # Second place South slice:
    # Deterministic Line Assignment: South slice takes precedence over North slice in any overlap
    # Overlap feathering / averaging is strictly avoided.
    num_assigned_s = 0
    num_overlap_pixels = 0
    if arr_s is not None and meta_s is not None:
        num_assigned_s, num_overlap_pixels = _place_slice_on_master(
            arr_s, meta_s, nodata_s, overwrite_existing=True
        )

    # 12. Seamline Continuity Audit
    seamline_continuity = True
    if meta_n is not None and meta_s is not None and not gap_detected:
        # Check the boundary seam: bottom row of North slice
        seam_r_master = int(round((master_y0 - meta_s.transform[3]) / px_h))
        if 0 <= seam_r_master < master_h:
            seam_row = master_data[seam_r_master, :]
            # If both slices covered this X span, check that there are no unexpected NaNs
            c_start = max(
                int(round((meta_n.transform[0] - master_x0) / px_w)),
                int(round((meta_s.transform[0] - master_x0) / px_w)),
            )
            c_end = min(
                int(round((meta_n.transform[0] + meta_n.transform[1] * meta_n.shape[1] - master_x0) / px_w)),
                int(round((meta_s.transform[0] + meta_s.transform[1] * meta_s.shape[1] - master_x0) / px_w)),
            )
            if c_end > c_start:
                seam_span = seam_row[c_start:c_end]
                # Check for completely blank row or excessive NaNs along the seam
                if np.all(np.isnan(seam_span)):
                    seamline_continuity = False

    # 13. Area and Pixel Accounting
    valid_pixel_count = int(np.count_nonzero(np.isfinite(master_data)))
    total_pixel_count = int(master_data.size)
    nodata_pixel_count = total_pixel_count - valid_pixel_count

    pixel_area_m2 = float(px_w * px_h)
    valid_area_km2 = float((valid_pixel_count * pixel_area_m2) / 1e6)
    total_area_km2 = float((total_pixel_count * pixel_area_m2) / 1e6)

    # Area conservation assertion:
    # valid_pixels_master must match num_assigned_n + num_assigned_s - num_overlap_pixels (within master window)
    expected_valid_pixels = num_assigned_n + num_assigned_s - num_overlap_pixels

    provenance: dict[str, Any] = {
        "assembly_method": "DIRECT_ABUTTING_ASSEMBLY",
        "crs": master_grid.crs,
        "master_shape": list(master_grid.shape),
        "north_slice_present": meta_n is not None,
        "south_slice_present": meta_s is not None,
        "is_partial": meta_n is None or meta_s is None,
        "missing_slice": "north" if meta_n is None else ("south" if meta_s is None else None),
        "north_slice_id": id_n,
        "south_slice_id": id_s,
        "north_slice_shape": list(meta_n.shape) if meta_n is not None else None,
        "south_slice_shape": list(meta_s.shape) if meta_s is not None else None,
        "gap_detected": bool(gap_detected),
        "gap_rows": int(gap_rows),
        "gap_distance_meters": float(gap_distance_meters),
        "overlap_detected": bool(overlap_detected),
        "overlap_rows": int(overlap_rows),
        "overlap_pixels": int(num_overlap_pixels),
        "seamline_continuity": bool(seamline_continuity),
        "valid_pixel_count": valid_pixel_count,
        "nodata_pixel_count": nodata_pixel_count,
        "expected_valid_pixel_count": expected_valid_pixels,
        "valid_area_km2": valid_area_km2,
        "total_area_km2": total_area_km2,
        "blending_applied": False,
        "resampling_applied": False,
    }

    return AssembledRaster(
        data=master_data,
        metadata=master_grid,
        provenance=provenance,
    )

