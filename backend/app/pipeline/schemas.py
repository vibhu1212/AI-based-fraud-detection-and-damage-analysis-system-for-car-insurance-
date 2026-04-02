"""
Shared Pipeline Schemas — Data structures passed between modules.
All schemas are JSON-serializable via Pydantic.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PartInfo(BaseModel):
    """A detected vehicle part."""
    name: str
    bounding_box: List[float] = Field(description="[x1, y1, x2, y2]")
    confidence: float = 0.0
    mask_path: Optional[str] = None


class DamageInfo(BaseModel):
    """A detected damage instance."""
    model_config = {"protected_namespaces": ()}

    damage_type: str  # dent, scratch, crack, shatter, deformation, paint_damage, glass_damage
    severity: str = "moderate"  # minor, moderate, severe, totalled
    severity_score: float = 0.5  # 0.0 - 1.0
    part: str = "unknown"
    bounding_box: List[float] = Field(default_factory=list, description="[x1, y1, x2, y2]")
    area_percentage: float = 0.0
    confidence: float = 0.0
    mask_path: Optional[str] = None
    model_source: str = "unknown"  # yolo, maskrcnn, ensemble, fallback


class SeverityInfo(BaseModel):
    """Severity assessment for overall damage."""
    severity_score: float = 0.0  # 0.0 - 1.0
    severity_level: str = "low"  # low, medium, high, critical
    damage_count: int = 0
    total_area_percentage: float = 0.0
    critical_parts_affected: List[str] = Field(default_factory=list)


class CostLineItem(BaseModel):
    """A single cost line item."""
    part: str
    damage_type: str
    repair_cost: float = 0.0
    replace_cost: float = 0.0
    recommended_action: str = "repair"  # repair, replace, repaint
    depreciation_pct: float = 0.0
    final_cost: float = 0.0
    source_citation: str = ""


class PipelineResult(BaseModel):
    """Unified result from the full pipeline."""
    claim_id: str = ""
    pipeline_version: str = "1.0.0"

    # Per-module outputs
    quality_gate: Dict[str, Any] = Field(default_factory=dict)
    vehicle_id: Dict[str, Any] = Field(default_factory=dict)
    parts: List[PartInfo] = Field(default_factory=list)
    damages: List[DamageInfo] = Field(default_factory=list)
    severity: SeverityInfo = Field(default_factory=SeverityInfo)
    cost: Dict[str, Any] = Field(default_factory=dict)
    report: Dict[str, Any] = Field(default_factory=dict)

    # Pipeline metadata
    modules_executed: List[str] = Field(default_factory=list)
    modules_skipped: List[str] = Field(default_factory=list)
    modules_failed: List[str] = Field(default_factory=list)
    total_time_ms: float = 0.0
    errors: List[str] = Field(default_factory=list)
