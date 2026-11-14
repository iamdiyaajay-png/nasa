"""
BHnMISnTRA: Member 1 Data & Scientific Intelligence
Deeply Immutable Configuration Schemas, Models & Discriminated Unions.
"""

import math
from typing import Annotated, Any, Literal, Union
from pydantic import Field, model_validator

from .constants import PRD_CONSTANTS
from .enums import (
    CalibrationState,
    ConfounderCriticality,
    ConfounderState,
    ExemptionApprovalStatus,
    IncidenceAngleQuality,
    NotAssessedReason,
    UnavailableAnglePolicy,
)
from .exceptions import (
    AntimeridianFlagMismatchError,
    ContradictoryExemptionError,
    DegenerateBoundingBoxError,
    DuplicateProductIdError,
    GeometryMismatchError,
    IncompleteCalibrationProvenanceError,
    InsufficientAcquisitionsError,
    InvalidBoundingBoxError,
    MissingGeometryMetadataError,
)
from .types import (
    SafeCopyBaseModel,
    UtcDatetime,
    enforce_non_empty_str,
    enforce_strict_finite_float,
    enforce_strict_int,
)


# =============================================================================
# 1. CALIBRATION SCHEMAS & DISCRIMINATED UNION
# =============================================================================

class RawDnProvenance(SafeCopyBaseModel):
    calibration_source_doc: str
    lut_or_aux_file: str
    applied_scale: Literal["dn_squared", "digital_number"]
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for f in ("calibration_source_doc", "lut_or_aux_file"):
                if f in data:
                    data[f] = enforce_non_empty_str(data[f], f)
        return data


class CalibratedLinearProvenance(SafeCopyBaseModel):
    calibration_source_doc: str
    declared_linear_scale: Literal["sigma0", "gamma0", "beta0"]
    calibration_factor: float
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "calibration_source_doc" in data:
                data["calibration_source_doc"] = enforce_non_empty_str(data["calibration_source_doc"], "calibration_source_doc")
            if "calibration_factor" in data:
                val = enforce_strict_finite_float(data["calibration_factor"], "calibration_factor")
                if val <= 0.0:
                    raise ValueError(f"calibration_factor must be strictly positive (> 0.0), got {val}")
                data["calibration_factor"] = val
        return data


class CalibratedDbProvenance(SafeCopyBaseModel):
    calibration_source_doc: str
    decibel_reference_scale: Literal["10*log10(sigma0)", "10*log10(gamma0)", "10*log10(beta0)"]
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "calibration_source_doc" in data:
                data["calibration_source_doc"] = enforce_non_empty_str(data["calibration_source_doc"], "calibration_source_doc")
        return data


class RawDnCalibration(SafeCopyBaseModel):
    calibration_state: Literal[CalibrationState.RAW_DN] = CalibrationState.RAW_DN
    provenance: RawDnProvenance


class CalibratedLinearCalibration(SafeCopyBaseModel):
    calibration_state: Literal[CalibrationState.CALIBRATED_LINEAR_POWER] = CalibrationState.CALIBRATED_LINEAR_POWER
    provenance: CalibratedLinearProvenance


class CalibratedDbCalibration(SafeCopyBaseModel):
    calibration_state: Literal[CalibrationState.CALIBRATED_DB] = CalibrationState.CALIBRATED_DB
    provenance: CalibratedDbProvenance


CalibrationMetadata = Annotated[
    Union[RawDnCalibration, CalibratedLinearCalibration, CalibratedDbCalibration],
    Field(discriminator="calibration_state")
]


# =============================================================================
# 2. INCIDENCE ANGLE & EXEMPTION SCHEMAS
# =============================================================================

