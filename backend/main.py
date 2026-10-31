
from fastapi import FastAPI
from datetime import datetime, timezone

from backend.api.routes import router

app = FastAPI(
    title="JobShield AI",
    description="AI-Powered Recruitment Fraud Detection and Verification",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.include_router(router)


@app.get("/")
def home():
    return {
        "message": "Welcome to JobShield AI",
        "status": "Backend is running"
    }


@app.get("/health")
def health():
    from backend.ml.predict import MODEL_LOADED

    return {
        "status": "running",
        "database": "configured",
        "model_loaded": MODEL_LOADED,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }