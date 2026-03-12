# Database models package
from app.models.base import Base, get_db, engine
from app.models.enums import (
    UserRole,
    ClaimStatus,
    RiskLevel,
    MediaType,
    CaptureAngle,
    DamageType,
    SeverityLevel,
    RepairAction
)
from app.models.user import User
from app.models.policy import Policy
from app.models.claim import Claim, ClaimStateTransition
from app.models.metrics import ProcessMetric
from app.models.media import MediaAsset, QualityGateResult
from app.models.damage import DamageDetection, DuplicateCheckResult
from app.models.icve import ICVEEstimate, ICVELineItem
from app.models.report import ReportDraft, AIArtifact
from app.models.audit import AuditEvent, RiskAssessment

__all__ = [
    "Base",
    "get_db",
    "engine",
    "UserRole",
    "ClaimStatus",
    "RiskLevel",
    "MediaType",
    "CaptureAngle",
    "DamageType",
    "SeverityLevel",
    "RepairAction",
    "User",
    "Policy",
    "Claim",
    "ClaimStateTransition",
    "MediaAsset",
    "QualityGateResult",
    "DamageDetection",
    "DuplicateCheckResult",
    "ICVEEstimate",
    "ICVELineItem",
    "ReportDraft",
    "AIArtifact",
    "AuditEvent",
    "RiskAssessment",
]

