
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# ---------------------------------------------------------------------------
# CORS
# Set FRONTEND_ORIGIN on Render to your Streamlit Cloud URL, e.g.:
#   https://your-app-name.streamlit.app
# Multiple origins can be comma-separated:
#   https://your-app.streamlit.app,https://custom-domain.com
# During local development the default "*" allows all origins.
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("FRONTEND_ORIGIN", "*")

if _raw_origins.strip() == "*":
    allow_origins = ["*"]
    allow_credentials = False  # credentials cannot be used with wildcard
else:
    allow_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
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