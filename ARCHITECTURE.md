# AI Automated Insurance Survey Agent — Hybrid Pipeline Architecture

**Project:** AI Automated Insurance Survey Agent (TIH-IoT CHANAKYA Fellowship 2025)  
**Scope:** Modular ML tools / standalone models for integration into existing insurer systems  
**Architecture:** Custom Hybrid Pipeline — Best of 5 Paradigms  

---

## Design Philosophy

This hybrid pipeline combines the **strongest elements** from five distinct architectural paradigms into one cohesive, modular system:

| Element | Source Pipeline | What We Take |
|---------|---------------|--------------|
| **Sequential modular JSON I/O** | Pipeline 1 (Linear Chain) | Clean module interfaces, independent testability, REST API integration |
| **Dynamic routing & self-correction** | Pipeline 2 (LangGraph Agents) | Supervisor-based triage, retry loops, fraud escalation paths |
| **Knowledge-grounded decisions** | Pipeline 3 (RAG-Augmented) | Vector DB for policies, parts catalogs, historical fraud patterns |
| **Fast/Deep dual-track processing** | Pipeline 4 (Dual-Stream Triage) | Lightweight fast path for 80% of claims, heavy path for complex cases |
| **SOTA vs Scratch cross-training** | Pipeline 5 (Data Flywheel) | Dual-model benchmarking, knowledge distillation, active learning |

---

## Hybrid Pipeline — Full Architecture

