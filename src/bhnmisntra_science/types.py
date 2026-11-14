"""
BHnMISnTRA: Member 1 Data & Scientific Intelligence
Strict Ingestion Types & UTC Datetime Normalization.
"""

from datetime import datetime, timezone
import math
from typing import Annotated, Any
from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer, model_validator


def enforce_strict_int(v: Any, field_name: str) -> int:
    """Strictly accepts only native int; rejects bool, float, string, None."""
    if type(v) is bool:
        raise ValueError(f"{field_name} must be a strict integer, got boolean: {v}")
    if isinstance(v, float):
        raise ValueError(f"{field_name} must be a strict integer, got float: {v}")
    if not isinstance(v, int):
        raise ValueError(f"{field_name} must be a strict integer, got {type(v).__name__}")
    return v


def enforce_strict_finite_float(v: Any, field_name: str) -> float:
    """Strictly accepts native float/int; rejects bool, strings, NaN, +Inf, -Inf."""
    if type(v) is bool:
        raise ValueError(f"{field_name} must be a strict float, got boolean: {v}")
    if not isinstance(v, (float, int)):
        raise ValueError(f"{field_name} must be a numeric float, got {type(v).__name__}")
    val = float(v)
    if not math.isfinite(val):
        raise ValueError(f"{field_name} must be a finite number, got: {val}")
    return val


def enforce_non_empty_str(v: Any, field_name: str) -> str:
    """Rejects non-strings, empty strings, and whitespace-only strings."""
    if not isinstance(v, str):
        raise ValueError(f"{field_name} must be a string, got {type(v).__name__}")
    clean = v.strip()
    if not clean:
        raise ValueError(f"{field_name} cannot be empty or whitespace-only")
    return clean


def parse_and_normalize_utc(v: Any) -> datetime:
    """
    Parses ISO strings or datetimes, normalizes to UTC, preserves microseconds.
    Rejects naive datetimes, malformed formats, and booleans.
    Does NOT perform global string replacements.
    """
    if type(v) is bool or v is None:
        raise ValueError(f"Datetime must be an ISO string or datetime object, got {type(v).__name__}")

    if isinstance(v, datetime):
        dt = v
    elif isinstance(v, str):
        s = v.strip()
        if not s:
            raise ValueError("Datetime string cannot be empty or whitespace-only")
        if s.endswith(("Z", "z")):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except Exception as e:
            raise ValueError(f"Malformed ISO-8601 timestamp string: '{v}'") from e
    else:
        raise ValueError(f"Expected datetime or ISO string, got {type(v).__name__}")

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Naive datetime rejected: '{v}'. Timestamps must be timezone-aware.")

    return dt.astimezone(timezone.utc)


def serialize_utc_z(dt: datetime) -> str:
    """Guarantees RFC 3339 / ISO-8601 formatting with trailing 'Z' and microsecond preservation."""
    dt_utc = dt.astimezone(timezone.utc)
    if dt_utc.microsecond != 0:
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


UtcDatetime = Annotated[
    datetime,
    BeforeValidator(parse_and_normalize_utc),
    PlainSerializer(serialize_utc_z, return_type=str)
]


class SafeCopyBaseModel(BaseModel):
    """
    Base model providing deep immutability and defensive shallow copying
    in mode='before' to prevent mutating caller-owned input dictionaries.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def defensive_copy_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return dict(data)
        return data

