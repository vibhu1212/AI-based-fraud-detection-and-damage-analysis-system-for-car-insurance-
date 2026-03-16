# Reusable Assets Directory

This document lists the core components and modules of the **AI Automated Insurance Survey Agent** that have been designed as reusable, plug-and-play modules for existing insurance systems.

## 1. Machine Learning Models
These models map directly to the pipeline modules and can be reused independently or in other sequences.

- **M0: Image Quality & Privacy Gate**
  - Path: `backend/app/modules/m0_quality/`
  - Reusable Use Case: General-purpose PII scrubbing and image quality pre-check before storage.
- **M1: Fraud Detection**
  - Path: `backend/app/modules/m1_fraud/`
  - Reusable Use Case: General EXIF tampering and deepfake analysis for any submitted digital media.
- **M2: Vehicle Identification**
  - Path: `backend/app/modules/m2_vehicle_id/`
  - Reusable Use Case: Automated vehicle classification (Make/Model/Year) for cataloging or inventory purposes.
- **M4: Damage Detection Dual Model Engine**
  - Path: `backend/app/modules/m4_damage/`
  - Reusable Use Case: Benchmarking setup to compare from-scratch ML models vs SOTA (Mask R-CNN).

## 2. Infrastructure & Utility Modules
- **FastAPI Backend Framework**
  - Path: `backend/app/core/`
  - Description: Standardized implementation of REST endpoints, dependency injection, and Pydantic schemas.
- **RAG Preprocessing Scripts**
  - Path: `scripts/rag/`
  - Description: Tools to embed policy documents into `pgvector` for citation-backed AI output.

## 3. Frontend Dashboard Components
- **Module Test Runner Interface**
  - Path: `frontend/src/components/ModuleRunner.tsx`
  - Description: A React component allowing independent execution and JSON inspection of any arbitrary backend module.
- **Damage Map Visualizer**
  - Path: `frontend/src/components/DamageVisualizer.tsx`
  - Description: Highlighting segmentation maps (e.g., bumpers, dents) interactively over an uploaded image.

## 4. Datasets & DVC Configurations
- **Indian Vehicle Dataset (Annotated)**
  - Reusable Use Case: Curated training dataset containing >200 models with varied backgrounds (Requires specific repo access).
- **Pricing rules & Labor Matrices**
  - Reusable Use Case: Standardized rate cards and depreciation matrices adapted from IRDAI.
