
def decide_vacancy_status(
    search_status,
    results=None,
    submitted_job_title="",
    submitted_location="",
    submitted_job_id=None
):
    results = results or []

    # Search could not be completed
    if search_status != "RESULTS_FOUND":
        if search_status == "NO_RESULTS":
            return {
                "status": "NOT_FOUND",
                "finding": "No matching vacancy was found in the searched official listings."
            }

        return {
            "status": "UNABLE_TO_VERIFY",
            "finding": "Official vacancy verification could not be completed."
        }

    # A listing exists, but compare submitted details
    for item in results:
        job = item.get("official_job", item)
        differences = []

        official_title = (job.get("title") or "").strip()
        official_location = (job.get("location") or "").strip()
        official_id = str(job.get("job_id") or "").strip()

        if submitted_job_id and str(submitted_job_id).strip() != official_id:
            differences.append("JOB_ID_MISMATCH")

        if (
            submitted_job_title
            and submitted_job_title.strip().lower() != official_title.lower()
        ):
            differences.append("JOB_TITLE_MISMATCH")

        if (
            submitted_location
            and submitted_location.strip().lower() not in official_location.lower()
        ):
            differences.append("JOB_LOCATION_MISMATCH")

        if differences:
            return {
                "status": "DETAILS_MISMATCH",
                "finding": "The official vacancy exists, but submitted details conflict with the official listing.",
                "differences": differences,
                "official_job": job
            }

        return {
            "status": "DETAILS_MATCH",
            "finding": "The submitted vacancy details match an official listing. Recruiter identity and offer authenticity are not yet confirmed.",
            "official_job": job
        }

    return {
        "status": "NOT_FOUND",
        "finding": "No matching vacancy was found."
    }
