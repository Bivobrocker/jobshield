
from urllib.parse import urlsplit


ATS_PLATFORMS = {
    "greenhouse.io": "GREENHOUSE",
    "boards.greenhouse.io": "GREENHOUSE",
    "lever.co": "LEVER",
    "jobs.lever.co": "LEVER",
    "myworkdayjobs.com": "WORKDAY",
    "workday.com": "WORKDAY",
    "smartrecruiters.com": "SMARTRECRUITERS",
    "careers.smartrecruiters.com": "SMARTRECRUITERS",
    "jobs.smartrecruiters.com": "SMARTRECRUITERS",
    "ashbyhq.com": "ASHBY",
    "jobs.ashbyhq.com": "ASHBY"
}


def detect_ats_platform(careers_url):
    if not careers_url:
        return {
            "platform": "UNKNOWN",
            "hostname": None
        }

    try:
        parsed = urlsplit(careers_url)
        hostname = (parsed.hostname or "").lower().rstrip(".")

        if parsed.scheme not in ("http", "https") or not hostname:
            raise ValueError("Invalid careers URL")

        platform = "CUSTOM_WEBSITE"

        for domain, name in ATS_PLATFORMS.items():
            if hostname == domain or hostname.endswith("." + domain):
                platform = name
                break

        return {
            "platform": platform,
            "hostname": hostname
        }

    except ValueError:
        return {
            "platform": "UNKNOWN",
            "hostname": None
        }