class IncidenceAngleExemption(SafeCopyBaseModel):
    exemption_id: str
    target_acquisition_id: str
    justification: str
    approved_by: str
    approval_status: ExemptionApprovalStatus
    timestamp_utc: UtcDatetime

    @model_validator(mode="before")
    @classmethod
    def validate_exemption(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for f in ("exemption_id", "target_acquisition_id", "approved_by"):
                if f in data:
                    data[f] = enforce_non_empty_str(data[f], f)
            if "justification" in data:
                clean = enforce_non_empty_str(data["justification"], "justification")
                if len(clean) < 10:
                    raise ValueError(f"justification must be substantive (>= 10 chars), got '{clean}'")
                data["justification"] = clean
        return data


class IncidenceAngleMetadata(SafeCopyBaseModel):
    quality: IncidenceAngleQuality
    angle_deg: float | None = None
    estimation_method: str | None = None
    unavailable_reason: str | None = None
    documented_limitation: str | None = None
    exemption: IncidenceAngleExemption | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_numeric_angle(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "angle_deg" in data and data["angle_deg"] is not None:
                data["angle_deg"] = enforce_strict_finite_float(data["angle_deg"], "angle_deg")
            for f in ("estimation_method", "unavailable_reason", "documented_limitation"):
                if f in data and data[f] is not None:
                    data[f] = enforce_non_empty_str(data[f], f)
        return data

    @model_validator(mode="after")
    def validate_quality_invariants(self) -> "IncidenceAngleMetadata":
        if self.quality == IncidenceAngleQuality.AVAILABLE:
            if self.angle_deg is None:
                raise ValueError("angle_deg is strictly required when quality is AVAILABLE")
            if not (10.0 <= self.angle_deg <= 70.0):
                raise ValueError(f"Incidence angle {self.angle_deg}° outside physical SAR range [10.0°, 70.0°]")
            if self.unavailable_reason is not None or self.estimation_method is not None:
                raise ValueError("unavailable_reason and estimation_method must be None when quality is AVAILABLE")

        elif self.quality == IncidenceAngleQuality.ESTIMATED:
            if self.angle_deg is None:
                raise ValueError("angle_deg is strictly required when quality is ESTIMATED")
            if not (10.0 <= self.angle_deg <= 70.0):
                raise ValueError(f"Estimated angle {self.angle_deg}° outside physical SAR range [10.0°, 70.0°]")
            if not self.estimation_method or not self.estimation_method.strip():
                raise ValueError("estimation_method is strictly required when quality is ESTIMATED")
            if self.unavailable_reason is not None:
                raise ValueError("unavailable_reason must be None when quality is ESTIMATED")

        elif self.quality == IncidenceAngleQuality.UNAVAILABLE:
            if self.angle_deg is not None:
                raise ValueError(f"angle_deg must be None when quality is UNAVAILABLE, got {self.angle_deg}")
            if self.estimation_method is not None:
                raise ValueError("estimation_method must be None when quality is UNAVAILABLE")
            if not self.unavailable_reason or not self.unavailable_reason.strip():
                raise ValueError("unavailable_reason is strictly required when quality is UNAVAILABLE")
            if not self.documented_limitation or not self.documented_limitation.strip():
                raise ValueError("documented_limitation is strictly required when quality is UNAVAILABLE")

        return self


# =============================================================================
# 3. SENSOR & ORBIT METADATA SCHEMAS
# =============================================================================

class SensorMetadata(SafeCopyBaseModel):
    mission: str
    sensor_name: str
    frequency_band: str
    sensor_mode: str
    polarization: str
    look_direction: str
    incidence_angle: IncidenceAngleMetadata

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for f in ("mission", "sensor_name", "frequency_band", "sensor_mode", "polarization", "look_direction"):
                if f in data:
                    data[f] = enforce_non_empty_str(data[f], f)
        return data


class OrbitParameters(SafeCopyBaseModel):
    orbit_direction: str
    relative_orbit: int
    pass_type: str = "exact_repeat"

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "orbit_direction" in data:
                data["orbit_direction"] = enforce_non_empty_str(data["orbit_direction"], "orbit_direction").lower()
            if "pass_type" in data:
                data["pass_type"] = enforce_non_empty_str(data["pass_type"], "pass_type")
            if "relative_orbit" in data:
                data["relative_orbit"] = enforce_strict_int(data["relative_orbit"], "relative_orbit")
        return data


class AcquisitionMetadata(SafeCopyBaseModel):
    product_id: str
    acquisition_utc: UtcDatetime
    sensor: SensorMetadata
    orbit: OrbitParameters
    calibration: CalibrationMetadata
    file_path: str

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for f in ("product_id", "file_path"):
                if f in data:
                    data[f] = enforce_non_empty_str(data[f], f)
        return data

    @model_validator(mode="after")
    def validate_exemption_target_binding(self) -> "AcquisitionMetadata":
        # Invariant: If an incidence angle exemption is present, its target ID must match product_id
        ex = self.sensor.incidence_angle.exemption
        if ex is not None and ex.target_acquisition_id != self.product_id:
            raise ValueError(
                f"Exemption target ID '{ex.target_acquisition_id}' does not match "
                f"acquisition product_id '{self.product_id}'"
            )
        return self


# =============================================================================
# 4. GEOGRAPHIC BOUNDING BOX SCHEMA
# =============================================================================

class BoundingBoxWGS84(SafeCopyBaseModel):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    crosses_antimeridian: bool

    @model_validator(mode="before")
    @classmethod
    def validate_raw(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for f in ("min_lon", "min_lat", "max_lon", "max_lat"):
                if f in data:
                    data[f] = enforce_strict_finite_float(data[f], f)
            if "crosses_antimeridian" in data:
                if type(data["crosses_antimeridian"]) is not bool:
                    raise ValueError(f"crosses_antimeridian must be a boolean, got {type(data['crosses_antimeridian']).__name__}")
        return data

    @model_validator(mode="after")
    def validate_geometry(self) -> "BoundingBoxWGS84":
        if not (-180.0 <= self.min_lon <= 180.0) or not (-180.0 <= self.max_lon <= 180.0):
            raise InvalidBoundingBoxError(f"Longitudes must lie within [-180.0, 180.0], got min={self.min_lon}, max={self.max_lon}")
        if not (-90.0 <= self.min_lat <= 90.0) or not (-90.0 <= self.max_lat <= 90.0):
            raise InvalidBoundingBoxError(f"Latitudes must lie within [-90.0, 90.0], got min={self.min_lat}, max={self.max_lat}")

        delta_lat = self.max_lat - self.min_lat
        if delta_lat <= 0.0:
            raise DegenerateBoundingBoxError(f"Latitude span must be strictly positive (min_lat < max_lat), got span={delta_lat}")

        if not self.crosses_antimeridian:
            delta_lon = self.max_lon - self.min_lon
            if delta_lon <= 0.0:
                raise InvalidBoundingBoxError(f"Ordinary bounding box requires min_lon < max_lon, got span={delta_lon}")
        else:
            if self.min_lon <= 0.0 or self.max_lon >= 0.0 or self.min_lon <= self.max_lon:
                raise AntimeridianFlagMismatchError(
                    f"Antimeridian box requires min_lon > 0 and max_lon < 0 with min_lon > max_lon, "
                    f"got min_lon={self.min_lon}, max_lon={self.max_lon}"
                )
            delta_lon = (180.0 - self.min_lon) + (self.max_lon - (-180.0))
            if delta_lon <= 0.0:
                raise DegenerateBoundingBoxError(f"Antimeridian box has degenerate zero or negative span: {delta_lon}")

        return self


# =============================================================================
# 5. THRESHOLD STRATEGY DISCRIMINATED UNION
# =============================================================================

class FixedDbThresholdConfig(SafeCopyBaseModel):
    strategy_name: Literal["fixed_db"] = "fixed_db"
    drop_threshold_db: float

    @model_validator(mode="before")
    @classmethod
    def validate_raw(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "drop_threshold_db" in data:
                val = enforce_strict_finite_float(data["drop_threshold_db"], "drop_threshold_db")
                if val >= 0.0:
                    raise ValueError(f"drop_threshold_db must be strictly negative dB (< 0.0), got {val}")
                data["drop_threshold_db"] = val
        return data


class RobustMadThresholdConfig(SafeCopyBaseModel):
    strategy_name: Literal["robust_mad"] = "robust_mad"
    k_multiplier: float

    @model_validator(mode="before")
    @classmethod
    def validate_raw(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "k_multiplier" in data:
                val = enforce_strict_finite_float(data["k_multiplier"], "k_multiplier")
                if val <= 0.0:
                    raise ValueError(f"k_multiplier must be strictly positive (> 0.0), got {val}")
                data["k_multiplier"] = val
        return data


class OtsuThresholdConfig(SafeCopyBaseModel):
    strategy_name: Literal["otsu"] = "otsu"
    num_histogram_bins: int
    clip_percentiles: tuple[float, float]

    @model_validator(mode="before")
    @classmethod
    def validate_raw(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "num_histogram_bins" in data:
                bins = enforce_strict_int(data["num_histogram_bins"], "num_histogram_bins")
                if bins < 2 or bins > 65536:
                    raise ValueError(f"num_histogram_bins must be an integer in [2, 65536], got {bins}")
                data["num_histogram_bins"] = bins
            if "clip_percentiles" in data:
                raw_p = data["clip_percentiles"]
                if not isinstance(raw_p, (list, tuple)) or len(raw_p) != 2:
                    raise ValueError("clip_percentiles must be a 2-tuple (p_min, p_max)")
                p0 = enforce_strict_finite_float(raw_p[0], "clip_percentiles[0]")
                p1 = enforce_strict_finite_float(raw_p[1], "clip_percentiles[1]")
                if not (0.0 <= p0 < p1 <= 100.0):
                    raise ValueError(f"clip_percentiles must satisfy 0.0 <= p_min < p_max <= 100.0, got ({p0}, {p1})")
                data["clip_percentiles"] = (p0, p1)
        return data


ThresholdConfig = Annotated[
    Union[FixedDbThresholdConfig, RobustMadThresholdConfig, OtsuThresholdConfig],
    Field(discriminator="strategy_name")
]


# =============================================================================
# 6. PIPELINE PARAMETERS SCHEMA (ZERO SILENT DEFAULTS)
# =============================================================================

class PipelineParameters(SafeCopyBaseModel):
    speckle_filter_name: Literal["boxcar", "lee"] = Field(...)
    speckle_window_size: int = Field(...)
    threshold_strategy: ThresholdConfig = Field(...)
    min_mapping_unit_pixels: int = Field(...)
    flood_growth_tolerance: float = Field(...)
    sustained_overlap_ratio: float = Field(...)
    min_spatial_coverage_ratio: float = Field(...)
    min_valid_pixel_ratio: float = Field(...)
    spatial_tuning_split_ratio: float = Field(...)
    max_incidence_angle_divergence_deg: float = Field(...)
    unavailable_incidence_angle_policy: UnavailableAnglePolicy = Field(...)

    @model_validator(mode="before")
    @classmethod
    def validate_numeric_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "speckle_window_size" in data:
                val = enforce_strict_int(data["speckle_window_size"], "speckle_window_size")
                if val < 3 or val % 2 == 0:
                    raise ValueError(f"speckle_window_size must be an odd positive integer >= 3, got {val}")
                data["speckle_window_size"] = val

            if "min_mapping_unit_pixels" in data:
                val = enforce_strict_int(data["min_mapping_unit_pixels"], "min_mapping_unit_pixels")
                if val < 1:
                    raise ValueError(f"min_mapping_unit_pixels must be an integer >= 1, got {val}")
                data["min_mapping_unit_pixels"] = val

            if "flood_growth_tolerance" in data:
                val = enforce_strict_finite_float(data["flood_growth_tolerance"], "flood_growth_tolerance")
                if not (0.0 <= val <= 1.0):
                    raise ValueError(f"flood_growth_tolerance must be in [0.0, 1.0], got {val}")
                data["flood_growth_tolerance"] = val

            for f in ("sustained_overlap_ratio", "min_spatial_coverage_ratio", "min_valid_pixel_ratio"):
                if f in data:
                    val = enforce_strict_finite_float(data[f], f)
                    if not (0.0 < val <= 1.0):
                        raise ValueError(f"{f} must be in (0.0, 1.0], got {val}")
                    data[f] = val

            if "spatial_tuning_split_ratio" in data:
                val = enforce_strict_finite_float(data["spatial_tuning_split_ratio"], "spatial_tuning_split_ratio")
                if not (0.0 < val < 1.0):
                    raise ValueError(f"spatial_tuning_split_ratio must be strictly in (0.0, 1.0), got {val}")
                data["spatial_tuning_split_ratio"] = val

            if "max_incidence_angle_divergence_deg" in data:
                val = enforce_strict_finite_float(data["max_incidence_angle_divergence_deg"], "max_incidence_angle_divergence_deg")
                if not (0.0 < val <= 45.0):
                    raise ValueError(f"max_incidence_angle_divergence_deg must be in (0.0, 45.0], got {val}")
                data["max_incidence_angle_divergence_deg"] = val

        return data


# =============================================================================
# 7. CONFOUNDER SCHEMAS
# =============================================================================

class ConfounderAssessmentSource(SafeCopyBaseModel):
    provider: str
    dataset_name: str
    url_or_doi: str
    window_start_utc: UtcDatetime
    window_end_utc: UtcDatetime

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for f in ("provider", "dataset_name", "url_or_doi"):
                if f in data:
                    data[f] = enforce_non_empty_str(data[f], f)
        return data

    @model_validator(mode="after")
    def validate_time_window(self) -> "ConfounderAssessmentSource":
        if self.window_start_utc >= self.window_end_utc:
            raise ValueError(
                f"window_start_utc ({self.window_start_utc}) must be strictly earlier than "
                f"window_end_utc ({self.window_end_utc})"
            )
        return self


class ConfounderExemption(SafeCopyBaseModel):
    exemption_id: str
    target_confounder_id: str
    justification: str
    approved_by: str
    approval_status: ExemptionApprovalStatus
    timestamp_utc: UtcDatetime

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for f in ("exemption_id", "target_confounder_id", "approved_by"):
                if f in data:
                    data[f] = enforce_non_empty_str(data[f], f)
            if "justification" in data:
                clean = enforce_non_empty_str(data["justification"], "justification")
                if len(clean) < 10:
                    raise ValueError(f"justification must be substantive (>= 10 chars), got '{clean}'")
                data["justification"] = clean
        return data


class ConfounderRecord(SafeCopyBaseModel):
    confounder_id: str
    name: str
    criticality: ConfounderCriticality
    state: ConfounderState
    description: str
    assessment_source: ConfounderAssessmentSource | None = None
    not_assessed_reason: NotAssessedReason | None = None
    threshold_applied: str | None = None
    observed_metric: float | None = None
    scientific_limitation: str | None = None
    exemption: ConfounderExemption | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for f in ("confounder_id", "name", "description"):
                if f in data:
                    data[f] = enforce_non_empty_str(data[f], f)
            if "threshold_applied" in data and data["threshold_applied"] is not None:
                data["threshold_applied"] = enforce_non_empty_str(data["threshold_applied"], "threshold_applied")
            if "scientific_limitation" in data and data["scientific_limitation"] is not None:
                data["scientific_limitation"] = enforce_non_empty_str(data["scientific_limitation"], "scientific_limitation")
            if "observed_metric" in data and data["observed_metric"] is not None:
                data["observed_metric"] = enforce_strict_finite_float(data["observed_metric"], "observed_metric")
        return data

    @model_validator(mode="after")
    def validate_invariants(self) -> "ConfounderRecord":
        if self.state in (ConfounderState.CLEAR, ConfounderState.FLAGGED):
            if self.assessment_source is None:
                raise ValueError(f"assessment_source is strictly required when state is {self.state}")
            if self.threshold_applied is None:
                raise ValueError(f"threshold_applied is strictly required when state is {self.state}")
            if self.not_assessed_reason is not None:
                raise ValueError(f"not_assessed_reason must be None when state is {self.state}")

        elif self.state == ConfounderState.NOT_ASSESSED:
            if self.not_assessed_reason is None:
                raise ValueError("not_assessed_reason is strictly required when state is NOT_ASSESSED")
            if self.scientific_limitation is None:
                raise ValueError("scientific_limitation is strictly required when state is NOT_ASSESSED")
            if self.assessment_source is not None:
                raise ValueError("assessment_source must be None when state is NOT_ASSESSED")

        if self.exemption is not None:
            if self.state == ConfounderState.CLEAR:
                raise ContradictoryExemptionError("Contradictory exemption: A confounder assessed as CLEAR cannot carry an exemption.")
            if self.criticality == ConfounderCriticality.NON_CRITICAL:
                raise ContradictoryExemptionError("Irrelevant exemption: Non-critical confounders do not block evaluation and cannot carry exemptions.")
            if self.exemption.target_confounder_id != self.confounder_id:
                raise ValueError(
                    f"Exemption target ID '{self.exemption.target_confounder_id}' does not match "
                    f"confounder_id '{self.confounder_id}'"
                )

        return self


# =============================================================================
# 8. TOP-LEVEL INVESTIGATION CONFIGURATION SCHEMA
# =============================================================================

class InvestigationConfig(SafeCopyBaseModel):
    investigation_id: str
    study_area_id: str
    bbox: BoundingBoxWGS84
    phenomenon_type: Literal["flood", "clearing", "landslide", "coastal"]
    expected_behavior: Literal["receding", "sustained"]
    reference_acquisition: AcquisitionMetadata
    comparison_acquisition: AcquisitionMetadata
    subsequent_acquisitions: tuple[AcquisitionMetadata, ...]
    parameters: PipelineParameters
    output_dir: str
    confounders: tuple[ConfounderRecord, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def validate_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for f in ("investigation_id", "study_area_id", "output_dir"):
                if f in data:
                    data[f] = enforce_non_empty_str(data[f], f)
            if "confounders" in data and isinstance(data["confounders"], (list, tuple)):
                data["confounders"] = tuple(data["confounders"])
            if "subsequent_acquisitions" in data:
                raw_seq = data["subsequent_acquisitions"]
                if not isinstance(raw_seq, (list, tuple)):
                    raise ValueError(f"subsequent_acquisitions must be a sequence, got {type(raw_seq).__name__}")
                if len(raw_seq) < PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED:
                    raise InsufficientAcquisitionsError(
                        f"InvestigationConfig requires at least {PRD_CONSTANTS.MIN_SUBSEQUENT_FOR_SUPPORTED} "
                        f"subsequent acquisitions, got {len(raw_seq)}"
                    )
                data["subsequent_acquisitions"] = tuple(raw_seq)
        return data

    @model_validator(mode="after")
    def validate_investigation_integrity(self) -> "InvestigationConfig":
        ref = self.reference_acquisition
        comp = self.comparison_acquisition
        all_acqs = (ref, comp) + self.subsequent_acquisitions

        # 1. Product ID Uniqueness
        seen_ids = set()
        for acq in all_acqs:
            if acq.product_id in seen_ids:
                raise DuplicateProductIdError(f"Duplicate product_id detected in sequence: {acq.product_id}")
            seen_ids.add(acq.product_id)

        # 2. Mandatory Geometry Compatibility Check
        ref_geom = (
            ref.sensor.frequency_band,
            ref.sensor.sensor_mode,
            ref.sensor.polarization,
            ref.sensor.look_direction,
            ref.orbit.orbit_direction,
            ref.orbit.relative_orbit,
        )
        for idx, acq in enumerate(all_acqs[1:], start=1):
            acq_geom = (
                acq.sensor.frequency_band,
                acq.sensor.sensor_mode,
                acq.sensor.polarization,
                acq.sensor.look_direction,
                acq.orbit.orbit_direction,
                acq.orbit.relative_orbit,
            )
            if any(val is None or val == "" for val in acq_geom):
                raise MissingGeometryMetadataError(f"Missing mandatory geometry metadata at index {idx} ({acq.product_id})")
            if acq_geom != ref_geom:
                raise GeometryMismatchError(
                    f"Geometry mismatch at acquisition index {idx} ({acq.product_id}) vs reference ({ref.product_id}): "
                    f"Expected {ref_geom}, got {acq_geom}"
                )

        return self

