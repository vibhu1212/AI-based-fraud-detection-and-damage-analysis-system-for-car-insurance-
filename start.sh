#!/usr/bin/env bash
# ============================================================
# InsurAI — Start All Services (Linux / macOS)
# Run: chmod +x start.sh && ./start.sh
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${PURPLE}${BOLD}  🧠 InsurAI — AI Insurance Survey Agent${NC}"
echo -e "${CYAN}  Module Testing Dashboard${NC}"
echo -e "  ─────────────────────────────────────"
echo ""

# ── Check prerequisites ──────────────────────────────────────
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}✗ $1 is not installed. Please install $1 first.${NC}"
        exit 1
    fi
}

echo -e "${YELLOW}▸ Checking prerequisites...${NC}"
check_command python3
check_command node
check_command npm

PYTHON_VER=$(python3 --version 2>&1 | awk '{print $2}')
NODE_VER=$(node --version 2>&1)
echo -e "  ${GREEN}✓${NC} Python ${PYTHON_VER}"
echo -e "  ${GREEN}✓${NC} Node.js ${NODE_VER}"
echo ""

# ── Backend setup ────────────────────────────────────────────
echo -e "${YELLOW}▸ Setting up backend...${NC}"

BACKEND_DIR="${PROJECT_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "  Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "${VENV_DIR}/bin/activate"

# Install dependencies if needed
if [ ! -f "${VENV_DIR}/.deps_installed" ]; then
    echo -e "  Installing Python dependencies (this may take a few minutes)..."
    echo ""
    pip install -r "${BACKEND_DIR}/requirements.txt"
    echo ""
    touch "${VENV_DIR}/.deps_installed"
else
    echo -e "  ${GREEN}✓${NC} Python dependencies already installed"
fi

# Create .env if it doesn't exist
if [ ! -f "${BACKEND_DIR}/.env" ] && [ -f "${BACKEND_DIR}/.env.example" ]; then
    cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env"
    echo -e "  ${GREEN}✓${NC} Created .env from .env.example"
fi

echo -e "  ${GREEN}✓${NC} Backend ready"
echo ""

# ── Frontend setup ───────────────────────────────────────────
echo -e "${YELLOW}▸ Setting up frontend...${NC}"

FRONTEND_DIR="${PROJECT_DIR}/frontend"

# Install dependencies if needed
if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
    echo -e "  Installing Node.js dependencies..."
    echo ""
    (cd "$FRONTEND_DIR" && npm install)
else
    echo -e "  ${GREEN}✓${NC} Node.js dependencies already installed"
fi

echo -e "  ${GREEN}✓${NC} Frontend ready"
echo ""

# ── Start services ───────────────────────────────────────────
echo -e "${YELLOW}▸ Starting services...${NC}"
echo ""

# Trap to kill background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}▸ Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null && echo -e "  ${GREEN}✓${NC} Backend stopped"
    kill $FRONTEND_PID 2>/dev/null && echo -e "  ${GREEN}✓${NC} Frontend stopped"
    echo -e "${PURPLE}${BOLD}  👋 InsurAI stopped. Goodbye!${NC}"
    echo ""
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start backend
echo -e "  Starting backend on ${CYAN}http://localhost:8000${NC} ..."
(cd "$BACKEND_DIR" && uvicorn app.main:app --reload --port 8000 --host 0.0.0.0) &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend
echo -e "  Starting frontend on ${CYAN}http://localhost:5173${NC} ..."
(cd "$FRONTEND_DIR" && npm run dev -- --host 0.0.0.0 --port 5173) &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 2

echo ""
echo -e "  ╔═══════════════════════════════════════════════╗"
echo -e "  ║  ${GREEN}${BOLD}✅ InsurAI is running!${NC}                        ║"
echo -e "  ║                                               ║"
echo -e "  ║  ${CYAN}Frontend:${NC}  http://localhost:5173              ║"
echo -e "  ║  ${CYAN}Backend:${NC}   http://localhost:8000              ║"
echo -e "  ║  ${CYAN}API Docs:${NC}  http://localhost:8000/api/docs     ║"
echo -e "  ║                                               ║"
echo -e "  ║  Press ${YELLOW}Ctrl+C${NC} to stop all services           ║"
echo -e "  ╚═══════════════════════════════════════════════╝"
echo ""

# Wait for background processes
wait
