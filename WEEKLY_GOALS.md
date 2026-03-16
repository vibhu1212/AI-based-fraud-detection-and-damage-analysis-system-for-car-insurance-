# Weekly Goals — AI Insurance Survey Agent (10 Months / 40 Weeks)

---

## Phase 1: Core Pipeline Modules (Months 1-5 / Weeks 1-20)

### Month 1: Foundation & M0-M1

**Week 1** — Project Setup & Environment
- [x] Set up development environment (CUDA, PyTorch, FastAPI)
- [ ] Configure MLflow experiment tracking
- [ ] Initialize DVC for dataset versioning
- [x] Set up project structure (modules/, services/, core/)
- [x] Create base module abstract class and shared schemas

**Week 2** — M0: Quality Gate Implementation
- [x] Implement blur detection (Laplacian variance, OpenCV)
- [x] Implement exposure/brightness checker
- [x] Build resolution validator
- [x] Create quality scoring (EnhancedQualityGateValidator service)
- [x] Write module REST endpoint (POST /api/modules/M0/process)

**Week 3** — M0: PII Masking Engine
- [x] Implement person/face detection (YOLO11m, class 0, conf=0.45 — blurs top 35% of bbox)
- [x] Implement license plate detector (YOLO11m_plates conf=0.3 + Haar cascade union)
- [x] Build Gaussian blur (99×99) redaction pipeline (pii_masker.py)
- [x] DPDP Act 2023 compliance — faces and plates masked before any output
- [x] Integration: quality gate → PII masking → redacted_image_b64 in M0 response

**Week 4** — M1: Fraud Detection (From Scratch)
- [ ] Collect fraud dataset (FaceForensics++, DEFACTO, custom)
- [ ] Design Custom EfficientNet-B4 forensics architecture
- [ ] Implement EXIF metadata analyzer
- [ ] Begin training fraud detection CNN
- [ ] Build module endpoint with fraud scoring

---

### Month 2: M1 Completion & M2-M3

**Week 5** — M1: Fraud Detection Continued
- [ ] Complete fraud CNN training (evaluate on holdout set)
- [ ] Implement GAN fingerprint analysis
- [ ] Build fraud confidence report generator
- [ ] Add human escalation path for high-score claims
- [ ] Benchmark fraud detector: precision, recall, F1

**Week 6** — M2: Vehicle Identification (Data Collection)
- [ ] Scrape Indian vehicle dataset (CarDekho, 200+ models)
- [ ] Clean and annotate vehicle images (make/model/year/trim)
- [ ] Prepare YOLO training dataset format
- [ ] Version dataset with DVC
- [ ] Begin YOLOv10 fine-tuning on Indian vehicles

**Week 7** — M2: Vehicle Identification (Training & Eval)
- [ ] Complete YOLOv10-L training (full model)
- [ ] Train YOLOv10-Nano (fast track variant)
- [ ] Evaluate: mAP50, mAP50-95 on test set
- [ ] Build vehicle identification module endpoint
- [ ] Test with real Indian car images

**Week 8** — M3: Part Segmentation
- [ ] Prepare CarDD + COCO-Vehicles + custom part dataset
- [ ] Define 40+ Indian car part classes
- [ ] Begin SegFormer-B5 fine-tuning
- [ ] Build data augmentation pipeline (Albumentations)
- [ ] Track training in MLflow

---

### Month 3: M3 Completion & M4 Dual-Model

**Week 9** — M3: Part Segmentation Continued
- [ ] Complete SegFormer-B5 training
- [ ] Evaluate: mIoU per part class
- [ ] Build part segmentation module endpoint
- [ ] Visualize segmentation masks
- [ ] Integration test: M2 → M3 pipeline flow

**Week 10** — M4: Damage Analysis — SOTA Path
- [ ] Prepare damage detection dataset (CarDD + custom annotated)
- [ ] Define 7 damage classes: dent, scratch, crack, shatter, deformation, paint, glass
- [ ] Fine-tune Mask R-CNN on damage dataset
- [ ] Implement severity scoring head (MLP on mask area + damage type)
- [ ] Track training metrics in MLflow

**Week 11** — M4: Damage Analysis — From-Scratch Path
- [ ] Design Custom UNet + Attention architecture
- [ ] Implement from-scratch model (PyTorch)
- [ ] Train on same dataset as Mask R-CNN
- [ ] Build comparison logic (mAP, IoU, F1 per model)
- [ ] Create model comparator module

