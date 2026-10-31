
# JobShield AI

### AI-Powered Job Fraud Detection and Verification Platform

JobShield AI helps job seekers assess potentially fraudulent job opportunities by combining machine learning with company, recruiter, domain, and vacancy verification.

## Problem

Job seekers face fake job postings, impersonated companies, fraudulent recruiters, and requests for money or sensitive personal information.

## Solution

JobShield AI provides an integrated platform to analyze job opportunities and present relevant verification evidence and risk assessments.

## Key Features

- Job description fraud-pattern analysis
- Company website verification
- Recruiter email and domain checks
- Careers-page and vacancy verification
- Machine-learning-based job classification
- Consolidated risk assessment dashboard

## Technology Stack

- Python
- Streamlit
- FastAPI
- Scikit-learn
- TF-IDF
- Logistic Regression
- SQLite

## Architecture

User Input
    ↓
Streamlit Frontend
    ↓
FastAPI Backend
    ↓
Verification Modules + ML Model
    ↓
Evidence Aggregation
    ↓
Risk Assessment
    ↓
Results Dashboard

## Run Locally

### 1. Clone the repository

git clone https://github.com/Bivobrocker/jobshield.git

cd jobshield

### 2. Create a virtual environment

python -m venv venv

### 3. Activate it (Windows)

venv\Scripts\activate

### 4. Install dependencies

pip install -r requirements.txt

### 5. Start the backend

uvicorn backend.main:app --reload --port 8000

### 6. Start the frontend in another terminal

streamlit run frontend/app.py

## API Documentation

Once the backend is running:

http://127.0.0.1:8000/docs

## Important Note

JobShield AI provides risk assessments based on available evidence. It does not guarantee that every fraudulent or legitimate job opportunity will be correctly identified.

## Future Scope

- Additional recruitment platform integrations
- Improved verification coverage
- Explainable risk assessment
- Model evaluation and calibration
- Scalable cloud deployment

## License

MIT License
