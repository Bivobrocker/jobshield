import re
import time
import requests
import json
from html.parser import HTMLParser
from html import unescape
from urllib.parse import urlsplit

from backend.verification.company_sources import safe_get


HEADERS = {"User-Agent": "JobShieldAI/1.0"}
TIMEOUT = (3, 5)


def extract_board_name(careers_url, allowed_hosts):
    parsed = urlsplit(careers_url)

    if (
        parsed.scheme not in ("http", "https")
        or parsed.hostname not in allowed_hosts
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Invalid or unsupported ATS URL.")

    parts = parsed.path.strip("/").split("/")

    if not parts or not parts[0]:
        raise ValueError("ATS board name is missing.")

    return parts[0]


def matches_requested_details(
    title,
    location,
    current_job_id,
    job_title,
    job_location,
    job_id
):
    if job_title and title.strip().lower() != job_title.strip().lower():
        return False

    if (
        job_location
        and job_location.strip().lower() not in location.lower()
    ):
        return False

    if job_id and str(job_id).strip() != str(current_job_id).strip():
        return False

    return True


def search_greenhouse_jobs(
    careers_url,
    job_title="",
    location="",
    job_id=None
):
    try:
        board = extract_board_name(
            careers_url,
            {"boards.greenhouse.io", "job-boards.greenhouse.io"}
        )

        api_url = (
            f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
        )

        response = requests.get(
            api_url,
            headers=HEADERS,
            params={"content": "true"},
            timeout=TIMEOUT
        )
        response.raise_for_status()

        jobs = response.json().get("jobs", [])
        matches = []

        for job in jobs:
            title = job.get("title", "").strip()

            job_location = job.get("location", {})
            if isinstance(job_location, dict):
                job_location = job_location.get("name", "")

            current_id = str(job.get("id", ""))

            if matches_requested_details(
                title,
                str(job_location),
                current_id,
                job_title,
                location,
                job_id
            ):
                matches.append({
                    "job_id": current_id,
                    "title": title,
                    "location": str(job_location),
                    "official_url": job.get("absolute_url"),
                    "description": job.get("content", "")
                })

        return {
            "status": "RESULTS_FOUND" if matches else "NO_RESULTS",
            "total_jobs_checked": len(jobs),
            "matches": matches
        }

    except (requests.RequestException, ValueError, TypeError) as error:
        return {
            "status": "UNABLE_TO_VERIFY",
            "message": str(error),
            "matches": []
        }


def search_lever_jobs(
    careers_url,
    job_title="",
    location="",
    job_id=None
):
    try:
        board = extract_board_name(
            careers_url,
            {"jobs.lever.co"}
        )

        api_url = f"https://api.lever.co/v0/postings/{board}"

        response = requests.get(
            api_url,
            headers=HEADERS,
            params={"mode": "json"},
            timeout=TIMEOUT
        )
        response.raise_for_status()

        jobs = response.json()
        matches = []

        for job in jobs:
            title = job.get("text", "").strip()
            categories = job.get("categories") or {}
            job_location = categories.get("location", "")
            current_id = str(job.get("id", ""))

            if matches_requested_details(
                title,
                str(job_location),
                current_id,
                job_title,
                location,
                job_id
            ):
                matches.append({
                    "job_id": current_id,
                    "title": title,
                    "location": str(job_location),
                    "official_url": job.get("hostedUrl"),
                    "description": (
                        job.get("descriptionPlain")
                        or job.get("description")
                        or ""
                    )
                })

        return {
            "status": "RESULTS_FOUND" if matches else "NO_RESULTS",
            "total_jobs_checked": len(jobs),
            "matches": matches
        }

    except (requests.RequestException, ValueError, TypeError) as error:
        return {
            "status": "UNABLE_TO_VERIFY",
            "message": str(error),
            "matches": []
        }


def search_ashby_jobs(
    careers_url,
    job_title="",
    location="",
    job_id=None
):
    try:
        board = extract_board_name(
            careers_url,
            {"jobs.ashbyhq.com"}
        )

        api_url = (
            f"https://api.ashbyhq.com/posting-api/job-board/{board}"
        )

        response = requests.get(
            api_url,
            headers=HEADERS,
            params={"includeCompensation": "false"},
            timeout=TIMEOUT
        )
        response.raise_for_status()

        jobs = response.json().get("jobs", [])
        matches = []

        for job in jobs:
            title = job.get("title", "").strip()
            job_location = job.get("location", "")
            current_id = str(job.get("id", ""))

            if matches_requested_details(
                title,
                str(job_location),
                current_id,
                job_title,
                location,
                job_id
            ):
                matches.append({
                    "job_id": current_id,
                    "title": title,
                    "location": str(job_location),
                    "official_url": job.get("jobUrl"),
                    "description": (
                        job.get("descriptionHtml")
                        or job.get("description")
                        or ""
                    )
                })

        return {
            "status": "RESULTS_FOUND" if matches else "NO_RESULTS",
            "total_jobs_checked": len(jobs),
            "matches": matches
        }

    except (requests.RequestException, ValueError, TypeError) as error:
        return {
            "status": "UNABLE_TO_VERIFY",
            "message": str(error),
            "matches": []
        }

def search_workday_jobs(careers_url, job_title="", location="", job_id=None):
    try:
        parsed = urlsplit(careers_url)
        hostname = (parsed.hostname or "").lower()

        # Accept only public Workday careers hosts
        match = re.fullmatch(
            r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com",
            hostname
        )

        if (
            not match
            or parsed.scheme != "https"
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Invalid or unsupported Workday careers URL.")

        tenant = match.group(1)
        path_parts = [p for p in parsed.path.split("/") if p]

        if not path_parts:
            raise ValueError("Workday site name is missing.")

        # Ignore locale such as en-US
        if re.fullmatch(r"[a-z]{2}-[A-Z]{2}", path_parts[0]):
            path_parts = path_parts[1:]

        if not path_parts:
            raise ValueError("Workday site name is missing.")

        site = path_parts[0]

        base_url = (
            f"https://{hostname}/wday/cxs/{tenant}/{site}"
        )
        jobs_url = f"{base_url}/jobs"

        headers = {
            "User-Agent": "JobShieldAI/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        matches = []
        total_jobs = 0
        offset = 0
        page_limit = 20
        max_jobs = 2000

        while offset < max_jobs:
            response = requests.post(
                jobs_url,
                headers=headers,
                json={
                    "appliedFacets": {},
                    "limit": page_limit,
                    "offset": offset,
                    "searchText": job_title or ""
                },
                timeout=TIMEOUT
            )

            response.raise_for_status()
            payload = response.json()

            if offset == 0:
                total_jobs = int(payload.get("total", 0))

            postings = payload.get("jobPostings", [])

            if not postings:
                break

            for posting in postings:
                title = (posting.get("title") or "").strip()
                job_location = (
                    posting.get("locationsText") or ""
                ).strip()
                external_path = posting.get("externalPath")

                if not title or not external_path:
                    continue

                # Match submitted title and location
                if job_title and title.lower() != job_title.strip().lower():
                    continue

                if (
                    location
                    and location.strip().lower()
                    not in job_location.lower()
                ):
                    continue

                detail_url = base_url + external_path

                detail_response = requests.get(
                    detail_url,
                    headers=headers,
                    timeout=TIMEOUT
                )
                detail_response.raise_for_status()

                detail_data = detail_response.json()
                info = detail_data.get("jobPostingInfo", {})

                current_id = str(
                    info.get("jobReqId") or ""
                ).strip()

                # Fall back to the requisition ID in the URL path
                if not current_id:
                    id_match = re.search(
                        r"_([^/_]+)$", external_path
                    )
                    current_id = (
                        id_match.group(1) if id_match else ""
                    )

                if (
                    job_id
                    and str(job_id).strip().lower()
                    not in (
                        current_id.lower(),
                        external_path.lower()
                    )
                    and str(job_id).strip().lower()
                    not in external_path.lower()
                ):
                    continue

                matches.append({
                    "job_id": current_id,
                    "title": info.get("title") or title,
                    "location": (
                        info.get("location") or job_location
                    ),
                    "official_url": (
                        info.get("externalUrl") or detail_url
                    ),
                    "description": (
                        info.get("jobDescription") or ""
                    )
                })

                if len(matches) >= 20:
                    break

            if len(matches) >= 20:
                break

            offset += page_limit

            if offset >= min(total_jobs, max_jobs):
                break

            time.sleep(0.2)

        return {
            "status": (
                "RESULTS_FOUND" if matches else "NO_RESULTS"
            ),
            "total_jobs_available": total_jobs,
            "jobs_scanned": min(offset + page_limit, total_jobs, max_jobs),
            "matches": matches
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
        KeyError
    ) as error:
        return {
            "status": "UNABLE_TO_VERIFY",
            "message": str(error),
            "matches": []
        }


def search_smartrecruiters_jobs(
    careers_url, job_title="", location="", job_id=None
):
    try:
        parsed = urlsplit(careers_url)
        hostname = (parsed.hostname or "").lower()

        allowed_hosts = {
            "careers.smartrecruiters.com",
            "jobs.smartrecruiters.com"
        }

        if (
            parsed.scheme != "https"
            or hostname not in allowed_hosts
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Invalid SmartRecruiters careers URL.")

        parts = [part for part in parsed.path.split("/") if part]

        if not parts:
            raise ValueError("SmartRecruiters company identifier is missing.")

        company = parts[0]

        if not re.fullmatch(r"[A-Za-z0-9_-]+", company):
            raise ValueError("Invalid SmartRecruiters company identifier.")

        base_url = (
            f"https://api.smartrecruiters.com/v1/companies/"
            f"{company}/postings"
        )

        headers = {
            "User-Agent": "JobShieldAI/1.0",
            "Accept": "application/json"
        }

        matches = []
        total_jobs = 0
        offset = 0
        page_limit = 100
        max_jobs = 1000

        while offset < max_jobs:
            response = requests.get(
                base_url,
                headers=headers,
                params={
                    "limit": page_limit,
                    "offset": offset,
                    "q": job_title or ""
                },
                timeout=TIMEOUT
            )
            response.raise_for_status()

            payload = response.json()
            postings = payload.get("content", [])

            if offset == 0:
                total_jobs = int(payload.get("totalFound", 0))

            if not postings:
                break

            for posting in postings:
                title = (posting.get("name") or "").strip()

                location_data = posting.get("location") or {}

                if isinstance(location_data, dict):
                    job_location = ", ".join(
                        str(location_data.get(key, "")).strip()
                        for key in ("city", "region", "country")
                        if location_data.get(key)
                    )
                else:
                    job_location = str(location_data)

                if job_title and title.lower() != job_title.strip().lower():
                    continue

                if (
                    location
                    and location.strip().lower()
                    not in job_location.lower()
                ):
                    continue

                posting_id = str(posting.get("id") or "")
                posting_uuid = str(posting.get("uuid") or "")
                reference = str(posting.get("refNumber") or "")

                if job_id and str(job_id).strip().lower() not in {
                    posting_id.lower(),
                    posting_uuid.lower(),
                    reference.lower()
                }:
                    continue

                detail_url = (
                    f"{base_url}/{posting_id}"
                )

                detail_response = requests.get(
                    detail_url,
                    headers=headers,
                    timeout=TIMEOUT
                )
                detail_response.raise_for_status()

                detail = detail_response.json()

                detail_location = detail.get("location") or {}

                if isinstance(detail_location, dict):
                    job_location = ", ".join(
                        str(detail_location.get(key, "")).strip()
                        for key in ("city", "region", "country")
                        if detail_location.get(key)
                    ) or job_location

                job_ad = detail.get("jobAd") or {}
                sections = job_ad.get("sections") or {}

                description_parts = []

                if isinstance(sections, dict):
                    for section in sections.values():
                        if isinstance(section, dict):
                            description_parts.append(
                                section.get("text") or ""
                            )

                description = (
                    "\n".join(description_parts)
                    or job_ad.get("jobDescription")
                    or ""
                )

                matches.append({
                    "job_id": posting_id,
                    "title": detail.get("name") or title,
                    "location": job_location,
                    "official_url": (
                        detail.get("postingUrl")
                        or posting.get("postingUrl")
                        or f"https://jobs.smartrecruiters.com/"
                           f"{company}/{posting_id}"
                    ),
                    "description": description
                })

                if len(matches) >= 20:
                    break

            if len(matches) >= 20:
                break

            offset += page_limit

            if offset >= min(total_jobs, max_jobs):
                break

            time.sleep(0.2)

        return {
            "status": "RESULTS_FOUND" if matches else "NO_RESULTS",
            "total_jobs_available": total_jobs,
            "jobs_scanned": min(offset + page_limit, total_jobs, max_jobs),
            "matches": matches
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
        KeyError
    ) as error:
        return {
            "status": "UNABLE_TO_VERIFY",
            "message": str(error),
            "matches": []
        }



class JobPageParser(HTMLParser):
    """Extract structured job data and visible text from a job detail page."""

    def __init__(self):
        super().__init__()
        self.title_parts = []
        self.h1_parts = []
        self.visible_parts = []
        self.jsonld_blocks = []
        self.meta = {}
        self._in_title = False
        self._in_h1 = False
        self._in_jsonld = False
        self._script_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        tag = tag.lower()

        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
        elif tag == "meta":
            key = (
                attrs.get("property")
                or attrs.get("name")
                or attrs.get("itemprop")
            )
            value = attrs.get("content")
            if key and value:
                self.meta[key.lower()] = value

        elif tag == "script":
            script_type = (attrs.get("type") or "").lower()
            self._in_jsonld = (
                "application/ld+json" in script_type
            )
            self._script_parts = []

    def handle_data(self, data):
        if not data:
            return

        if self._in_title:
            self.title_parts.append(data)

        if self._in_h1:
            self.h1_parts.append(data)

        if self._in_jsonld:
            self._script_parts.append(data)
        else:
            cleaned = data.strip()
            if cleaned:
                self.visible_parts.append(cleaned)

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "script" and self._in_jsonld:
            block = "".join(self._script_parts).strip()
            if block:
                self.jsonld_blocks.append(block)
            self._in_jsonld = False
            self._script_parts = []


def _normalise_text(value):
    value = unescape(str(value or ""))
    return " ".join(value.lower().split())


def _plain_text_from_html(value):
    parser = JobPageParser()
    try:
        parser.feed(str(value or ""))
        return " ".join(parser.visible_parts)
    except Exception:
        return re.sub(r"<[^>]+>", " ", str(value or ""))


def _walk_job_postings(value):
    """Yield schema.org JobPosting objects from JSON-LD structures."""
    if isinstance(value, list):
        for item in value:
            yield from _walk_job_postings(item)
    elif isinstance(value, dict):
        types = value.get("@type", [])
        if isinstance(types, str):
            types = [types]

        if any(str(item).lower() == "jobposting" for item in types):
            yield value

        for key, child in value.items():
            if key != "@context":
                yield from _walk_job_postings(child)


def _location_from_jobposting(job):
    locations = job.get("jobLocation") or []
    if isinstance(locations, dict):
        locations = [locations]

    values = []

    for item in locations:
        if not isinstance(item, dict):
            continue

        address = item.get("address") or {}
        if isinstance(address, str):
            values.append(address)
            continue

        for key in (
            "streetAddress",
            "addressLocality",
            "addressRegion",
            "postalCode",
            "addressCountry"
        ):
            value = address.get(key)
            if isinstance(value, dict):
                value = value.get("name") or value.get("@id")
            if value:
                values.append(str(value))

    return ", ".join(dict.fromkeys(values))


def _identifier_from_jobposting(job):
    identifier = job.get("identifier") or ""

    if isinstance(identifier, dict):
        identifier = (
            identifier.get("value")
            or identifier.get("name")
            or ""
        )

    return str(identifier).strip()


def _location_matches(requested, actual, visible_text):
    if not requested:
        return True

    requested_norm = _normalise_text(requested)
    actual_norm = _normalise_text(actual)

    if requested_norm and actual_norm:
        if requested_norm in actual_norm or actual_norm in requested_norm:
            return True

    # For common "City, Country" inputs, require the city to appear.
    city = requested.split(",")[0].strip()
    city_norm = _normalise_text(city)

    return bool(city_norm and city_norm in _normalise_text(
        actual_norm + " " + visible_text
    ))


def search_custom_website(
    careers_url,
    job_title="",
    location="",
    job_id=None,
    job_url=None
):
    """
    Verify one user-supplied job detail page on the same host as
    the discovered official careers page.

    This adapter does not crawl arbitrary sites or infer legitimacy
    from a URL alone. It requires matching job-page content.
    """
    try:
        if not job_url:
            raise ValueError(
                "A specific job posting URL is required for custom careers sites."
            )

        careers_parsed = urlsplit(careers_url)
        job_parsed = urlsplit(job_url)

        careers_host = (careers_parsed.hostname or "").lower().rstrip(".")
        job_host = (job_parsed.hostname or "").lower().rstrip(".")

        if (
            careers_parsed.scheme not in ("http", "https")
            or job_parsed.scheme not in ("http", "https")
            or not careers_host
            or not job_host
            or job_parsed.username
            or job_parsed.password
            or job_host != careers_host
        ):
            raise ValueError(
                "Job posting URL must use the same host as the discovered careers page."
            )

        response = safe_get(job_url)

        final_host = (
            urlsplit(response.url).hostname or ""
        ).lower().rstrip(".")

        if final_host != careers_host:
            raise ValueError(
                "Job posting redirected away from the discovered careers host."
            )

        parser = JobPageParser()
        parser.feed(response.text[:2000000])

        visible_text = " ".join(parser.visible_parts)
        page_title = " ".join(parser.title_parts).strip()
        h1_title = " ".join(parser.h1_parts).strip()

        jsonld_jobs = []

        for block in parser.jsonld_blocks:
            try:
                payload = json.loads(block)
                jsonld_jobs.extend(_walk_job_postings(payload))
            except (json.JSONDecodeError, TypeError):
                continue

        # Prefer schema.org JobPosting data where available.
        structured = jsonld_jobs[0] if jsonld_jobs else {}

        official_title = (
            structured.get("title")
            or h1_title
            or parser.meta.get("og:title")
            or page_title
        )

        official_location = _location_from_jobposting(structured)

        if not official_location:
            for key in (
                "joblocation",
                "og:locality",
                "location"
            ):
                if parser.meta.get(key):
                    official_location = parser.meta[key]
                    break

        official_description = (
            structured.get("description")
            or parser.meta.get("description")
            or visible_text
        )

        official_description = _plain_text_from_html(
            official_description
        )

        structured_id = _identifier_from_jobposting(structured)
        page_url_lower = response.url.lower()
        visible_lower = visible_text.lower()

        title_matches = (
            bool(job_title)
            and _normalise_text(official_title)
            == _normalise_text(job_title)
        )

        location_matches = _location_matches(
            location,
            official_location,
            visible_text
        )

        id_matches = True
        if job_id:
            requested_id = str(job_id).strip().lower()
            id_matches = (
                requested_id in page_url_lower
                or requested_id == structured_id.lower()
                or requested_id in visible_lower
            )

        # Do not mark a page verified if essential job identity
        # information cannot be extracted.
        if not official_title or not visible_text:
            return {
                "status": "UNABLE_TO_VERIFY",
                "message": (
                    "The job page was reachable, but its job details "
                    "could not be extracted reliably."
                ),
                "total_jobs_checked": 1,
                "matches": []
            }

        if not title_matches or not location_matches or not id_matches:
            return {
                "status": "NO_RESULTS",
                "message": (
                    "The supplied job page did not match all requested "
                    "job details."
                ),
                "total_jobs_checked": 1,
                "matches": []
            }

        match = {
            "job_id": structured_id or (
                str(job_id) if job_id else ""
            ),
            "title": official_title,
            "location": official_location or location,
            "official_url": response.url,
            "description": official_description,
            "verification_method": (
                "SAME_OFFICIAL_CAREERS_HOST_AND_JOB_PAGE_CONTENT"
            ),
            "structured_jobposting_found": bool(structured)
        }

        return {
            "status": "RESULTS_FOUND",
            "total_jobs_checked": 1,
            "matches": [match]
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError
    ) as error:
        return {
            "status": "UNABLE_TO_VERIFY",
            "message": str(error),
            "matches": []
        }


def search_ats_jobs(
    careers_url,
    platform,
    job_title="",
    location="",
    job_id=None,
    job_url=None
):
    adapters = {
        "GREENHOUSE": search_greenhouse_jobs,
        "LEVER": search_lever_jobs,
        "ASHBY": search_ashby_jobs,
        "WORKDAY": search_workday_jobs,
        "SMARTRECRUITERS": search_smartrecruiters_jobs
    }

    platform = (platform or "UNKNOWN").upper()

    try:
        if platform == "CUSTOM_WEBSITE":
            return search_custom_website(
                careers_url,
                job_title,
                location,
                job_id,
                job_url
            )

        adapter = adapters.get(platform)

        if not adapter:
            return {
                "status": "UNABLE_TO_VERIFY",
                "message": f"No search adapter available for {platform}.",
                "matches": []
            }

        return adapter(
            careers_url,
            job_title,
            location,
            job_id
        )

    except Exception as error:
        return {
            "status": "UNABLE_TO_VERIFY",
            "message": str(error),
            "matches": []
        }
