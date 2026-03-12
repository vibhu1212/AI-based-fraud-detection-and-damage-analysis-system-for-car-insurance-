"""
Confidence Explanation API Endpoints
Provides explanations for AI confidence scores
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from enum import Enum

from app.models.base import get_db
from app.models.claim import Claim
from app.models.report import AIArtifact
from app.services.confidence_explainer import (
    confidence_explainer, 
    ModelType, 
    ConfidenceLevel
)

router = APIRouter(prefix="/explanations", tags=["explanations"])


class ModelTypeEnum(str, Enum):
    damage_detection = "damage_detection"
    damage_classification = "damage_classification"
    cost_estimation = "cost_estimation"
    fraud_detection = "fraud_detection"
    image_quality = "image_quality"
    vin_ocr = "vin_ocr"


class ExplanationResponse(BaseModel):
    score: float
    level: str
    summary: str
    factors: list
    recommendations: list
    alternatives: list
    model_type: str
    model_version: str


class QuickExplanationResponse(BaseModel):
    level: str
    summary: str
    color: str


@router.get("/claim/{claim_id}", response_model=dict)
async def get_claim_explanations(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all confidence explanations for a claim's AI results.
    Returns explanations for quality gate, damage detection, cost estimation, and fraud check.
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    explanations = {}
    
    # Get AI artifacts for this claim
    artifacts = db.query(AIArtifact).filter(
        AIArtifact.claim_id == claim_id
    ).all()
    
    # Quality gate explanation
    quality_artifact = next(
        (a for a in artifacts if a.artifact_type == "quality_gate_result"), 
        None
    )
    if quality_artifact and quality_artifact.artifact_json:
        avg_score = quality_artifact.artifact_json.get("average_score", 0.85)
        explanation = confidence_explainer.explain(
            ModelType.IMAGE_QUALITY,
            avg_score,
            quality_artifact.artifact_json
        )
        explanations["quality_gate"] = confidence_explainer.to_dict(explanation)
    
    # VIN OCR explanation
    vin_artifact = next(
        (a for a in artifacts if a.artifact_type == "vin_ocr_result"),
        None
    )
    if vin_artifact and vin_artifact.artifact_json:
        vin_score = vin_artifact.artifact_json.get("confidence", 0.8) / 100
        explanation = confidence_explainer.explain(
            ModelType.VIN_OCR,
            vin_score,
            vin_artifact.artifact_json
        )
        explanations["vin_ocr"] = confidence_explainer.to_dict(explanation)
    
    # Damage detection explanation
    damage_artifact = next(
        (a for a in artifacts if a.artifact_type == "damage_detection_result"),
        None
    )
    if damage_artifact and damage_artifact.artifact_json:
        damages = damage_artifact.artifact_json.get("damages", [])
        if damages:
            avg_conf = sum(d.get("confidence", 0.7) for d in damages) / len(damages)
            explanation = confidence_explainer.explain(
                ModelType.DAMAGE_DETECTION,
                avg_conf,
                {"damage_count": len(damages), "damages": damages}
            )
            explanations["damage_detection"] = confidence_explainer.to_dict(explanation)
    
    # Cost estimation explanation
    cost_artifact = next(
        (a for a in artifacts if a.artifact_type == "cost_estimation_result"),
        None
    )
    if cost_artifact and cost_artifact.artifact_json:
        cost_score = cost_artifact.artifact_json.get("confidence", 0.75)
        explanation = confidence_explainer.explain(
            ModelType.COST_ESTIMATION,
            cost_score,
            cost_artifact.artifact_json
        )
        explanations["cost_estimation"] = confidence_explainer.to_dict(explanation)
    
    # Fraud detection explanation
    fraud_artifact = next(
        (a for a in artifacts if a.artifact_type == "fraud_detection_result"),
        None
    )
    if fraud_artifact and fraud_artifact.artifact_json:
        fraud_score = fraud_artifact.artifact_json.get("similarity_score", 0.1)
        explanation = confidence_explainer.explain(
            ModelType.FRAUD_DETECTION,
            fraud_score,
            fraud_artifact.artifact_json
        )
        explanations["fraud_detection"] = confidence_explainer.to_dict(explanation)
    
    return {
        "claim_id": claim_id,
        "explanations": explanations
    }


@router.get("/damage/{damage_id}", response_model=ExplanationResponse)
async def get_damage_explanation(
    damage_id: str,
    model_type: ModelTypeEnum = ModelTypeEnum.damage_classification,
    db: Session = Depends(get_db)
):
    """
    Get confidence explanation for a specific damage detection.
    """
    # Find damage in AI artifacts
    artifacts = db.query(AIArtifact).filter(
        AIArtifact.artifact_type == "damage_detection_result"
    ).all()
    
    damage_data = None
    for artifact in artifacts:
        if artifact.artifact_json:
            damages = artifact.artifact_json.get("damages", [])
            for damage in damages:
                if damage.get("id") == damage_id:
                    damage_data = damage
                    break
            if damage_data:
                break
    
    if not damage_data:
        raise HTTPException(status_code=404, detail="Damage not found")
    
    # Generate explanation
    score = damage_data.get("confidence", 0.75)
    explanation = confidence_explainer.explain(
        ModelType(model_type.value),
        score,
        damage_data
    )
    
    return confidence_explainer.to_dict(explanation)


@router.get("/quick", response_model=QuickExplanationResponse)
async def get_quick_explanation(
    score: float = Query(..., ge=0.0, le=1.0),
    model_type: ModelTypeEnum = ModelTypeEnum.damage_detection
):
    """
    Get a quick one-line explanation for a confidence score.
    Useful for tooltips and inline displays.
    """
    level = confidence_explainer.get_confidence_level(score)
    summary = confidence_explainer.generate_summary(
        ModelType(model_type.value),
        level
    )
    
    # Determine color
    color_map = {
        ConfidenceLevel.VERY_HIGH: "#22c55e",  # green
        ConfidenceLevel.HIGH: "#84cc16",       # lime
        ConfidenceLevel.MODERATE: "#eab308",   # yellow
        ConfidenceLevel.LOW: "#f97316",        # orange
        ConfidenceLevel.VERY_LOW: "#ef4444"    # red
    }
    
    return {
        "level": level.value,
        "summary": summary,
        "color": color_map.get(level, "#94a3b8")
    }


@router.post("/generate")
async def generate_explanation(
    score: float = Query(..., ge=0.0, le=1.0),
    model_type: ModelTypeEnum = ModelTypeEnum.damage_detection,
    context: Optional[dict] = None
):
    """
    Generate a custom explanation for any confidence score.
    Useful for testing and custom integrations.
    """
    explanation = confidence_explainer.explain(
        ModelType(model_type.value),
        score,
        context
    )
    
    return confidence_explainer.to_dict(explanation)