**Week 12** — M4: Cross-Training Engine
- [ ] Implement knowledge distillation (soft-label loss)
- [ ] Build winner-teaches-loser logic
- [ ] Implement SOTA blind spot detection (scratch wins unexpectedly)
- [ ] Create ensemble prediction mode (weighted average)
- [ ] Integration test: full M4 dual-model pipeline

---

### Month 4: M5-M6 & Pipeline Integration

**Week 13** — M5: 3D Depth (Monocular)
- [ ] Implement Custom Depth UNet from scratch
- [ ] Train on indoor/vehicle depth datasets
- [ ] Implement MiDaS v3.1 fine-tuned fallback
- [ ] Build depth map visualization
- [ ] Module endpoint for monocular depth

**Week 14** — M5: 3D Depth (Multi-view NeRF)
- [ ] Set up COLMAP for camera pose estimation
- [ ] Integrate Instant-NGP for NeRF reconstruction
- [ ] Implement 3D Gaussian Splatting pipeline
- [ ] Build volumetric damage quantification
- [ ] Test with multi-view insurance image sets

**Week 15** — M6: ICVE Pricing Engine
- [ ] Build rule-based cost calculation engine
- [ ] Implement parts catalog database (OEM prices)
- [ ] Implement IRDAI labor rate card lookup
- [ ] Add depreciation calculation (vehicle age-based)
- [ ] Build per-part repair vs replace cost comparison

**Week 16** — M6 + Pipeline Integration
- [ ] Implement cost confidence bounds calculation
- [ ] Build audit trail with source citations
- [ ] Integration test: M4 → M5 → M6 data flow
- [ ] Build triage router (fast/deep track selection)
- [ ] End-to-end pipeline test: M0 → M6

---

### Month 5: M7, Dashboard & Phase 1 Milestone

**Week 17** — M7: Report Generator (VLM)
- [ ] Set up InternVL2 / LLaVA-1.6 for inference
- [ ] Fine-tune VLM on insurance report examples
- [ ] Implement GRAD-CAM overlay generator
- [ ] Build citation verifier (hallucination guard)
- [ ] Generate PDF + JSON report output

**Week 18** — M7 Completion & Testing Dashboard
- [ ] Complete VLM fine-tuning
- [ ] Build report template system (fast track)
- [ ] Test report quality with domain experts
- [ ] Enhance testing dashboard with all module panels
- [ ] Add pipeline visualization to dashboard

**Week 19** — Full Pipeline Integration
- [ ] End-to-end pipeline test: M0 → M7 (full track)
- [ ] End-to-end pipeline test: fast track
- [ ] Build arbitration module (fast vs deep comparison)
- [ ] Performance benchmarks (latency per module)
- [ ] Fix integration bugs

**Week 20** — Phase 1 Milestone & Documentation
- [ ] Full pipeline demo with real insurance images
- [ ] Write Phase 1 research report
- [ ] Document all module interfaces and performance
- [ ] Performance optimization pass
- [ ] **🎯 MILESTONE: Working 8-module pipeline with sequential execution**

---

## Phase 2: Research Contributions (Months 6-10 / Weeks 21-40)

### Month 6: RAG Knowledge Layer

**Week 21** — Vector Database Setup
- [ ] Set up pgvector (PostgreSQL extension)
- [ ] Implement embedding pipeline (bge-large-en-v1.5)
- [ ] Design vector DB schema (collections, metadata)
- [ ] Build RAG service abstraction layer

**Week 22** — Knowledge Base Population
- [ ] Embed insurance policy documents
- [ ] Embed OEM parts catalog
- [ ] Embed historical fraud pattern descriptions
- [ ] Embed IRDAI labor rate cards
- [ ] Embed vehicle specification database

**Week 23** — RAG Integration into Modules
- [ ] Integrate RAG into M1 (fraud pattern retrieval)
- [ ] Integrate RAG into M2 (policy verification)
- [ ] Integrate RAG into M6 (parts/labor/policy retrieval)
- [ ] Integrate RAG into M7 (citation grounding)
- [ ] Test RAG retrieval quality (precision@k)

**Week 24** — RAG Optimization
- [ ] Implement multi-query RAG (parallel retrieval)
- [ ] Add reranking for improved precision
- [ ] Build citation verifier (trace facts to sources)
- [ ] Latency optimization (RAG retrieval < 2 seconds)
- [ ] **🎯 MILESTONE: RAG-grounded pipeline with citation-backed outputs**

---

### Month 7: Cross-Training Flywheel

