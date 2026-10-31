from pathlib import Path
import json

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = ROOT / "models" / "jobshield_model.joblib"
THRESHOLD_PATH = ROOT / "models" / "model_threshold.json"

MODEL = None
THRESHOLD = 0.5

TEXT_COLUMNS = [
    "title",
    "company_profile",
    "description",
    "requirements",
    "benefits"
]

CATEGORICAL_COLUMNS = [
    "location",
    "department",
    "employment_type",
    "required_experience",
    "required_education",
    "industry",
    "function"
]

NUMERIC_COLUMNS = [
    "telecommuting",
    "has_company_logo",
    "has_questions"
]

FEATURE_COLUMNS = (
    TEXT_COLUMNS + CATEGORICAL_COLUMNS + NUMERIC_COLUMNS
)

try:
    MODEL = joblib.load(MODEL_PATH)

    with open(THRESHOLD_PATH, "r") as f:
        THRESHOLD = float(json.load(f)["threshold"])

except Exception as error:
    print(f"ML model loading failed: {error}")
    MODEL = None
    THRESHOLD = 0.5

MODEL_LOADED = MODEL is not None


def predict_job_risk(
    job_text,
    job_title=None,
    company_name=None,
    job_location=None
):
    if not MODEL_LOADED:
        return None

    row = {
        "title": job_title or "",
        "company_profile": company_name or "",
        "description": job_text or "",
        "requirements": "",
        "benefits": "",
        "location": job_location or "",
        "department": "",
        "employment_type": "",
        "required_experience": "",
        "required_education": "",
        "industry": "",
        "function": "",
        "telecommuting": None,
        "has_company_logo": None,
        "has_questions": None
    }

    features = pd.DataFrame(
        [row],
        columns=FEATURE_COLUMNS
    )

    probabilities = MODEL.predict_proba(features)[0]

    fraud_index = list(MODEL.classes_).index(1)
    fraud_score = float(probabilities[fraud_index])

    prediction = (
        "FRAUDULENT"
        if fraud_score >= THRESHOLD
        else "LEGITIMATE"
    )

    return {
        "prediction": prediction,
        "score": round(fraud_score, 4),
        "score_type": "uncalibrated_model_probability"
    }