```mermaid
flowchart TD
    INPUT([📱 Input: Multi-Photo Upload + Policy Metadata]) --> TRIAGE

    subgraph TRIAGE_LAYER ["🔀 Dynamic Triage Router"]
        TRIAGE[🎯 Claim Complexity Scorer\nMobileNetV3 + Rule Engine\nFeatures: image count · vehicle value · claim history]
        TRIAGE --> TRIAGE_DECISION{Complexity\nScore}
        TRIAGE_DECISION -->|"< 0.4 Simple"| FAST_TRACK
        TRIAGE_DECISION -->|"0.4-0.8 Complex"| FULL_TRACK
        TRIAGE_DECISION -->|"> 0.8 Critical"| FULL_TRACK_WITH_3D
    end

    subgraph M0 ["M0 — Privacy & Quality Gate"]
        QA[🔍 Image Quality Assessor\nEnhancedQualityGateValidator\nBlur · Exposure · Resolution]
        QA --> PII[🔒 PII Masking Engine\nYOLO11m person + YOLO11m_plates + Haar cascade\nGaussian blur 99x99 · DPDP Act 2023 Compliant]
    end

    subgraph M1 ["M1 — Forensics & Fraud Detection"]
        FRAUD_MAIN[🕵️ Deepfake & Tamper Detector\nCustom EfficientNet-B4 From Scratch\nGAN Fingerprint + EXIF Analysis]
        FRAUD_RAG[📚 Historical Fraud RAG Query\nVector DB: Similar fraud signatures\nContext-enriched fraud scoring]
        FRAUD_MAIN --> FRAUD_RAG
        FRAUD_RAG --> FRAUD_SCORE{Fraud Score}
        FRAUD_SCORE -->|"> 0.75"| ESCALATE[🚨 Human Escalation\nInterrupt + Fraud Report]
        FRAUD_SCORE -->|"≤ 0.75"| CONTINUE[✅ Continue]
    end

    subgraph M2 ["M2 — Vehicle Identification"]
        VEH_DETECT[🚗 Indian Vehicle Detector\nYOLOv10 Fine-tuned\nMake · Model · Year · Trim\n200+ Indian Models]
        VEH_RAG[📚 Vehicle Spec RAG Query\nVerify detected model vs policy\nFetch part geometries + depreciation]
        VEH_DETECT --> VEH_RAG
    end

    subgraph M3 ["M3 — Part Segmentation"]
        PART_SEG[🏷️ Part Segmentation Engine\nSegFormer-B5 Fine-tuned\nDoor · Hood · Bumper · Fender · Windshield\nDataset: CarDD + COCO-Vehicles + Custom]
    end

    subgraph M4 ["M4 — Damage Analysis (Dual-Model Cross-Training)"]
        SOTA_DMG[🏆 SOTA Path: Mask R-CNN\nFine-tuned on CarDD + Custom]
        SCRATCH_DMG[🔨 Research Path: Custom UNet\nFrom Scratch + Attention Mechanism]
        COMPARE[📊 Model Comparator\nmAP · IoU · F1 · Inference Time\nMLflow Tracking]
        SOTA_DMG --> COMPARE
        SCRATCH_DMG --> COMPARE
        COMPARE --> CROSS_TRAIN{Winner?}
        CROSS_TRAIN -->|"SOTA wins"| DISTILL[Knowledge Distillation\nSOTA teaches Scratch]
        CROSS_TRAIN -->|"Scratch wins"| ANOMALY[🌟 SOTA Blind Spot\nFlag for annotation]
        CROSS_TRAIN -->|"Near tie"| ENSEMBLE[Ensemble Prediction\nWeighted average]
        DISTILL --> DMG_OUT[Consensus Damage Map\n+ Severity Scores]
        ANOMALY --> DMG_OUT
        ENSEMBLE --> DMG_OUT
    end

    subgraph M5 ["M5 — 3D Depth Estimation (Optional)"]
        DEPTH_CHECK{Multi-view\nImages?}
        DEPTH_CHECK -->|"Yes 3+"| NERF[🌐 3D Gaussian Splatting\nInstant-NGP\nDamage Volume + Point Cloud]
        DEPTH_CHECK -->|"No"| MONO[📐 Custom Depth UNet\nFrom Scratch Monocular Depth\nFallback: MiDaS v3.1]
        NERF --> DEPTH_OUT[Depth-enriched Damage JSON\nVolume in cm³ · Depth in mm]
        MONO --> DEPTH_OUT
    end

    subgraph M6 ["M6 — ICVE Pricing Engine (Zero AI)"]
        ICVE[🧾 Rule-Based Cost Engine\nPart ID + Severity + Vehicle Age]
        PARTS_RAG[📚 Parts Catalog RAG\nOEM Prices + Aftermarket Options]
        LABOR_RAG[📚 Labor Rate RAG\nIRDAI-Approved Regional Rates]
        POLICY_RAG[📚 Policy Clause RAG\nDeductibles + Coverage Limits]
        ICVE --> PARTS_RAG
        PARTS_RAG --> LABOR_RAG
        LABOR_RAG --> POLICY_RAG
        POLICY_RAG --> COST_OUT[💰 Cost Breakdown\nPer-part: Repair/Replace/Depreciation\nTotal with Confidence Bounds\nEvery Price Cited to Source]
    end

    subgraph M7 ["M7 — Explainable Report Generator"]
        VLM[📝 VLM Report Generator\nInternVL2 / LLaVA-1.6 Fine-tuned\nImages + Damage JSON + Cost JSON + RAG Context]
        XAI[🔬 GRAD-CAM Overlay Generator\nDamage Region Heatmaps]
        CITE[✅ Citation Verifier\nAll facts traced to KB source\nZero hallucination guard]
        VLM --> XAI
        XAI --> CITE
        CITE --> REPORT_OUT[📋 Survey Report\nJSON + PDF\nAudit Hash · Timestamps · Model Versions]
    end

    subgraph RAG_KB ["📚 Insurance Knowledge Layer"]
        VECTOR_DB[(Vector Database\npgvector / Weaviate)]
        KB_POLICY[Insurance Policy Terms\nIRDAI Guidelines]
        KB_PARTS[OEM Parts Catalog\nPart Numbers + Prices]
        KB_FRAUD[Historical Fraud Patterns\nAnomaly Signatures]
        KB_LABOR[Labor Rate Cards\nRegional IRDAI Rates]
        KB_VEHICLE[Vehicle Spec DB\n200+ Indian Models]
        KB_POLICY --> VECTOR_DB
        KB_PARTS --> VECTOR_DB
        KB_FRAUD --> VECTOR_DB
        KB_LABOR --> VECTOR_DB
        KB_VEHICLE --> VECTOR_DB
    end

    subgraph ACTIVE_LEARNING ["🔄 Active Learning & Retraining Loop"]
        AL_QUEUE[🎯 Active Learning Engine\nUncertainty + Diversity Sampling]
        ANNOTATOR[👨‍🔬 Human Annotator\nLabel Studio / CVAT\n20-50 samples/week]
        DVC[📦 Dataset Versioner\nDVC - Full Data Lineage]
        TRAINER[🏋️ Model Trainer\nPyTorch Lightning + DeepSpeed]
        EVAL[📊 Automated Evaluation\nmAP · IoU · AUC on Holdout]
        DRIFT[📉 Drift Monitor\nEvidently AI / Alibi Detect]
        AL_QUEUE --> ANNOTATOR
        ANNOTATOR --> DVC
        DVC --> TRAINER
        TRAINER --> EVAL
        EVAL -->|"Better"| DEPLOY[Canary Deploy 10%]
        EVAL -->|"Worse"| ARCHIVE[Archive + Keep Current]
        DRIFT -->|"Bias Alert"| AL_QUEUE
    end

    FAST_TRACK --> M0
    FULL_TRACK --> M0
    FULL_TRACK_WITH_3D --> M0

    M0 --> M1
    M1 --> M2
    M2 --> M3
    M3 --> M4
    M4 -->|"Full Track"| M5
    M4 -->|"Fast Track"| M6
    M5 --> M6
    M6 --> M7

    M4 -.->|"Disagreement/Uncertainty"| AL_QUEUE
    M7 -.->|"Low VLM Confidence"| AL_QUEUE
    DEPLOY -.->|"Updated Models"| M4

    VECTOR_DB -.-> FRAUD_RAG
    VECTOR_DB -.-> VEH_RAG
    VECTOR_DB -.-> PARTS_RAG
    VECTOR_DB -.-> LABOR_RAG
    VECTOR_DB -.-> POLICY_RAG

    M7 --> HITL[👤 Human-in-the-Loop Review\nSurveyor / Underwriter Approval\nAll RAG Citations Visible]
    HITL --> FINAL([✅ Final Claim Decision\nApprove · Reject · Partial · Escalate])

    FINAL -.->|"Settlement Feedback"| CALIBRATION[(📊 Calibration DB\nEstimate vs Actual Delta)]
    CALIBRATION -.-> DRIFT

    style TRIAGE_LAYER fill:#1a0a2e,stroke:#f59e0b,color:#fff
    style M0 fill:#1a1a2e,stroke:#e94560,color:#fff
    style M1 fill:#16213e,stroke:#f5a623,color:#fff
    style M2 fill:#0f3460,stroke:#00b4d8,color:#fff
    style M3 fill:#1a1a2e,stroke:#06d6a0,color:#fff
    style M4 fill:#281a0a,stroke:#fbbf24,color:#fff
    style M5 fill:#16213e,stroke:#a855f7,color:#fff
    style M6 fill:#0f3460,stroke:#f72585,color:#fff
    style M7 fill:#1a1a2e,stroke:#4cc9f0,color:#fff
    style RAG_KB fill:#0a1628,stroke:#818cf8,color:#fff
    style ACTIVE_LEARNING fill:#1a1a0a,stroke:#f97316,color:#fff
```

