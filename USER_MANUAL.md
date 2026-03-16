# User Manual: AI Insurance Survey Agent

## 1. Introduction
Welcome to the Developer and Researcher User Manual for the **AI Automated Insurance Survey Agent**. This system is designed as an 8-module sequential ML pipeline to automate vehicle damage and pricing assessments.

## 2. Getting Started

### 2.1 Starting the System
The easiest way to run the platform locally is using the provided start scripts.

- **Linux:** Run `./start.sh`
- **macOS:** Double click `start.command` or run `./start.sh`
- **Windows:** Double click `start.bat`

This command automatically:
1. Provisions the Python virtual environment and installs backend dependencies.
2. Migrates environment variables (`.env`).
3. Starts the FastAPI backend (Default on http://localhost:8000).
4. Installs Node.js dependencies and starts the Vite frontend testing dashboard (Default on http://localhost:5173).

### 2.2 Dashboard Usage
The React Frontend is specifically built for testing and benchmarking the pipeline.

1. **Upload an Image:** Navigate to the main screen and drag-and-drop a vehicle damage image.
2. **Select Module Testing Mode:** Choose whether you want to run an individual module (e.g., `M2: Vehicle ID`) or a full pipeline sequence.
3. **Inspect Output:** View the resulting JSON data, overlaid damage masks, confidence scores, and estimated repair costs.

## 3. API Reference
If you're integrating the AI Agent into an existing system:
- Access the auto-generated Swagger UI at `http://localhost:8000/docs`.
- Each pipeline step M0 through M7 has a dedicated endpoint that accepts an image byte array and returns standard JSON.

## 4. Troubleshooting
- **Address Already in Use:** If Port `8000` or `5173` is busy, stop existing processes using `kill -9 $(lsof -t -i:8000)`.
- **Validation Errors on Startup:** Ensure the `.env` file matches the fields required in `backend/app/config.py` (e.g., `OCR_ENGINE` and `DETECTION_MODEL_PATH`).
- **Missing Models:** Model weights (`.pt`, `.bin`) are gitignored and must be downloaded separately using DVC: `dvc pull`.

## 5. Support & Contributions
For feature requests or adding a custom model to the cross-training flywheel, please create a feature branch and submit a PR.
Read `MONTHLY_GOALS.md` for our current trajectory.
