import ipaddress
from urllib.parse import urlsplit
from datetime import datetime, timezone


def check_job_url(job_url):
    checked_at = datetime.now(timezone.utc).isoformat()

    if not job_url:
        return {
            "category": "JOB_URL",
            "status": "MISSING",
            "severity": "UNKNOWN",
            "finding": "Job posting URL was not provided.",
            "source_url": None,
            "checked_at": checked_at
        }

    try:
        parsed = urlsplit(job_url.strip())

        if parsed.scheme not in ("http", "https"):
            raise ValueError("Invalid scheme")

        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Invalid URL")

        hostname = parsed.hostname.lower().rstrip(".")

        if hostname == "localhost" or hostname.endswith(".localhost"):
            raise ValueError("Local address")

        try:
            ip = ipaddress.ip_address(hostname)
            if not ip.is_global:
                raise ValueError("Private IP")
        except ValueError as error:
            if str(error) == "Private IP":
                raise

        return {
            "category": "JOB_URL",
            "status": "UNVERIFIED",
            "severity": "INFO",
            "finding": "Job URL has a valid basic format. The vacancy has not been verified.",
            "source_url": job_url,
            "checked_at": checked_at
        }

    except Exception:
        return {
            "category": "JOB_URL",
            "status": "MISMATCH",
            "severity": "WARNING",
            "finding": "Job URL is invalid or points to an unsafe address.",
            "source_url": job_url,
            "checked_at": checked_at
        }