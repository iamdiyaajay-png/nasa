"""
BHnMISnTRA: Member 1 Data & Scientific Intelligence
Domain Enumerations.
"""

from enum import Enum


class CalibrationState(str, Enum):
    RAW_DN = "raw_dn"
    CALIBRATED_LINEAR_POWER = "calibrated_linear_power"
    CALIBRATED_DB = "calibrated_db"


class IncidenceAngleQuality(str, Enum):
    AVAILABLE = "available"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"


class UnavailableAnglePolicy(str, Enum):
    EXCLUDE_FROM_BEAT_TEST = "exclude_from_beat_test"
    FLAG_AND_ALLOW_WITH_LIMITATION = "flag_and_allow_with_limitation"
    FAIL_VALIDATION = "fail_validation"


class ExemptionApprovalStatus(str, Enum):
    APPROVED = "approved"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"


class ConfounderState(str, Enum):
    CLEAR = "clear"
    FLAGGED = "flagged"
    NOT_ASSESSED = "not_assessed"


class ConfounderCriticality(str, Enum):
    CRITICAL = "critical"
    NON_CRITICAL = "non_critical"


class NotAssessedReason(str, Enum):
    DATA_UNAVAILABLE = "data_unavailable"
    OUT_OF_SPATIAL_SWATH = "out_of_spatial_swath"
    TEMPORAL_LAG = "temporal_lag"
    SENSOR_UNSUPPORTED = "sensor_unsupported"
    EXCLUDED_FROM_RUN_SCOPE = "excluded_from_run_scope"


class AngleComparisonOutcome(str, Enum):
    COMPLIANT = "compliant"
    COMPLIANT_WITH_ESTIMATE_WARNING = "compliant_with_estimate_warning"
    DIVERGENCE_EXEMPTED = "divergence_exempted"
    DIVERGENCE_VIOLATION = "divergence_violation"
    UNAVAILABLE_EXCLUDED = "unavailable_excluded"
    UNAVAILABLE_FLAGGED = "unavailable_flagged"
    UNAVAILABLE_FATAL_ERROR = "unavailable_fatal_error"


class PhenomenonType(str, Enum):
    FLOOD = "flood"
    CLEARING = "clearing"
    LANDSLIDE = "landslide"
    COASTAL = "coastal"


class ExpectedBehavior(str, Enum):
    RECEDING = "receding"
    SUSTAINED = "sustained"


class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    INCONCLUSIVE = "inconclusive"
    UNVERIFIED = "unverified"

