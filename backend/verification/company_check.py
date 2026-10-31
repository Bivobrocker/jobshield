
from datetime import datetime, timezone
from urllib.parse import urlsplit

from backend.verification.company_sources import discover_careers_page


def check_company_website(website, company_name=None):
    checked_at = datetime.now(timezone.utc).isoformat()

    if not website:
        return {
            "category": "COMPANY_WEBSITE",
            "status": "MISSING",
            "severity": "UNKNOWN",
            "finding": "Company website was not provided.",
            "source_url": None,
            "checked_at": checked_at
        }

    try:
        parsed = urlsplit(website.strip())

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Invalid website URL")

        company_name = company_name or parsed.hostname

        result = discover_careers_page(
            company_name,
            website.strip()
        )

        if result.get("status") != "CAREERS_LINKS_FOUND":
            return {
                "category": "COMPANY_WEBSITE",
                "status": "UNVERIFIED",
                "severity": "INFO",
                "finding": (
                    "Website could not be linked to a discoverable "
                    "careers portal. Company ownership remains unconfirmed."
                ),
                "source_url": website,
                "checked_at": checked_at,
                "discovery": result
            }

        links = result.get("careers_links", [])

        ats_links = [
            link for link in links
            if link.get("type") == "ATS_PORTAL"
        ]

        if ats_links:
            return {
                "category": "COMPANY_WEBSITE",
                "status": "MATCHED",
                "severity": "INFO",
                "finding": (
                    "Company website links to a careers page and "
                    "a recruitment platform. This supports the "
                    "company-careers relationship but does not "
                    "independently prove legal ownership."
                ),
                "source_url": website,
                "checked_at": checked_at,
                "careers_links": links
            }

        return {
            "category": "COMPANY_WEBSITE",
            "status": "UNVERIFIED",
            "severity": "INFO",
            "finding": (
                "A careers page was discovered on the company website, "
                "but no supported recruitment platform was confirmed."
            ),
            "source_url": website,
            "checked_at": checked_at,
            "careers_links": links
        }

    except ValueError:
        return {
            "category": "COMPANY_WEBSITE",
            "status": "MISMATCH",
            "severity": "WARNING",
            "finding": "Company website URL is invalid or unsafe.",
            "source_url": website,
            "checked_at": checked_at
        }

    except Exception:
        return {
            "category": "COMPANY_WEBSITE",
            "status": "UNABLE_TO_VERIFY",
            "severity": "WARNING",
            "finding": "Company careers relationship could not be verified.",
            "source_url": website,
            "checked_at": checked_at
        }
