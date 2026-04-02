"""
InsurAI FastAPI Application Entry Point
P0 Master Locks Enforced: AI Drafts, Human Approves
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import health, auth, claims, surveyor, policies, websocket, audit, profile, storage, icve, vehicle_override, modules

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered insurance claim processing with P0 Master Locks",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profile.router, prefix="/api/users", tags=["Profile"])
app.include_router(claims.router, prefix="/api/claims", tags=["Claims"])
app.include_router(surveyor.router, prefix="/api/surveyor", tags=["Surveyor"])
app.include_router(policies.router, prefix="/api/policies", tags=["Policies"])
app.include_router(audit.router, tags=["Audit"])
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])
app.include_router(icve.router, prefix="/api/icve", tags=["ICVE"])
app.include_router(vehicle_override.router, tags=["Vehicle"])
from app.api import metrics, explanations
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
app.include_router(explanations.router, prefix="/api", tags=["Explanations"])
app.include_router(modules.router, prefix="/api", tags=["Module Testing"])
from app.api import pipeline_api
app.include_router(pipeline_api.router, prefix="/api", tags=["Pipeline"])


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"📍 Environment: {'Development' if settings.DEBUG else 'Production'}")
    print(f"🔒 P0 Master Locks: ENFORCED")
    print(f"✅ AI Drafts, Human Approves: ACTIVE")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    print(f"👋 {settings.APP_NAME} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
