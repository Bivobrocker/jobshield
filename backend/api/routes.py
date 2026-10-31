
import json
from urllib.parse import urlsplit
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.schemas import JobAnalysisRequest, JobAnalysisResponse
from backend.database.db import get_db, Base, engine
from backend.database.models import JobAnalysis
from backend.engine.rules import detect_text_red_flags
from backend.engine.decision import decide_risk
from backend.ml.predict import predict_job_risk

from backend.verification.company_check import check_company_website
from backend.verification.email_check import check_recruiter_email
from backend.verification.domain_check import check_domain
from backend.verification.url_check import check_job_url
from backend.verification.vacancy_verifier import verify_vacancy


router = APIRouter(prefix="/api/v1", tags=["Job Analysis"])

Base.metadata.create_all(bind=engine)


@router.post("/analyze", response_model=JobAnalysisResponse)
def analyze_job(
    request: JobAnalysisRequest,
    db: Session = Depends(get_db)
):

    analysis_id = "JS-" + str(uuid4())[:8].upper()
    checked_at = datetime.now(timezone.utc).isoformat()

    evidence = []
    recommendations = []
    vacancy_verification = None

    # True only while every required verification function returns
    # a structured result. An UNVERIFIED result still counts as a
    # completed check; it does not count as verified evidence.
    checks_completed = True

    # 1. Detect suspicious message content
    text_evidence, text_recommendations = detect_text_red_flags(
        request.job_text
    )

    evidence.extend(text_evidence)
    recommendations.extend(text_recommendations)

    # 2. Run company and recruiter checks
    # Store the company result so it can be displayed and reused if needed.
    company_evidence = None

    try:
        company_evidence = check_company_website(
            request.company_website,
            request.company_name
        )
        if isinstance(company_evidence, dict):
            evidence.append(company_evidence)
        else:
            checks_completed = False
    except Exception:
        checks_completed = False
        evidence.append({
            "category": "VERIFICATION_ERROR",
            "status": "UNABLE_TO_VERIFY",
            "severity": "WARNING",
            "finding": "Company website verification failed.",
            "source_url": request.company_website,
            "checked_at": checked_at
        })

    checks = [
        lambda: check_recruiter_email(
            request.recruiter_email,
            request.company_website
        ),
        # DNS and HTTP reachability do not prove domain ownership.
        lambda: check_domain(request.company_website)
    ]

    for check in checks:
        try:
            result = check()
            if isinstance(result, dict):
                evidence.append(result)
            else:
                checks_completed = False
        except Exception:
            checks_completed = False
            evidence.append({
                "category": "VERIFICATION_ERROR",
                "status": "UNABLE_TO_VERIFY",
                "severity": "WARNING",
                "finding": "A verification check could not be completed.",
                "source_url": None,
                "checked_at": checked_at
            })

    # 3. Verify the actual vacancy
    if (
        request.company_name
        and request.company_website
        and (request.job_title or request.job_id)
    ):
        try:
            
            vacancy_result = verify_vacancy(
                company_name=request.company_name,
                company_website=request.company_website,
                job_title=request.job_title or "",
                job_location=request.job_location or "",
                job_id=request.job_id,
                submitted_description=request.job_text,
                careers_url=request.careers_url,
                job_url=request.job_url,
                discovery_result=(
                    company_evidence.get("discovery")
                    if isinstance(company_evidence, dict)
                    else None
                )
            )


            if not isinstance(vacancy_result, dict):
                checks_completed = False
                vacancy_result = None
                raise ValueError("Vacancy verifier returned an invalid result")

            vacancy_verification = vacancy_result
            vacancy_status = vacancy_result.get(
                "status", "UNABLE_TO_VERIFY"
            )

            official_job = vacancy_result.get("official_job", {})

            evidence.append({
                "category": "OFFICIAL_VACANCY_VERIFICATION",
                "status": vacancy_status,
                "severity": (
                    "HIGH"
                    if vacancy_status == "DETAILS_MISMATCH"
                    else "INFO"
                ),
                "finding": vacancy_result.get(
                    "finding",
                    "Official vacancy verification could not be completed."
                ),
                "source_url": official_job.get("official_url"),
                "checked_at": checked_at
            })

            # 4. Description comparison
            for result in vacancy_result.get(
                "description_comparisons", []
            ):
                comparison = result.get(
                    "description_comparison", {}
                )

                comparison_status = comparison.get(
                    "status", "UNABLE_TO_COMPARE"
                )

                severity = (
                    "WARNING"
                    if comparison_status in (
                        "LOW_MATCH",
                        "PARTIAL_MATCH"
                    )
                    else "INFO"
                )

                evidence.append({
                    "category": "JOB_DESCRIPTION_COMPARISON",
                    "status": comparison_status,
                    "severity": severity,
                    "finding": comparison.get("finding", ""),
                    "source_url": result.get(
                        "official_job", {}
                    ).get("official_url"),
                    "checked_at": checked_at
                })

            if vacancy_status == "UNABLE_TO_VERIFY":
                recommendations.append(
                    "Verify the vacancy manually through the employer's independently confirmed careers website."
                )

            if vacancy_status == "NOT_FOUND":
                recommendations.append(
                    "Check the job ID and search for the vacancy directly on the employer's careers website."
                )

        except Exception:
            checks_completed = False
            evidence.append({
                "category": "OFFICIAL_VACANCY_VERIFICATION",
                "status": "UNABLE_TO_VERIFY",
                "severity": "WARNING",
                "finding": "The vacancy verification service encountered an error.",
                "source_url": None,
                "checked_at": checked_at
            })

            recommendations.append(
                "Verify the vacancy manually through the employer's official careers website."
            )

    else:
        checks_completed = False
        evidence.append({
            "category": "OFFICIAL_VACANCY_VERIFICATION",
            "status": "MISSING",
            "severity": "INFO",
            "finding": "Insufficient company or vacancy details for official listing verification.",
            "source_url": None,
            "checked_at": checked_at
        })

        recommendations.append(
            "Provide the company name, website and job title or job ID for vacancy verification."
        )

    # 5. Cross-check the submitted job URL against the official listing.
    # A URL format check alone does not verify that the link is the same vacancy.
    if request.job_url:
        official_url = None
        if isinstance(vacancy_verification, dict):
            official_url = (
                vacancy_verification.get("official_job") or {}
            ).get("official_url")

        def comparable_url(value):
            try:
                parsed = urlsplit(value.strip())
                if parsed.scheme not in ("http", "https") or not parsed.hostname:
                    return None
                if parsed.username or parsed.password:
                    return None
                host = parsed.hostname.lower().rstrip(".")
                port = parsed.port
                if port and not ((parsed.scheme == "http" and port == 80) or
                                 (parsed.scheme == "https" and port == 443)):
                    host = f"{host}:{port}"
                path = "/" + "/".join(
                    part for part in parsed.path.split("/") if part
                )
                return host, path.rstrip("/").lower()
            except (AttributeError, TypeError, ValueError):
                return None

        submitted_key = comparable_url(request.job_url)
        official_key = comparable_url(official_url) if official_url else None

        if (
            vacancy_verification
            and vacancy_verification.get("status") == "DETAILS_MATCH"
            and submitted_key
            and official_key
            and submitted_key == official_key
        ):
            job_url_evidence = {
                "category": "JOB_URL",
                "status": "VERIFIED",
                "severity": "INFO",
                "finding": "Submitted job URL matches the URL of the vacancy found by the official listing check.",
                "source_url": official_url,
                "checked_at": checked_at
            }
        elif (
            vacancy_verification
            and vacancy_verification.get("status") == "DETAILS_MATCH"
            and submitted_key
            and official_key
        ):
            job_url_evidence = {
                "category": "JOB_URL",
                "status": "MISMATCH",
                "severity": "WARNING",
                "finding": "Submitted job URL does not match the URL of the vacancy found by the official listing check.",
                "source_url": request.job_url,
                "checked_at": checked_at
            }
        else:
            # No independently matched official URL is available; retain the
            # original safe-format validation and do not claim verification.
            job_url_evidence = check_job_url(request.job_url)

        evidence.append(job_url_evidence)
    else:
        evidence.append(check_job_url(None))

    # 6. General safety recommendations
    recommendations.extend([
        "Verify the recruiter using contact details published on the independently confirmed company website.",
        "Never pay recruitment fees or share OTPs, passwords or banking credentials."
    ])

    # 7. Complete evidence fields
    for item in evidence:
        item.setdefault("source_url", None)
        item.setdefault("checked_at", checked_at)

    recommendations = list(dict.fromkeys(recommendations))

    # 8. ML prediction
    model_result = None

    try:
        ml_output = predict_job_risk(
            job_text=request.job_text,
            job_title=request.job_title,
            company_name=request.company_name,
            job_location=request.job_location
        )

        if ml_output:
            model_result = {
                "prediction": ml_output["prediction"],
                "score": ml_output["score"],
                "score_type": ml_output["score_type"]
            }

    except Exception as error:
        print(f"ML prediction error: {error}")

    # 9. Decide overall risk
    # ML does not override the evidence-based verdict.
    verdict = decide_risk(
        evidence,
        checks_completed=checks_completed
    )

    # 10. Save analysis to database
    try:
        db_record = JobAnalysis(
            analysis_id=analysis_id,
            verdict=verdict,
            company_name=request.company_name,
            job_title=request.job_title,
            job_text=request.job_text,
            vacancy_verification=json.dumps(
                vacancy_verification
            ) if vacancy_verification else None,
            evidence=json.dumps(evidence),
            recommendations=json.dumps(recommendations)
        )

        db.add(db_record)
        db.commit()

    except Exception:
        db.rollback()
        raise

    # 11. Return final API response
    return JobAnalysisResponse(
        analysis_id=analysis_id,
        verdict=verdict,
        model=model_result,
        vacancy_verification=vacancy_verification,
        evidence=evidence,
        recommendations=recommendations,
        limitations=[
            "The ML model uses an EMSCAD-based historical dataset from 2012-2014; performance on modern job scams has not yet been independently validated.",
            "The ML score is an uncalibrated model output, not a confirmed probability of fraud.",
            "Automated vacancy search currently supports Greenhouse, Lever, Ashby, Workday and SmartRecruiters. Other platforms may return UNABLE_TO_VERIFY.",
            "A matching vacancy does not prove that the recruiter contacting the applicant is genuine.",
            "Careers portal ownership is not independently confirmed.",
            "Description similarity is a supporting signal, not proof of fraud.",
            "Unavailable or incomplete searches must not be interpreted as proof of fraud."
        ]
    )


@router.get("/history")
def get_analysis_history(
    db: Session = Depends(get_db)
):
    records = (
        db.query(JobAnalysis)
        .order_by(JobAnalysis.created_at.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "analysis_id": item.analysis_id,
            "verdict": item.verdict,
            "company_name": item.company_name,
            "job_title": item.job_title,
            "created_at": item.created_at,
            "evidence": json.loads(item.evidence or "[]"),
            "recommendations": json.loads(
                item.recommendations or "[]"
            )
        }
        for item in records
    ]
