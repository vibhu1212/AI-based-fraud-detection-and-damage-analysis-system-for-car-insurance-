# Monthly Goals — AI Insurance Survey Agent (10 Months)

---

## Overview

| Phase | Months | Focus | Key Deliverable |
|-------|--------|-------|----------------|
| **Phase 1** | 1-5 | Core Pipeline Modules | Working 8-module pipeline (M0-M7) |
| **Phase 2** | 6-10 | Research Contributions | RAG grounding, cross-training flywheel, paper |

---

## Phase 1: Core Pipeline Modules

### Month 1 — Foundation, M0: Quality Gate, M1: Fraud Detection
**Objective**: Set up project infrastructure and complete the first two modules.

| Deliverable | Status |
|-------------|--------|
| Development environment (CUDA, PyTorch, MLflow, DVC) | [/] |
| Base module interface + shared Pydantic schemas | [x] |
| M0: Image quality assessment (blur, exposure, resolution) | [x] |
| M0: PII masking (YOLO11m person + YOLO11m_plates + Haar cascade) | [x] |
| M1: Custom EfficientNet-B4 fraud CNN (from scratch) | [ ] |
| M1: EXIF metadata analyzer | [ ] |
| Module REST endpoints for M0 and M1 | [/] |

**🎯 Milestone**: M0 and M1 independently functional with REST APIs

---

### Month 2 — M2: Vehicle ID, M3: Part Segmentation
**Objective**: Train and deploy vehicle identification and part segmentation models.

| Deliverable | Status |
|-------------|--------|
| Indian vehicle dataset (200+ models, CarDekho + custom) | [ ] |
| YOLOv10-L fine-tuned on Indian vehicles (full model) | [ ] |
| YOLOv10-Nano trained (fast track variant) | [ ] |
| CarDD + custom part segmentation dataset (40+ classes) | [ ] |
| SegFormer-B5 fine-tuned for part segmentation | [ ] |
| Module REST endpoints for M2 and M3 | [ ] |
| Integration test: M0 → M1 → M2 → M3 sequential flow | [ ] |

**🎯 Milestone**: 4 modules working in sequence with JSON data flow

---

### Month 3 — M4: Damage Analysis (Dual-Model)
**Objective**: Build and benchmark SOTA vs from-scratch damage detection — core research distinction.

| Deliverable | Status |
|-------------|--------|
| Damage dataset (7 classes: dent, scratch, crack, shatter, deformation, paint, glass) | [ ] |
| Mask R-CNN fine-tuned (SOTA path) | [ ] |
| Custom UNet + Attention (from-scratch path) | [ ] |
| Model comparator (mAP, IoU, F1 per model) | [ ] |
| Knowledge distillation engine (winner teaches loser) | [ ] |
| Ensemble prediction mode | [ ] |
| Severity scoring head (minor/moderate/severe/totalled) | [ ] |

**🎯 Milestone**: Dual-model damage analysis with cross-training engine

---

### Month 4 — M5: 3D Depth, M6: ICVE Pricing
**Objective**: Complete depth estimation and rule-based pricing engine.

| Deliverable | Status |
|-------------|--------|
| Custom Depth UNet from scratch (monocular) | [ ] |
| Instant-NGP + 3D Gaussian Splatting (multi-view) | [ ] |
| Volumetric damage quantification (depth mm, volume cm³) | [ ] |
| Rule-based ICVE cost engine (zero AI in pricing) | [ ] |
| Parts catalog database (OEM prices) | [ ] |
| IRDAI labor rate card lookup | [ ] |
| Depreciation calculation + confidence bounds | [ ] |
| Triage router (fast/deep track selection logic) | [ ] |

**🎯 Milestone**: Pipeline complete through M6 with triage routing

---

### Month 5 — M7: Report Generator, Full Integration
**Objective**: Complete VLM-based report generation and achieve end-to-end pipeline.