---

## Module Specifications

### M0 — Privacy & Quality Gate

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Filter low-quality images; mask PII for DPDP/IRDAI compliance |
| **Input** | Raw images (JPEG/PNG), `List[UploadFile]` — all images processed per request |
| **Output** | `{ quality_score, blur_score, exposure_score, passed, pii_found, faces_detected, plates_detected, faces_boxes, plates_boxes, redacted_image_b64 }` |
| **Models** | `EnhancedQualityGateValidator` (quality), YOLO11m class 0 conf=0.45 (person/face), YOLO11m_plates conf=0.3 + Haar cascade union (plates) |
| **Redaction** | Gaussian blur 99×99 on top 35% of person bbox (head) and full plate bbox |
| **Build Type** | Fine-tuned + Custom |
| **Status** | ✅ Implemented |
| **Track** | Both Fast and Deep |

### M1 — Forensics & Fraud Detection

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Detect manipulated/deepfaked images; flag suspicious claims |
| **Input** | Sanitized images, EXIF metadata |
| **Output** | `{ fraud_score, fraud_type, exif_analysis, rag_similar_frauds[], escalation_required }` |
| **Models** | Custom EfficientNet-B4 (from scratch), EXIF analyzer, RAG fraud pattern retriever |
| **Build Type** | From Scratch (research model) |
| **Track** | Deep only (Fast Track skips this) |
| **Innovation** | RAG-grounded historical fraud comparison from Pipeline 3 |

### M2 — Vehicle Identification

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Identify Indian vehicle make, model, year, trim level |
| **Input** | Sanitized images |
| **Output** | `{ make, model, year, trim, confidence, variant, body_type, policy_match_verified }` |
| **Models** | YOLOv10 fine-tuned (Deep), YOLOv10-Nano (Fast) |
| **Dataset** | Custom scraped: Maruti, Tata, Hyundai, Mahindra + CarDekho |
| **Build Type** | Fine-tuned SOTA |
| **Innovation** | RAG policy verification — detected vehicle cross-checked against policy DB |