**Week 25** — Dual-Model Benchmarking Infrastructure
- [ ] Set up MLflow experiments for SOTA vs Scratch tracking
- [ ] Implement per-batch metric comparison
- [ ] Build automated benchmark reports
- [ ] Create dashboard for model comparison visualization

**Week 26** — Knowledge Distillation Pipeline
- [ ] Implement soft-label distillation loss function
- [ ] Build winner-teaches-loser training loop
- [ ] Implement distillation temperature tuning
- [ ] Test distillation effectiveness (scratch model improvement)

**Week 27** — Active Learning Engine
- [ ] Implement uncertainty sampling strategy
- [ ] Implement diversity sampling strategy
- [ ] Set up Label Studio for human annotation
- [ ] Build active learning queue with priority ranking
- [ ] Test with 50 annotations/week budget

**Week 28** — Cross-Training Validation
- [ ] Run cross-training for 2 weeks of data
- [ ] Measure scratch model improvement via distillation
- [ ] Document SOTA blind spots found by scratch model
- [ ] Write research findings for cross-training contribution
- [ ] **🎯 MILESTONE: Cross-training flywheel operational with measurable improvement**

---

### Month 8: Drift Detection & Auto-Calibration

**Week 29** — Drift Monitoring Setup
- [ ] Set up Evidently AI for model performance monitoring
- [ ] Implement calibration database (estimate vs settlement)
- [ ] Build drift detection alerts
- [ ] Create automated drift reports

**Week 30** — Calibration Feedback Loop
- [ ] Implement post-settlement feedback collector
- [ ] Build regional bias detection
- [ ] Implement vehicle-type bias detection
- [ ] Create automatic recalibration triggers
- [ ] Test with simulated settlement data

**Week 31** — Continuous Retraining Pipeline
- [ ] Set up DVC-based dataset versioning for retraining
- [ ] Implement automated evaluation on holdout set
- [ ] Build canary deployment (10% traffic rollout)
- [ ] Implement rollback logic for degraded models
- [ ] Test retraining pipeline end-to-end

**Week 32** — MLOps Optimization
- [ ] Optimize retraining frequency
- [ ] Tune active learning batch sizes
- [ ] Performance profiling and compute optimization
- [ ] Document MLOps workflows
- [ ] **🎯 MILESTONE: Self-improving pipeline with drift detection and auto-calibration**

---

### Month 9: Research Paper & Advanced Features

**Week 33** — Research Paper Writing
- [ ] Write abstract and introduction
- [ ] Document methodology (hybrid pipeline design)
- [ ] Create comparison tables (SOTA vs Scratch results)
- [ ] Generate figures and diagrams

**Week 34** — Research Paper Continued
- [ ] Write results section (cross-training, RAG grounding, triage)
- [ ] Write discussion and conclusions
- [ ] Peer review within team
- [ ] Prepare supplementary materials

**Week 35** — Advanced Feature: Auto-Approve System
- [ ] Design auto-approve thresholds (claim value, confidence, fraud score)
- [ ] Implement auto-approve rule engine
- [ ] Build audit trail for auto-approved claims
- [ ] Test with historical claim data

**Week 36** — Advanced Feature: Enhanced 3D
- [ ] Improve NeRF quality with 3D Gaussian Splatting v2
- [ ] Add damage volume-to-severity mapping
- [ ] Build 3D visualization in testing dashboard
- [ ] **🎯 MILESTONE: Research paper draft complete**

---

### Month 10: Final Integration & Delivery

**Week 37** — Final Integration Testing
- [ ] End-to-end testing with 100+ real insurance claims
- [ ] Performance benchmarks (latency, accuracy, cost)
- [ ] Error analysis and edge case documentation
- [ ] UI polish on testing dashboard

**Week 38** — Production Readiness
- [ ] Docker containerization for all modules
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Security audit (PII handling, data encryption)
- [ ] Load testing

**Week 39** — Final Documentation
- [ ] Update all README and architecture docs
- [ ] Create deployment guide
- [ ] Record demo videos
- [ ] Prepare presentation materials

**Week 40** — Project Delivery
- [ ] Final demo to fellowship committee
- [ ] Submit research paper
- [ ] Publish GitHub repository
- [ ] Knowledge transfer documentation
- [ ] **🎯 MILESTONE: Complete 8-module hybrid pipeline with research contributions delivered**

---

## Progress Key
- `[ ]` — Not started
- `[/]` — In progress
- `[x]` — Completed