| Deliverable | Status |
|-------------|--------|
| InternVL2 / LLaVA-1.6 fine-tuned for insurance reports | [ ] |
| GRAD-CAM overlay generator | [ ] |
| PDF + JSON report generation | [ ] |
| Fast track template report system | [ ] |
| End-to-end pipeline: M0 → M7 (full track) | [ ] |
| End-to-end pipeline: fast track (M0 → M2 → M4 → M6 → M7) | [ ] |
| Arbitration module (fast vs deep comparison) | [ ] |
| Testing dashboard: all module test panels complete | [ ] |
| Phase 1 research report | [ ] |

**🎯 PHASE 1 COMPLETE**: Working 8-module hybrid pipeline

---

## Phase 2: Research Contributions

### Month 6 — RAG Knowledge Layer
**Objective**: Ground pipeline decisions in retrieved insurance knowledge.

| Deliverable | Status |
|-------------|--------|
| pgvector database setup with embedding pipeline | [ ] |
| Insurance policy documents embedded | [ ] |
| OEM parts catalog embedded | [ ] |
| Historical fraud patterns embedded | [ ] |
| IRDAI labor rate cards embedded | [ ] |
| RAG integrated into M1 (fraud patterns), M2 (policy), M6 (pricing), M7 (citations) | [ ] |
| Citation verifier (trace every fact to KB source) | [ ] |
| RAG retrieval latency < 2 seconds | [ ] |

**🎯 Milestone**: RAG-grounded pipeline with citation-backed outputs

---

### Month 7 — Cross-Training Data Flywheel
**Objective**: Implement the core research contribution — SOTA vs Scratch competitive improvement.

| Deliverable | Status |
|-------------|--------|
| MLflow experiments: per-batch SOTA vs Scratch metrics | [ ] |
| Knowledge distillation pipeline (soft-label training) | [ ] |
| Active learning engine (uncertainty + diversity sampling) | [ ] |
| Label Studio annotation pipeline (50 samples/week) | [ ] |
| Measured scratch model improvement through distillation | [ ] |
| Documented SOTA blind spots found by scratch model | [ ] |

**🎯 Milestone**: Cross-training flywheel with measurable model improvement

---

### Month 8 — Drift Detection & MLOps
**Objective**: Build self-monitoring and auto-calibration capabilities.

| Deliverable | Status |
|-------------|--------|
| Evidently AI drift monitoring | [ ] |
| Calibration DB (estimate vs settlement feedback) | [ ] |
| Regional and vehicle-type bias detection | [ ] |
| DVC-based continuous retraining pipeline | [ ] |
| Canary deployment (10% traffic, auto-rollback) | [ ] |
| Automated evaluation on holdout sets | [ ] |

**🎯 Milestone**: Self-improving pipeline with drift detection

---

### Month 9 — Research Paper & Advanced Features
**Objective**: Document research contributions and implement advanced capabilities.

| Deliverable | Status |
|-------------|--------|
| Research paper: methodology, results, cross-training findings | [ ] |
| Comparison tables: SOTA vs Scratch per damage class | [ ] |
| Auto-approve system (rule-based thresholds) | [ ] |
| Enhanced 3D damage visualization | [ ] |
| Paper peer review within team | [ ] |

**🎯 Milestone**: Research paper draft complete

---

### Month 10 — Final Integration & Delivery
**Objective**: Production-ready deliverables, documentation, and project submission.

| Deliverable | Status |
|-------------|--------|
| End-to-end testing with 100+ real claims | [ ] |
| Docker containerization for all modules | [ ] |
| API documentation (OpenAPI/Swagger) | [ ] |
| Security audit (PII handling, encryption) | [ ] |
| Final demo to fellowship committee | [ ] |
| Research paper submission | [ ] |
| GitHub repository published | [ ] |
| Deployment guide + knowledge transfer docs | [ ] |

**🎯 PHASE 2 COMPLETE**: Full hybrid pipeline with research contributions delivered

---

## Progress Key
- `[ ]` — Not started
- `[/]` — In progress
- `[x]` — Completed
