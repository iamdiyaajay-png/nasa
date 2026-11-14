"""
BHnMISnTRA: Member 1 Data & Scientific Intelligence
Typed Domain Exceptions.
"""


class ScientificError(Exception):
    """Base domain exception for BHnMISnTRA scientific pipeline."""
    pass


class AmbiguousCalibrationMetadataError(ScientificError):
    """Raised when product calibration state is ambiguous, missing, or contradictory."""
    pass


class IncompleteCalibrationProvenanceError(ScientificError):
    """Raised when required calibration documentation or provenance fields are missing."""
    pass


class GeometryMismatchError(ScientificError):
    """Raised when mandatory imaging geometry (band, mode, pol, look, orbit direction, track) differs."""
    pass


class MissingGeometryMetadataError(ScientificError):
    """Raised when mandatory geometry metadata is None or empty."""
    pass


class IncidenceAngleDivergenceError(ScientificError):
    """Raised when mid-swath incidence angle divergence exceeds configured tolerance."""
    pass


class UnavailableIncidenceAngleError(ScientificError):
    """Raised when incidence angle is unavailable and policy is FAIL_VALIDATION."""
    pass


class ExemptionTargetMismatchError(ScientificError):
    """Raised when an exemption target acquisition ID does not match the evaluating acquisition."""
    pass


class ContradictoryExemptionError(ScientificError):
    """Raised when an exemption is attached to a CLEAR confounder or invalid target."""
    pass


class InvalidBoundingBoxError(ScientificError):
    """Raised when bounding box coordinates violate geodetic bounds or ordinary ordering."""
    pass


class AntimeridianFlagMismatchError(ScientificError):
    """Raised when crosses_antimeridian flag contradicts coordinate values or signs."""
    pass


class DegenerateBoundingBoxError(ScientificError):
    """Raised when bounding box has zero or negative geographic span (e.g. 180 to -180 seam)."""
    pass


class DuplicateProductIdError(ScientificError):
    """Raised when identical product_id appears more than once in an investigation."""
    pass


class InsufficientAcquisitionsError(ScientificError):
    """Raised when fewer than 3 valid subsequent acquisitions are provided."""
    pass


class RasterAlignmentError(ScientificError):
    """Raised when raster shape, coordinate reference system, or affine transform differs."""
    pass


class ProcessingError(ScientificError):
    """Raised when scientific processing fails on invalid input or pipeline state."""
    pass


