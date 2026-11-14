"""
BHnMISnTRA: Stage 1 Acceptance Test Fixtures.
ALL DATA DEFINED IN THIS MODULE IS SYNTHETIC FOR SOFTWARE VERIFICATION ONLY.
TAG: FIXTURE_SYNTHETIC — NOT REAL SATELLITE DATA.
"""

from datetime import datetime, timezone
from typing import Any

SYNTHETIC_PROVENANCE_BADGE = "FIXTURE_SYNTHETIC — NOT REAL SATELLITE DATA"


def get_synthetic_valid_raw_dn_provenance() -> dict[str, Any]:
    return {
        "calibration_source_doc": "ESA-S1-DOC-001",
        "lut_or_aux_file": "annotation/calibration/calibration-s1a-iw1-slc-vv.xml",
        "applied_scale": "dn_squared",
        "notes": SYNTHETIC_PROVENANCE_BADGE,
    }


def get_synthetic_valid_linear_provenance() -> dict[str, Any]:
    return {
        "calibration_source_doc": "ESA-S1-DOC-002",
        "declared_linear_scale": "sigma0",
        "calibration_factor": 1.0,
        "notes": SYNTHETIC_PROVENANCE_BADGE,
    }


def get_synthetic_valid_db_provenance() -> dict[str, Any]:
    return {
        "calibration_source_doc": "ESA-S1-DOC-003",
        "decibel_reference_scale": "10*log10(sigma0)",
        "notes": SYNTHETIC_PROVENANCE_BADGE,
    }


def get_synthetic_valid_acquisition(
    product_id: str = "S1A_IW_GRDH_SYNTH_001",
    utc_str: str = "2026-05-24T06:12:00Z",
    angle_deg: float = 38.5,
    track: int = 12,
    cal_state: str = "calibrated_db"
) -> dict[str, Any]:
    return {
        "product_id": product_id,
        "acquisition_utc": utc_str,
        "sensor": {
            "mission": "Sentinel-1A",
            "sensor_name": "C-SAR",
            "frequency_band": "C",
            "sensor_mode": "IW",
            "polarization": "VV",
            "look_direction": "right",
            "incidence_angle": {
                "quality": "available",
                "angle_deg": angle_deg,
                "estimation_method": None,
                "unavailable_reason": None,
                "documented_limitation": None,
                "exemption": None,
            },
        },
        "orbit": {
            "orbit_direction": "ascending",
            "relative_orbit": track,
            "pass_type": "exact_repeat",
        },
        "calibration": {
            "calibration_state": cal_state,
            "provenance": get_synthetic_valid_db_provenance() if cal_state == "calibrated_db" else get_synthetic_valid_linear_provenance(),
        },
        "file_path": f"/data/synthetic/{product_id}.tif",
    }


def get_synthetic_valid_parameters(strategy: str = "fixed_db") -> dict[str, Any]:
    if strategy == "fixed_db":
        threshold_cfg = {
            "strategy_name": "fixed_db",
            "drop_threshold_db": -3.5,
        }
    elif strategy == "robust_mad":
        threshold_cfg = {
            "strategy_name": "robust_mad",
            "k_multiplier": 2.5,
        }
    elif strategy == "otsu":
        threshold_cfg = {
            "strategy_name": "otsu",
            "num_histogram_bins": 256,
            "clip_percentiles": (1.0, 99.0),
        }
    else:
        raise ValueError(f"Unknown synthetic strategy: {strategy}")

    return {
        "speckle_filter_name": "boxcar",
        "speckle_window_size": 5,
        "threshold_strategy": threshold_cfg,
        "min_mapping_unit_pixels": 10,
        "flood_growth_tolerance": 0.05,
        "sustained_overlap_ratio": 0.50,
        "min_spatial_coverage_ratio": 0.95,
        "min_valid_pixel_ratio": 0.90,
        "spatial_tuning_split_ratio": 0.30,
        "max_incidence_angle_divergence_deg": 1.5,
        "unavailable_incidence_angle_policy": "flag_and_allow_with_limitation",
    }


def get_synthetic_valid_investigation_config() -> dict[str, Any]:
    ref_acq = get_synthetic_valid_acquisition("S1A_SYNTH_REF", "2026-05-12T06:12:00Z")
    comp_acq = get_synthetic_valid_acquisition("S1A_SYNTH_COMP", "2026-05-24T06:12:00Z")
    sub1 = get_synthetic_valid_acquisition("S1A_SYNTH_SUB1", "2026-06-05T06:12:00Z")
    sub2 = get_synthetic_valid_acquisition("S1A_SYNTH_SUB2", "2026-06-17T06:12:00Z")
    sub3 = get_synthetic_valid_acquisition("S1A_SYNTH_SUB3", "2026-06-29T06:12:00Z")

    return {
        "investigation_id": "INV-2026-SYNTH-001",
        "study_area_id": "AREA-SYNTH-KERALA",
        "bbox": {
            "min_lon": 76.2,
            "min_lat": 9.9,
            "max_lon": 76.5,
            "max_lat": 10.2,
            "crosses_antimeridian": False,
        },
        "phenomenon_type": "flood",
        "expected_behavior": "receding",
        "reference_acquisition": ref_acq,
        "comparison_acquisition": comp_acq,
        "subsequent_acquisitions": [sub1, sub2, sub3],
        "parameters": get_synthetic_valid_parameters(),
        "output_dir": "/outputs/synthetic/INV-2026-SYNTH-001",
    }

