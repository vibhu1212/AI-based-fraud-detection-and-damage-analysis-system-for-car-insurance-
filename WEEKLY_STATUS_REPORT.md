# Weekly Status Report — AI Automated Insurance Survey Agent

---

## Report: Week 3 (Month 1)
**Reporting Period:** Mar 10 – Mar 16, 2026
**Phase:** Phase 1 — Core Pipeline Modules

---

## 2. Executive Summary
M0 (Privacy & Quality Gate) is now fully implemented and functional end-to-end. The quality gate (blur, exposure, resolution) was completed in Week 2. This week focused on the PII masking engine: upgraded from a basic face cascade to YOLO11m person detection, added dual-method license plate detection (YOLO11m_plates + Haar cascade), and fixed a UI bug where the redacted image was not rendering. The testing dashboard now supports multi-image batch processing with per-image result cards.

---

## 3. Accomplishments This Week

- **M0 PII Masker — Person Detection** — Replaced face cascade with YOLO11m (class 0, conf=0.45). Blurs top 35% of each detected person bbox as the head/face region. **Status: Completed**
- **M0 PII Masker — Plate Detection** — YOLO11m_plates (conf=0.3) unioned with Haar cascade (haarcascade_russian_plate_number) for higher recall on Indian plates. **Status: Completed**
- **M0 PII Masker — Redaction** — Gaussian blur 99×99 applied strictly within detected bounding boxes. Lazy-loaded model singletons. **Status: Completed**
- **UI Bug Fix — Redacted Image Not Showing** — Root cause: `redacted_image_b64` is inside `result.output`, not at `result` top level. Fixed all three read sites (image display, metrics grid, JSON viewer). **Status: Completed**
- **Multi-Image Processing** — Backend endpoint upgraded from single `UploadFile` to `List[UploadFile]`. Frontend sends all images in one request and renders one result card per image with correct original/redacted pairing. **Status: Completed**
- **Testing Dashboard** — Module test panel now shows per-image filename + timing in card header, PII badge (faces/plates count), side-by-side original vs redacted comparison. **Status: Completed**

---

## 4. Planned for Next Week (Week 4 — M1: Fraud Detection)

- Collect fraud dataset (FaceForensics++, DEFACTO, custom tampered images)
- Design Custom EfficientNet-B4 forensics architecture
- Implement EXIF metadata analyzer
- Begin training fraud detection CNN
- Build M1 module endpoint with fraud scoring

---

## 5. Risks and Blockers

| Risk/Blocker | Impact | Mitigation Strategy | Owner |
|---|---|---|---|
| YOLO11m_plates model weights not yet trained | Medium | Haar cascade fallback active; plate training dataset collection in progress | Kartikay |
| MLflow / DVC not yet configured | Low | Deferred to Week 4 setup; local runs tracked manually for now | Kartikay |

---

## 6. Key Metrics

- **Completed Tasks:** 6 / 6 planned for Week 3
- **M0 Status:** ✅ Fully functional (quality gate + PII masking + REST endpoint + UI)
- **Models in use:** YOLO11m (person), YOLO11m_plates (plates), Haar cascade (plates fallback)
- **Blur kernel:** 99×99 Gaussian
- **Multi-image support:** ✅ Unlimited images per request, sequential processing

---

## Template for Future Reports

### 1. Project Overview
- **Project Name:** AI Automated Insurance Survey Agent
- **Reporting Period:** [Start Date] to [End Date]
- **Prepared By:** [Your Name/Team]

### 2. Executive Summary
[Brief 1-2 paragraph summary of the week's overall progress, major milestones achieved, and any critical issues]

### 3. Accomplishments This Week
- [Task 1 Description] - **Status:** [Completed/In Progress]

### 4. Planned for Next Week
- [Planned Task 1]

### 5. Risks and Blockers
| Risk/Blocker | Impact | Mitigation Strategy | Owner |
|---|---|---|---|
| [Description] | [High/Med/Low] | [Action plan] | [Name] |

### 6. Key Metrics
- **Completed Tasks:** [Number]
- **Defects Found / Resolved:** [Number] / [Number]
- **Model Accuracy (if applicable):** [Metric]
