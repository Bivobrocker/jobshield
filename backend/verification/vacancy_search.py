
import requests

from backend.verification.company_sources import get_company_source


def search_official_jobs(company_name, job_title, location=""):
    source = get_company_source(company_name)

    if not source:
        return {
            "status": "UNSUPPORTED_COMPANY",
            "message": "No trusted official careers source is configured.",
            "matches": []
        }

    if not job_title or not job_title.strip():
        return {
            "status": "MISSING_JOB_TITLE",
            "message": "A job title is required for vacancy verification.",
            "matches": []
        }

    api_url = "https://apply.careers.microsoft.com/api/pcsx/search"

    params = {
        "domain": source["official_domain"],
        "query": job_title.strip(),
        "location": location.strip(),
        "start": 0
    }

    try:
        response = requests.get(
            api_url,
            params=params,
            headers={"User-Agent": "JobShieldAI/1.0"},
            timeout=15
        )

        if response.status_code == 429:
            return {
            "status": "UNABLE_TO_VERIFY",
            "message": "Microsoft careers search is temporarily rate-limited. Try again later.",
            "retry_after": response.headers.get("Retry-After"),
            "matches": []
        }

        response.raise_for_status()
        result = response.json()

        data = result.get("data", {})
        positions = data.get("positions", [])

        if not isinstance(positions, list):
            raise ValueError("Unexpected careers API response format")

        matches = []

        for job in positions:
            matches.append({
                "job_id": job.get("id"),
                "title": job.get("name"),
                "location": job.get("locations"),
                "official_url": job.get("positionUrl"),
                "source": source["careers_url"]
            })

        return {
            "status": "RESULTS_FOUND" if matches else "NO_RESULTS",
            "company": company_name,
            "total_count": data.get("count", len(matches)),
            "matches": matches,
            "source_url": source["careers_url"]
        }

    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
        return {
            "status": "UNABLE_TO_VERIFY",
            "message": str(error),
            "matches": []
        }
