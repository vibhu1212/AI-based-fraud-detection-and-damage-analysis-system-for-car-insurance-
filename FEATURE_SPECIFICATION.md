# Feature Specification Document

## 1. Introduction
This document outlines the feature specifications for the **AI Automated Insurance Survey Agent**. The system is a modular AI toolset designed for automated vehicle insurance damage assessment.

## 2. Core Features

### 2.1 M0: Privacy & Quality Gate
- **Image Quality Check:** Automatically rejects or flags images with low resolution, high blur, or poor exposure.
- **PII Masking:** Detects and masks Personally Identifiable Information (faces, license plates) to ensure DPDP compliance.

### 2.2 M1: Fraud Detection
- **Deepfake/Tamper Detection:** Analyzes images for digital manipulation and inconsistencies.
- **EXIF Forensics:** Verifies image metadata to ensure the photo matches the claimed time and location.

### 2.3 M2: Vehicle Identification
- **Make/Model Recognition:** Identifies over 200 Indian vehicle models.
- **Year Estimation:** Estimates the manufacturing generation/year from visual cues.

### 2.4 M3: Part Segmentation
- **Exterior Segmentation:** Accurately segments key car parts including doors, bumpers, hoods, fenders, and glass.

### 2.5 M4: Damage Analysis
- **Damage Detection (Dual-Model):** Detects 7 classes of damage (dent, scratch, crack, shatter, deformation, paint, glass).
- **Severity Scoring:** Classifies damage into minor, moderate, severe, or totalled.

### 2.6 M5: 3D Depth Estimation
- **Volumetric Analysis:** Estimates the depth and volume (cm³) of dents and deformations.
- **View Reconstruction:** Supports multi-view Gaussian splatting or monocular depth estimation.

### 2.7 M6: ICVE Pricing Engine
- **Rule-Based Engine:** Calculates costs based on OEM parts databases and IRDAI labor rate cards.
- **Depreciation Calculation:** Applies standard depreciation matrices over time.

### 2.8 M7: Report Generator
- **Explainable AI:** Uses VLMs to generate human-readable reports summarizing the damages and repair plan.
- **Visual Evidence:** Generates PDF/JSON reports with GRAD-CAM style overlays.
