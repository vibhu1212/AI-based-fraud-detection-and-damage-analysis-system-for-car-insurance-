# AI Automated Insurance Survey Agent

[![License](https://img.shields.io/badge/license-Research-blue.svg)]()
[![Fellowship](https://img.shields.io/badge/TIH--IoT-CHANAKYA%20Fellowship%202025-orange.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()

**Modular AI tools for automated vehicle insurance damage assessment — built for integration into existing insurer/TPA systems.**

> **TIH-IoT CHANAKYA Fellowship 2025** — 10-month research project developing standalone ML modules that any insurance company, TPA, or survey agency can plug into their existing workflow.

---

## 🏗️ Architecture

This project implements a **custom hybrid pipeline** combining 5 architectural paradigms:

- **Sequential modular JSON I/O** — Clean, independently testable modules
- **Dynamic routing** — Smart triage between fast/deep processing tracks
- **RAG-grounded decisions** — Policy-aware, citation-backed outputs
- **Dual-track processing** — Fast (<5s) for simple claims, deep (<2min) for complex
- **SOTA vs Scratch cross-training** — Research contribution: competitive model improvement

📖 **Full architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)  
📐 **Design specs**: [DESIGN_PLAN.md](DESIGN_PLAN.md)

### Pipeline Modules

| Module | Purpose | Build Type |
|--------|---------|-----------|
| **M0** Privacy & Quality Gate | Image quality + PII masking (DPDP compliant) | Custom + Fine-tuned |
| **M1** Fraud Detection | Deepfake/tamper detection + EXIF forensics | From Scratch |
| **M2** Vehicle Identification | Indian make/model/year (200+ models) | Fine-tuned SOTA |
| **M3** Part Segmentation | Door/bumper/hood/fender segmentation | Fine-tuned SOTA |
| **M4** Damage Analysis | Dual-model: Mask R-CNN vs Custom UNet | Both (benchmarked) |
| **M5** 3D Depth Estimation | NeRF/3DGS multi-view or monocular depth | Existing + Custom |
| **M6** ICVE Pricing | Rule-based cost engine (zero AI) | Custom Built |
| **M7** Report Generator | VLM explainable report + GRAD-CAM | Fine-tuned VLM |

---

## 🚀 Quick Start

### One-Click Start (Recommended)

Start both backend and frontend with a single command:

| OS | Command |
|----|---------|
| **Linux** | `./start.sh` |
| **macOS** | Double-click `start.command` in Finder (or `./start.sh`) |
| **Windows** | Double-click `start.bat` |

The script auto-creates a virtual environment, installs all dependencies, and opens both services.

### Prerequisites

- Python 3.10+
- Node.js 18+ (for testing dashboard)
- CUDA-capable GPU (recommended for ML inference)
- Redis (for async task processing)

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend (Module Testing Dashboard)

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Open http://localhost:5173 to access the **Module Testing Dashboard**.

---

## 🧪 Module Testing Dashboard

The frontend is a **developer/researcher tool** (not a user-facing app) for:

- **Individual Module Testing** — Upload images → see raw JSON output for any module (M0-M7)
- **Pipeline Testing** — Chain modules together, view data flow step-by-step
- **Benchmark Mode** — Side-by-side SOTA vs Scratch model comparison
- **Results Visualization** — Damage overlays, segmentation masks, depth maps, cost tables

---

## 🛠️ Tech Stack

### Core ML Models
- **M0 — Person detection**: YOLO11m (class 0, conf=0.45) — head/face region blur
- **M0 — Plate detection**: YOLO11m_plates (conf=0.3) + OpenCV Haar cascade (union for higher recall)
- **M0 — Quality gate**: Custom `EnhancedQualityGateValidator` (Laplacian blur, exposure, resolution)
- **M2 — Vehicle ID**: YOLOv8n fine-tuned on Indian vehicles (200+ models)
- **M4 — Damage analysis**: Mask R-CNN (SOTA) vs Custom UNet + Attention (from scratch) — dual-model benchmarked
- **M3 — Part segmentation**: SegFormer-B5 fine-tuned (40+ part classes)
- **M1 — Fraud detection**: Custom EfficientNet-B4 (from scratch)
- **M5 — 3D depth**: Instant-NGP + 3D Gaussian Splatting (multi-view), Custom Depth UNet (monocular)
- **M7 — Report generation**: InternVL2 / LLaVA-1.6 (fine-tuned VLM)

### Infrastructure
- **Backend**: FastAPI + Celery + Redis
- **API**: Multi-image endpoint (`List[UploadFile]`) — processes all images, returns per-image results
- **RAG**: pgvector + BAAI/bge-large embeddings
- **MLOps**: MLflow, DVC, Evidently AI
- **Frontend**: Vite + React + TypeScript — per-image result cards with original vs redacted comparison
- **Training**: PyTorch Lightning + DeepSpeed

### Datasets
- Custom Indian vehicle dataset (Combined from Kaggle and real-world local surveyor data)
- CarDD + COCO-Vehicles (damage/parts via Kaggle)
- FaceForensics++ + DEFACTO (fraud)
- Real surveyor damage estimates , damaged car images and reports

---

## 📅 Timeline

| Phase | Months | Focus |
|-------|--------|-------|
| **Phase 1** | 1-5 | Core pipeline modules (M0-M7) + sequential integration |
| **Phase 2** | 6-10 | Research contributions: cross-training, active learning, RAG |

📋 **Detailed plans**: [WEEKLY_GOALS.md](WEEKLY_GOALS.md) · [MONTHLY_GOALS.md](MONTHLY_GOALS.md)

---

## 📁 Project Structure

```
├── ARCHITECTURE.md          # Hybrid pipeline architecture
├── DESIGN_PLAN.md           # Module specs & interfaces
├── WEEKLY_GOALS.md          # 40-week task breakdown
├── MONTHLY_GOALS.md         # 10-month milestones
├── backend/                 # FastAPI + ML modules
│   ├── app/
│   │   ├── api/             # REST endpoints
│   │   ├── modules/         # M0-M7 pipeline modules
│   │   ├── services/        # Shared services (RAG, triage)
│   │   └── core/            # Base classes & schemas
│   ├── models/              # Model weights (gitignored)
│   └── datasets/            # Training data (gitignored)
├── frontend/                # Module Testing Dashboard
│   └── src/                 # Vite + React app
├── notebooks/               # Research notebooks
├── scripts/                 # Training & eval scripts
└── configs/                 # Pipeline configuration
```

---

## 🔬 Research Contributions

1. **SOTA vs From-Scratch Benchmarking** — Head-to-head competition between fine-tuned SOTA models and custom-built architectures on Indian vehicle damage data
2. **Cross-Training Data Flywheel** — Winner-teaches-loser knowledge distillation with active learning
3. **RAG-Grounded Insurance AI** — Every pricing and report output is citation-backed from verified sources
4. **Indian Vehicle Specialization** — Custom datasets for 200+ Indian car models with regional pricing

---
