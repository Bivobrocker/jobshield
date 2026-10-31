
import ipaddress
import socket
import requests

from urllib.parse import urlsplit, urljoin
from html.parser import HTMLParser
from datetime import datetime, timezone
from functools import lru_cache


CAREER_KEYWORDS = (
    "career", "careers", "jobs", "job-openings",
    "work-with-us", "work-with", "recruitment",
    "opportunities", "vacancies"
)

ATS_HOSTS = {
    "GREENHOUSE": ("boards.greenhouse.io", "job-boards.greenhouse.io"),
    "LEVER": ("jobs.lever.co",),
    "ASHBY": ("jobs.ashbyhq.com",),
    "WORKDAY": ("myworkdayjobs.com", "myworkday.com"),
    "SMARTRECRUITERS": (
        "careers.smartrecruiters.com",
        "jobs.smartrecruiters.com"
    )
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobShieldAI/1.0)"
}

REDIRECT_CODES = (301, 302, 303, 307, 308)

# Short timeout to avoid long waits on unresponsive websites.
REQUEST_TIMEOUT = (3, 5)

# Limit discovery to avoid serially fetching many career pages.
MAX_CAREER_PAGES = 5


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_link = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            attributes = dict(attrs)
            href = attributes.get("href")

            if href:
                self.current_link = {
                    "href": href,
                    "text": attributes.get("title", "")
                }

    def handle_data(self, data):
        if self.current_link:
            self.current_link["text"] += " " + data.strip()

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_link:
            self.links.append(self.current_link)
            self.current_link = None


@lru_cache(maxsize=256)
def is_public_domain(hostname):
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_global
    except ValueError:
        try:
            addresses = socket.getaddrinfo(hostname, None)
            return bool(addresses) and all(
                ipaddress.ip_address(item[4][0]).is_global
                for item in addresses
            )
        except (socket.gaierror, ValueError):
            return False


def validate_public_url(url):
    try:
        parsed = urlsplit(url)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            return False

        hostname = parsed.hostname.lower().rstrip(".")

        if (
            hostname == "localhost"
            or hostname.endswith(".localhost")
        ):
            return False

        return is_public_domain(hostname)

    except (ValueError, TypeError):
        return False


def safe_get(url, max_redirects=3):
    current_url = url

    for _ in range(max_redirects + 1):
        if not validate_public_url(current_url):
            raise ValueError(
                "URL is invalid or resolves to a non-public address."
            )

        response = requests.get(
            current_url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False
        )

        if response.status_code in REDIRECT_CODES:
            location = response.headers.get("Location")

            if not location:
                raise ValueError("Redirect has no destination.")

            current_url = urljoin(current_url, location)
            continue

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")

        if "text/html" not in content_type.lower():
            raise ValueError("URL did not return an HTML page.")

        return response

    raise ValueError("Maximum redirect limit exceeded.")


def parse_links(html, base_url):
    parser = LinkParser()
    parser.feed(html[:1000000])

    results = []

    for item in parser.links:
        link = urljoin(base_url, item["href"])
        parsed = urlsplit(link)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            continue

        results.append({
            "url": link,
            "label": item["text"].strip() or item["href"],
            "host": parsed.hostname.lower().rstrip(".")
        })

    return results


def is_ats_link(url):
    hostname = (
        (urlsplit(url).hostname or "")
        .lower()
        .rstrip(".")
    )

    return any(
        hostname == domain or hostname.endswith("." + domain)
        for domains in ATS_HOSTS.values()
        for domain in domains
    )


def is_careers_link(link):
    parsed = urlsplit(link["url"])
    path = parsed.path.lower().strip("/")
    label = link["label"].lower()

    if "jobseeker" in label or "login" in label:
        return False

    return any(
        keyword in path.split("/") or keyword in label
        for keyword in CAREER_KEYWORDS
    )


def discover_careers_page(company_name, company_website):
    checked_at = datetime.now(timezone.utc).isoformat()

    if not company_name or not company_website:
        return {
            "status": "MISSING",
            "message": "Company name and website are required.",
            "careers_links": [],
            "career_pages": [],
            "checked_at": checked_at
        }

    try:
        website = company_website.strip()
        homepage = safe_get(website)

        homepage_links = parse_links(
            homepage.text,
            homepage.url
        )

        career_pages = []
        seen_pages = set()

        for link in homepage_links:
            if is_careers_link(link) and link["url"] not in seen_pages:
                seen_pages.add(link["url"])
                career_pages.append(link)

        if not career_pages:
            return {
                "status": "NO_CAREERS_LINK_FOUND",
                "company": company_name,
                "website_checked": website,
                "careers_links": [],
                "career_pages": [],
                "checked_at": checked_at,
                "message": (
                    "No careers page was discovered on the supplied website."
                )
            }

        ats_links = []
        page_failures = []

        # Check only the most relevant two careers pages.
        for page in career_pages[:MAX_CAREER_PAGES]:
            try:
                response = safe_get(page["url"])

                page_links = parse_links(
                    response.text,
                    response.url
                )

                for link in page_links:
                    if is_ats_link(link["url"]):
                        ats_links.append({
                            **link,
                            "type": "ATS_PORTAL",
                            "discovered_from": response.url
                        })

            except (
                requests.RequestException,
                ValueError,
                TypeError
            ) as error:
                page_failures.append({
                    "url": page["url"],
                    "message": str(error)
                })

        unique_ats_links = []
        seen_ats = set()

        for link in ats_links:
            if link["url"] not in seen_ats:
                seen_ats.add(link["url"])
                unique_ats_links.append(link)

        discovered_links = (
            unique_ats_links
            if unique_ats_links
            else [
                {**page, "type": "CAREERS_PAGE"}
                for page in career_pages
            ]
        )

        return {
            "status": "CAREERS_LINKS_FOUND",
            "company": company_name,
            "website_checked": website,
            "career_pages": career_pages,
            "careers_links": discovered_links,
            "page_failures": page_failures,
            "checked_at": checked_at,
            "message": (
                "Careers pages and recruitment links were discovered "
                "from the supplied website. This does not independently "
                "prove company ownership."
            )
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError
    ) as error:
        return {
            "status": "UNABLE_TO_VERIFY",
            "message": str(error),
            "careers_links": [],
            "career_pages": [],
            "checked_at": checked_at
        }