### M3 — Part Segmentation

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Segment individual car parts for damage localization |
| **Input** | Sanitized images, vehicle identification JSON |
| **Output** | `{ parts[]: { name, mask, bounding_box, confidence } }` |
| **Models** | SegFormer-B5 fine-tuned |
| **Dataset** | CarDD + COCO-Vehicles + Custom annotated (40+ part classes) |
| **Build Type** | Fine-tuned SOTA |
| **Track** | Deep only (Fast Track uses bounding boxes from M2) |

### M4 — Damage Analysis (Dual-Model with Cross-Training)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Detect and classify damage; benchmark SOTA vs from-scratch models |
| **Input** | Sanitized images, part segmentation masks |
| **Output** | `{ damages[]: { type, severity, mask, area_pct, confidence, model_source }, cross_training_metrics, consensus_method }` |
| **SOTA Model** | Mask R-CNN fine-tuned on CarDD + Custom |
| **Research Model** | Custom UNet + Attention (from scratch) |
| **Build Type** | Both (head-to-head benchmarking) |
| **Innovation** | Pipeline 5's cross-training flywheel — winner teaches loser via knowledge distillation |
| **Damage Classes** | Dent, Scratch, Crack, Shatter, Deformation, Paint Damage, Glass Damage |
| **Severity Levels** | Minor, Moderate, Severe, Totalled |

### M5 — 3D Depth Estimation (Optional)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Estimate damage depth/volume from multi-view or monocular images |
| **Input** | Sanitized images (3+ for NeRF, 1 for monocular) |
| **Output** | `{ depth_map, deformation_depth_mm, damage_volume_cm3, point_cloud_path }` |
| **Models** | Instant-NGP + 3D Gaussian Splatting (multi-view), Custom Depth UNet (monocular) |
| **Build Type** | Existing + Custom from scratch |
| **Track** | Deep only, triggered by triage router when multi-view available |

### M6 — ICVE Pricing Engine (Zero AI)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Calculate repair/replace costs using rule-based engine with RAG-grounded data |
| **Input** | Damage JSON, vehicle info, part IDs |
| **Output** | `{ line_items[]: { part, damage_type, repair_cost, replace_cost, depreciation, source_citation }, total, confidence_bounds }` |
| **Engine** | Pure rule-based — NO AI in pricing path |
| **Data Sources** | RAG: OEM parts catalog, IRDAI labor rates, policy clauses, depreciation tables |
| **Build Type** | Custom built |
| **Innovation** | Pipeline 3's RAG citations — every price traceable to source document |

### M7 — Explainable Report Generator

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Generate human-readable survey report with XAI overlays |
| **Input** | All prior module outputs + original images |
| **Output** | `{ report_pdf, report_json, grad_cam_overlays[], audit_hash, citations[] }` |
| **Models** | InternVL2 / LLaVA-1.6 fine-tuned VLM |
| **Build Type** | Fine-tuned VLM |
| **Innovation** | Citation verifier ensures every fact is RAG-grounded; GRAD-CAM damage heatmaps |

---

## Cross-Cutting Architecture Components

### Triage Router (from Pipeline 4)

Routes claims into **Fast Track** or **Full Track** based on complexity:

| Track | Latency | Modules Used | Coverage |
|-------|---------|-------------|----------|
| **Fast** | < 5 sec | M0 → M2 (Nano) → M4 (lightweight) → M6 (simplified) → M7 (template) | ~80% claims |
| **Full** | 30-120 sec | M0 → M1 → M2 → M3 → M4 (dual-model) → M5 (optional) → M6 (full RAG) → M7 (VLM) | ~20% claims |

**Arbitration**: When both tracks run, outputs are compared. If estimates differ by >15%, the Deep output is used.

### RAG Knowledge Layer (from Pipeline 3)

A shared vector database (pgvector) powering multiple modules:
- **M1** queries historical fraud patterns
- **M2** verifies vehicle against policy records  
- **M6** retrieves OEM prices, labor rates, policy clauses
- **M7** grounds every report fact in cited sources

### Cross-Training Engine (from Pipeline 5)

The core research contribution:
1. **Dual inference** — SOTA and from-scratch models run on every batch
2. **Metric comparison** — mAP, IoU, F1 tracked in MLflow
3. **Knowledge distillation** — Winner's predictions become soft labels for the loser
4. **Active learning** — Uncertain samples flagged for human annotation (20-50/week)
5. **Drift monitoring** — Evidently AI detects systematic model degradation

### Calibration Feedback Loop

