
from datetime import datetime, timezone
from urllib.parse import urlsplit

from backend.verification.company_sources import discover_careers_page
from backend.verification.ats_detector import detect_ats_platform
from backend.verification.ats_search import search_ats_jobs
from backend.verification.description_check import compare_job_descriptions
from backend.verification.vacancy_decision import decide_vacancy_status


def normalize_url(url):
    try:
        parsed = urlsplit(url)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            return None

        host = parsed.hostname.lower().rstrip(".")
        path_parts = [
            part for part in parsed.path.split("/") if part
        ]

        ats_hosts = {
            "jobs.lever.co",
            "jobs.ashbyhq.com",
            "boards.greenhouse.io",
            "job-boards.greenhouse.io"
        }

        if host in ats_hosts and path_parts:
            return host, path_parts[0].lower()

        return host, "/" + "/".join(path_parts).lower()

    except (ValueError, TypeError):
        return None


def verify_vacancy(
    company_name,
    company_website,
    job_title="",
    job_location="",
    job_id=None,
    submitted_description="",
    careers_url=None,
    job_url=None,
    discovery_result=None
):
    checked_at = datetime.now(timezone.utc).isoformat()

    # Reuse the company check's discovery result. Crawling the same
    # company homepage and careers pages twice caused long requests.
    discovery = discovery_result or discover_careers_page(
        company_name,
        company_website
    )

    if discovery.get("status") != "CAREERS_LINKS_FOUND":
        return {
            "status": "UNABLE_TO_VERIFY",
            "finding": "Company careers page could not be discovered.",
            "source_validation": "NOT_VALIDATED",
            "discovery": discovery,
            "checked_at": checked_at
        }

    career_pages = discovery.get("career_pages", [])
    discovered_links = discovery.get("careers_links", [])

    # 2. Validate supplied careers URL against discovered links.
    source_validation = "CAREERS_PAGE_DISCOVERED"

    if careers_url:
        supplied_key = normalize_url(careers_url)

        matched_links = [
            link for link in career_pages + discovered_links
            if normalize_url(link.get("url", "")) == supplied_key
        ] if supplied_key else []

        if not matched_links:
            return {
                "status": "UNABLE_TO_VERIFY",
                "finding": (
                    "Supplied careers URL was not discovered "
                    "from the company's careers website."
                ),
                "source_validation": "NOT_VALIDATED",
                "checked_at": checked_at
            }

        # Do not fetch the supplied URL again here.
        # ATS boards can block HTML requests or return non-HTML.
        source_validation = "DISCOVERED_CAREERS_URL_MATCHED"

        careers_links = matched_links

    else:
        careers_links = discovered_links

    # 3. Search supported ATS platforms or custom job pages.
    successful_search = False
    search_failures = []

    for link in careers_links:

        platform_info = detect_ats_platform(link["url"])
        platform = platform_info["platform"]

        search = search_ats_jobs(
            link["url"],
            platform,
            job_title,
            job_location,
            job_id,
            
        )

        if search.get("status") == "UNABLE_TO_VERIFY":
            search_failures.append({
                "platform": platform,
                "message": search.get(
                    "message",
                    "Search failed."
                )
            })
            continue

        successful_search = True

        if search.get("status") != "RESULTS_FOUND":
            continue

        # 4. Compare official and submitted descriptions.
        comparisons = []

        for match in search.get("matches", []):

            comparison = compare_job_descriptions(
                submitted_description,
                match.get("description", "")
            )

            comparisons.append({
                "official_job": match,
                "description_comparison": comparison
            })

        # 5. Decide vacancy verification status.
        decision = decide_vacancy_status(
            search["status"],
            search.get("matches", []),
            job_title,
            job_location,
            job_id
        )

        return {
            **decision,
            "platform": platform,
            "source_validation": (
                "LINKED_FROM_SUPPLIED_WEBSITE_NOT_INDEPENDENTLY_CONFIRMED"
            ),
            "description_comparisons": comparisons,
            "total_jobs_checked": search.get(
                "total_jobs_checked", 0
            ),
            "checked_at": checked_at
        }

    # 6. Distinguish completed searches from failed searches.
    if successful_search:
        return {
            "status": "NOT_FOUND",
            "finding": (
                "No matching vacancy was found in the "
                "successfully searched careers listings."
            ),
            "source_validation": source_validation,
            "search_failures": search_failures,
            "checked_at": checked_at
        }

    return {
        "status": "UNABLE_TO_VERIFY",
        "finding": (
            "No supported recruitment platform could "
            "complete vacancy verification."
        ),
        "source_validation": source_validation,
        "search_failures": search_failures,
        "checked_at": checked_at
    }
