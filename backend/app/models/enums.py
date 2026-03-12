"""
Database enums for type safety and constraints.
"""
import enum


class UserRole(str, enum.Enum):
    """User role enumeration."""
    CUSTOMER = "CUSTOMER"
    SURVEYOR = "SURVEYOR"
    ADMIN = "ADMIN"


class ClaimStatus(str, enum.Enum):
    """Claim status state machine."""
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    ANALYZING = "ANALYZING"
    NEEDS_RESUBMIT = "NEEDS_RESUBMIT"
    DRAFT_READY = "DRAFT_READY"
    SURVEYOR_REVIEW = "SURVEYOR_REVIEW"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RiskLevel(str, enum.Enum):
    """Risk level classification."""
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class MediaType(str, enum.Enum):
    """Media asset type."""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class CaptureAngle(str, enum.Enum):
    """Photo capture angle."""
    FRONT = "FRONT"
    REAR = "REAR"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    DASHBOARD = "DASHBOARD"
    DETAIL = "DETAIL"
    VIN = "VIN"


class DamageType(str, enum.Enum):
    """Damage classification types."""
    DENT = "DENT"
    SCRATCH = "SCRATCH"
    CRACK = "CRACK"
    GLASS_SHATTER = "GLASS_SHATTER"
    LAMP_BROKEN = "LAMP_BROKEN"
    TIRE_FLAT = "TIRE_FLAT"
    PAINT_CHIP = "PAINT_CHIP"
    RUST = "RUST"
    MISSING_PART = "MISSING_PART"
    OTHER = "OTHER"


class SeverityLevel(str, enum.Enum):
    """Damage severity classification."""
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class RepairAction(str, enum.Enum):
    """Recommended repair action."""
    REPAIR = "REPAIR"
    REPLACE = "REPLACE"
    PAINT = "PAINT"
    IGNORE = "IGNORE"