Post-settlement data flows back:
1. Actual settlement amount vs AI estimate stored in calibration DB
2. Drift monitor detects systematic bias (regional, vehicle-type, damage-type)
3. Bias alerts trigger targeted active learning

---

## Technology Stack

### Core Vision Models
| Model | Architecture | Build Type | Purpose |
|-------|-------------|-----------|---------|
| YOLO11m | YOLO family | Pre-trained | Person/face detection (M0) |
| YOLO11m_plates | YOLO family | Fine-tuned | License plate detection (M0) |
| YOLOv8n | YOLO family | Fine-tuned SOTA | Vehicle detection (M2) |
| SegFormer-B5 | Transformer segmentation | Fine-tuned SOTA | Part segmentation (M3) |
| Mask R-CNN | Instance segmentation | Fine-tuned SOTA | Damage detection — SOTA path (M4) |
| Custom UNet + Attention | UNet variant | From Scratch | Damage detection — research path (M4) |
| Custom EfficientNet-B4 | EfficientNet | From Scratch | Fraud/forensics (M1) |
| Custom Depth UNet | UNet variant | From Scratch | Monocular depth estimation (M5) |
| Instant-NGP + 3DGS | Neural radiance fields | Existing | 3D reconstruction (M5) |

### Language & Multimodal Models
- **VLM**: InternVL2-26B / LLaVA-1.6-34B (report generation)
- **Embeddings**: BAAI/bge-large-en-v1.5 / E5-large-v2 (RAG embeddings)

### Infrastructure
- **Backend**: FastAPI + Celery + Redis
- **Vector DB**: pgvector (PostgreSQL extension)
- **Experiment Tracking**: MLflow / Weights & Biases
- **Data Versioning**: DVC
- **Active Learning**: ModAL + Label Studio
- **Drift Detection**: Evidently AI
- **Model Serving**: BentoML / FastAPI + Docker
- **Training**: PyTorch Lightning + DeepSpeed

### Datasets
- **Vehicle**: Custom Indian vehicles (CarDekho scraped + manual annotation)
- **Damage**: CarDD + COCO-Vehicles + Custom annotated
- **Fraud**: FaceForensics++ + DEFACTO + Custom insurance fraud
- **Parts/Pricing**: IRDAI-compliant OEM catalog + regional labor rates
- **3D**: ShapeNet (pretrain) + custom multi-view insurance images

---

## Module Interface Contract

Every module exposes a standard REST API:

```
POST /api/modules/{module_id}/process
Content-Type: multipart/form-data

Request:
  files: List[UploadFile]   # one or more images

Response (single image):
{
  "module_id": "M0",
  "filename": "image.jpg",
  "processing_time_ms": 120,
  "output": { /* module-specific structured JSON */ }
}

Response (multiple images): array of the above objects
```

---

## Data Flow Summary

```
Input Images → Triage Router → [Fast/Full Track Selection]
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         │ FAST TRACK                                          │ FULL TRACK
         │ M0 → M2(Nano) → M4(light) → M6(simple) → M7(tmpl) │ M0 → M1 → M2 → M3 → M4(dual) → M5? → M6(RAG) → M7(VLM)
         └──────────────────────────┬──────────────────────────┘
                                    │
                        Arbitration (if both ran)
                                    │
                         Human-in-the-Loop Review
                                    │
                            Claim Decision
                                    │
                    Settlement Feedback → Calibration DB → Drift Monitor
```

---

## Comparison: Hybrid vs Individual Pipelines

| Criterion | Hybrid Pipeline | Best Individual |
|-----------|----------------|-----------------|
| Integration simplicity | ⭐⭐⭐⭐ | Pipeline 1 (⭐⭐⭐⭐⭐) |
| Research novelty | ⭐⭐⭐⭐⭐ | Pipeline 5 (⭐⭐⭐⭐⭐) |
| Explainability | ⭐⭐⭐⭐⭐ | Pipeline 3 (⭐⭐⭐⭐⭐) |
| Speed | ⭐⭐⭐⭐ | Pipeline 4 (⭐⭐⭐⭐⭐) |
| Scalability | ⭐⭐⭐⭐ | Pipeline 4 (⭐⭐⭐⭐⭐) |
| Regulatory compliance | ⭐⭐⭐⭐⭐ | Pipeline 3 (⭐⭐⭐⭐⭐) |
| Model improvement | ⭐⭐⭐⭐⭐ | Pipeline 5 (⭐⭐⭐⭐⭐) |
| 10-month feasibility | ⭐⭐⭐⭐ | Pipeline 1 (⭐⭐⭐⭐⭐) |
