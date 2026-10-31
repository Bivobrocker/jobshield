
import re
from urllib.parse import urlsplit


FREE_EMAIL_PROVIDERS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "proton.me",
    "protonmail.com"
}


def get_domain(value):
    if not value:
        return None

    value = value.strip()

    try:
        if "://" in value:
            value = urlsplit(value).hostname or ""
    except ValueError:
        return None

    return value.lower().rstrip(".").removeprefix("www.") or None


def check_recruiter_email(email, company_website):

    if not email:
        return {
            "category": "RECRUITER_EMAIL",
            "status": "MISSING",
            "severity": "UNKNOWN",
            "finding": "Recruiter email was not provided."
        }

    email = email.strip().lower()

    email_pattern = (
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
        r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
    )

    if (
        not re.fullmatch(email_pattern, email)
        or ".." in email
        or email.startswith(".")
        or email.endswith(".")
    ):
        return {
            "category": "RECRUITER_EMAIL",
            "status": "MISMATCH",
            "severity": "WARNING",
            "finding": "Recruiter email format is invalid."
        }

    email_domain = email.rsplit("@", 1)[1]
    company_domain = get_domain(company_website)

    if not company_domain:
        return {
            "category": "RECRUITER_EMAIL",
            "status": "UNVERIFIED",
            "severity": "UNKNOWN",
            "finding": "Company domain is unavailable for comparison."
        }

    if email_domain in FREE_EMAIL_PROVIDERS:
        return {
            "category": "RECRUITER_EMAIL",
            "status": "UNVERIFIED",
            "severity": "WARNING",
            "finding": "Recruiter uses a free email provider. Independently verify their identity."
        }

    if email_domain == company_domain:
        return {
            "category": "RECRUITER_EMAIL",
            "status": "MATCHED",
            "severity": "INFO",
            "finding": "Recruiter email domain matches the supplied company website domain. Recruiter identity is not independently confirmed."
        }

    return {
        "category": "RECRUITER_EMAIL",
        "status": "MISMATCH",
        "severity": "WARNING",
        "finding": "Recruiter email domain differs from the supplied company website domain. Verify through official company contact details."
    }
