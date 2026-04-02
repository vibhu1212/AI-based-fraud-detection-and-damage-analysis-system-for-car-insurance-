"""
M7 — Report Generator Service (Template-Based)
Generates structured JSON + annotated image reports from pipeline outputs.
VLM integration deferred to later phase.
"""
import cv2
import numpy as np
import json
import logging
import time
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Template-based survey report generator.
    Takes all module outputs and produces:
    1. Structured JSON report
    2. Annotated damage overlay image
    3. Summary text
    """

    def __init__(self):
        self.version = "1.0.0"

    def generate(
        self,
        image: np.ndarray,
        quality_gate: Dict[str, Any],
        vehicle_id: Dict[str, Any],
        parts: List[Dict],
        damages: List[Dict],
        severity: Dict[str, Any],
        cost_estimate: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a complete survey report.

        Returns:
            Dict with:
                report_json: structured report
                annotated_image_b64: damage overlay image
                summary_text: human-readable summary
                generated_at: timestamp
        """
        start = time.time()

        # 1. Generate annotated image with damage overlays
        annotated_b64 = self._generate_annotated_image(image, damages, parts)

        # 2. Build structured report
        report = self._build_report(
            quality_gate=quality_gate,
            vehicle_id=vehicle_id,
            parts=parts,
            damages=damages,
            severity=severity,
            cost_estimate=cost_estimate,
        )

        # 3. Generate human-readable summary
        summary = self._generate_summary(damages, severity, cost_estimate, vehicle_id)

        elapsed = round((time.time() - start) * 1000)

        return {
            "report_json": report,
            "annotated_image_b64": annotated_b64,
            "summary_text": summary,
            "report_version": self.version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "inference_time_ms": elapsed,
        }

    def _generate_annotated_image(
        self,
        image: np.ndarray,
        damages: List[Dict],
        parts: List[Dict],
    ) -> str:
        """Draw damage bounding boxes and labels on the image."""
        annotated = image.copy()
        h, w = annotated.shape[:2]

        # Color map for damage types
        colors = {
            "dent": (0, 165, 255),       # orange
            "scratch": (0, 255, 255),     # yellow
            "crack": (0, 0, 255),         # red
            "shatter": (0, 0, 200),       # dark red
            "deformation": (255, 0, 255), # magenta
            "paint_damage": (255, 255, 0),# cyan
            "glass_damage": (255, 0, 0),  # blue
        }
        default_color = (128, 128, 128)

        # Draw damage boxes
        for i, dmg in enumerate(damages):
            bbox = dmg.get("bounding_box", [])
            if len(bbox) < 4:
                continue

            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            damage_type = dmg.get("damage_type", "unknown")
            severity = dmg.get("severity", "unknown")
            confidence = dmg.get("confidence", 0)

            color = colors.get(damage_type, default_color)

            # Draw box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Draw label background
            label = f"{damage_type} ({severity}) {confidence:.0%}"
            font_scale = 0.5
            thickness = 1
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)

        # Draw severity banner at top
        severity_text = f"Damages: {len(damages)}"
        cv2.rectangle(annotated, (0, 0), (w, 35), (0, 0, 0), -1)
        cv2.putText(annotated, severity_text, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Encode to base64
        _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return base64.b64encode(buf.tobytes()).decode('utf-8')

    def _build_report(
        self,
        quality_gate: Dict,
        vehicle_id: Dict,
        parts: List[Dict],
        damages: List[Dict],
        severity: Dict,
        cost_estimate: Dict,
    ) -> Dict[str, Any]:
        """Build the structured JSON report."""
        return {
            "report_type": "AI Survey Report",
            "version": self.version,
            "generated_at": datetime.now(timezone.utc).isoformat(),

            "sections": [
                {
                    "title": "Image Quality Assessment",
                    "module": "M0",
                    "data": {
                        "passed": quality_gate.get("passed", quality_gate.get("status") == "passed"),
                        "blur_score": quality_gate.get("blur_score"),
                        "exposure_score": quality_gate.get("exposure_score"),
                        "pii_found": quality_gate.get("pii_found", False),
                        "faces_detected": quality_gate.get("faces_detected", 0),
                        "plates_detected": quality_gate.get("plates_detected", 0),
                    },
                },
                {
                    "title": "Vehicle Identification",
                    "module": "M2",
                    "data": {
                        "vehicle_type": vehicle_id.get("vehicle_type") or vehicle_id.get("display_name"),
                        "confidence": vehicle_id.get("confidence"),
                        "raw_class": vehicle_id.get("raw_class"),
                    },
                },
                {
                    "title": "Part Detection",
                    "module": "M3",
                    "data": {
                        "parts_detected": len(parts),
                        "parts": [
                            {"name": p.get("name"), "confidence": p.get("confidence")}
                            for p in parts[:10] if isinstance(p, dict)
                        ],
                    },
                },
                {
                    "title": "Damage Assessment",
                    "module": "M4",
                    "data": {
                        "total_damages": len(damages),
                        "severity_level": severity.get("severity_level", "unknown"),
                        "severity_score": severity.get("severity_score", 0),
                        "total_area_percentage": severity.get("total_area_percentage", 0),
                        "damages": [
                            {
                                "type": d.get("damage_type"),
                                "severity": d.get("severity"),
                                "part": d.get("part"),
                                "confidence": d.get("confidence"),
                                "area_pct": d.get("area_percentage"),
                            }
                            for d in damages
                        ],
                    },
                },
                {
                    "title": "Cost Estimation",
                    "module": "M6",
                    "data": cost_estimate,
                },
            ],

            "overall_assessment": {
                "severity_level": severity.get("severity_level", "unknown"),
                "severity_score": severity.get("severity_score", 0),
                "damage_count": len(damages),
                "estimated_cost": cost_estimate.get("total_estimate",
                                   cost_estimate.get("breakdown", {}).get("claim_settlement_estimate", 0)),
                "critical_parts": severity.get("critical_parts_affected", []),
            },
        }

    def _generate_summary(
        self,
        damages: List[Dict],
        severity: Dict,
        cost_estimate: Dict,
        vehicle_id: Dict,
    ) -> str:
        """Generate a human-readable text summary."""
        vehicle_type = (vehicle_id.get("vehicle_type") or
                        vehicle_id.get("display_name") or "vehicle")

        severity_level = severity.get("severity_level", "unknown")
        damage_count = len(damages)

        # Count damage types
        type_counts: Dict[str, int] = {}
        for d in damages:
            dt = d.get("damage_type", "unknown")
            type_counts[dt] = type_counts.get(dt, 0) + 1

        damage_desc = ", ".join(f"{count} {dtype}(s)" for dtype, count in type_counts.items())

        # Cost
        total_cost = cost_estimate.get("total_estimate",
                      cost_estimate.get("breakdown", {}).get("claim_settlement_estimate", 0))

        lines = [
            f"AI Survey Report — {vehicle_type.title()}",
            f"",
            f"Overall Severity: {severity_level.upper()}",
            f"Damages detected: {damage_count} ({damage_desc})",
            f"Total damage area: {severity.get('total_area_percentage', 0):.1f}%",
        ]

        if total_cost:
            lines.append(f"Estimated repair cost: ₹{total_cost:,.0f}")

        critical = severity.get("critical_parts_affected", [])
        if critical:
            lines.append(f"Critical parts affected: {', '.join(critical)}")

        lines.append(f"")
        lines.append(f"Note: This is an AI-generated preliminary assessment.")
        lines.append(f"Final evaluation requires human surveyor review.")

        return "\n".join(lines)
