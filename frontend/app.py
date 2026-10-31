import os
import html
from datetime import datetime

import requests
import streamlit as st


# =========================================================
# CONFIGURATION — matches the existing FastAPI backend
# =========================================================
API_BASE_URL = os.getenv("JOBSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
ANALYZE_URL = f"{API_BASE_URL}/api/v1/analyze"
HISTORY_URL = f"{API_BASE_URL}/api/v1/history"
HEALTH_URL = f"{API_BASE_URL}/health"
REQUEST_TIMEOUT = (5, 120)

st.set_page_config(
    page_title="JobShield AI | Recruitment Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# STYLING — retain the existing dark, futuristic visual style
# =========================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700;800&display=swap');
:root { --bg:#f5f7fb; --panel:#fff; --border:#e5e7eb; --red:#dc2626; --red-dark:#b91c1c; --text:#111827; --muted:#64748b; }
.stApp { background:linear-gradient(135deg,#fff 0%,#f7f8fc 58%,#fff5f5 100%); color:var(--text); font-family:'DM Sans',sans-serif; }
[data-testid="stHeader"] { background:rgba(255,255,255,.92); }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--border); }
[data-testid="stSidebar"] * { color:var(--text); }
.block-container { padding-top:1.5rem; padding-bottom:3rem; max-width:1500px; }
h1,h2,h3,h4 { color:var(--text)!important; font-family:'DM Sans',sans-serif; }
p,label,.stMarkdown,[data-testid="stCaptionContainer"] { color:var(--text); }
.hero { background:linear-gradient(110deg,#fff 0%,#fff9f7 60%,#fee2e2 100%); border:1px solid #f3d2d0; border-radius:18px; padding:22px 28px; margin-bottom:22px; box-shadow:0 12px 32px rgba(80,25,25,.055); }
.editorial-hero { background:linear-gradient(105deg,rgba(255,255,255,.98) 0%,rgba(255,250,248,.96) 58%,rgba(255,235,231,.96) 100%); border:1px solid #f1d6d2; border-radius:20px; padding:30px 34px; margin:6px 0 24px; position:relative; overflow:hidden; box-shadow:0 14px 38px rgba(80,25,25,.06); }
.editorial-kicker { color:#b91c1c; text-transform:uppercase; letter-spacing:2.4px; font-size:10px; font-weight:800; }
.editorial-title { font-family:'Playfair Display',Georgia,serif; font-size:clamp(34px,4vw,52px); line-height:1.04; font-weight:700; letter-spacing:-1.5px; color:#171717; margin:13px 0 12px; max-width:640px; }
.editorial-title span { color:#c51f2b; }
.editorial-copy { color:#596273; font-size:14px; max-width:590px; line-height:1.7; }
.editorial-art { min-height:205px; border-radius:16px; background:radial-gradient(circle at 50% 45%,rgba(255,255,255,.13),transparent 34%),radial-gradient(circle at 70% 25%,rgba(248,113,113,.28),transparent 28%),linear-gradient(135deg,#280d12,#65151c 55%,#a51d27); display:flex; align-items:center; justify-content:center; color:#fff; position:relative; overflow:hidden; }
.editorial-art:before { content:' '; position:absolute; width:210px; height:210px; border:1px solid rgba(255,255,255,.22); border-radius:50%; box-shadow:0 0 0 22px rgba(255,255,255,.035),0 0 0 48px rgba(255,255,255,.025),0 0 70px rgba(248,113,113,.3); }
.editorial-art-inner { position:relative; text-align:center; z-index:1; }
.editorial-art-inner strong { display:block; font-family:'Playfair Display',Georgia,serif; font-size:24px; }
.editorial-art-inner small { color:#ffd9d9; letter-spacing:1.5px; font-size:9px; text-transform:uppercase; }
.section-heading { font-family:'Playfair Display',Georgia,serif; font-size:25px; font-weight:700; color:#171717; margin:20px 0 4px; }

.brand { font-family:'DM Sans',sans-serif; font-size:30px; font-weight:800; letter-spacing:-1px; color:#111827; }
.brand span { color:var(--red); }
.hero-subtitle { color:#475569; font-size:14px; margin-top:8px; }
.section-label { color:var(--red); text-transform:uppercase; letter-spacing:2px; font-size:11px; font-weight:800; margin-bottom:8px; }
.metric-card { background:#fff; border:1px solid #e8e5e5; border-radius:13px; padding:18px; min-height:105px; box-shadow:0 5px 18px rgba(15,23,42,.035); transition:transform .18s ease,box-shadow .18s ease; }\n.metric-card:hover { transform:translateY(-2px); box-shadow:0 10px 24px rgba(15,23,42,.07); }
.metric-label { color:var(--muted); font-size:11px; font-weight:700; letter-spacing:.5px; }
.metric-value { color:#111827; font-size:25px; font-weight:800; margin-top:8px; overflow-wrap:anywhere; }
.metric-note { color:var(--red-dark); font-size:11px; margin-top:4px; }
.verdict { border-radius:14px; padding:19px; border:1px solid var(--border); background:#fff; margin:10px 0 18px; box-shadow:0 5px 18px rgba(15,23,42,.04); }
.verdict-high { border-left:5px solid #dc2626; background:#fff7f7; }
.verdict-medium { border-left:5px solid #d97706; background:#fffbeb; }
.verdict-low { border-left:5px solid #16a34a; background:#f0fdf4; }
.verdict-title { font-size:22px; font-weight:800; color:#111827; }
.verdict-caption { color:#64748b; font-size:13px; margin-top:5px; }
div.stButton>button,div.stFormSubmitButton>button { background:linear-gradient(100deg,#dc2626,#b91c1c); color:#fff; border:1px solid #dc2626; border-radius:10px; font-weight:700; min-height:42px; }
div.stButton>button:hover,div.stFormSubmitButton>button:hover { background:#b91c1c; border-color:#991b1b; color:#fff; box-shadow:0 5px 16px rgba(220,38,38,.18); }
div[data-testid="stForm"] { background:#fff; border:1px solid #e8e5e5; border-radius:16px; padding:22px; box-shadow:0 8px 26px rgba(15,23,42,.045); }
input,textarea { background-color:#fff!important; color:#111827!important; border-color:#d1d5db!important; }
[data-baseweb="select"]>div { background-color:#fff!important; border-color:#d1d5db!important; }
[data-testid="stMetric"] { background:#fff; border:1px solid var(--border); padding:13px; border-radius:12px; box-shadow:0 4px 14px rgba(15,23,42,.035); }
[data-testid="stMetricLabel"] { color:var(--muted)!important; }
[data-testid="stMetricValue"] { color:#111827!important; }
[data-testid="stExpander"] { background:#fff; border:1px solid var(--border); border-radius:11px; }
[data-testid="stExpander"] summary { color:#111827; }
[data-testid="stTabs"] button[aria-selected="true"] { color:var(--red)!important; border-bottom-color:var(--red)!important; }
[data-testid="stRadio"] label { color:#1f2937!important; }
.stAlert { border-radius:10px; }
hr { border-color:var(--border); }
footer,#MainMenu { visibility:hidden; }
.small-muted { color:var(--muted); font-size:12px; }
a { color:#b91c1c!important; }
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# API HELPERS
# =========================================================
def _decode_response(response):
    try:
        return response.json()
    except ValueError:
        return None


def api_get(url):
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = _decode_response(response)
        if data is None:
            return None, "Backend returned an invalid JSON response."
        return data, None
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to FastAPI. Start the backend and check JOBSHIELD_API_URL."
    except requests.exceptions.Timeout:
        return None, "Backend request timed out. Please retry."
    except requests.exceptions.HTTPError:
        return None, f"Backend returned HTTP {response.status_code}: {response.text[:500]}"
    except requests.exceptions.RequestException as exc:
        return None, f"Request failed: {exc}"


def api_analyze(payload):
    try:
        response = requests.post(ANALYZE_URL, json=payload, timeout=REQUEST_TIMEOUT)
        if response.status_code == 422:
            body = _decode_response(response) or response.text
            return None, f"Input validation failed: {body}"
        response.raise_for_status()
        data = _decode_response(response)
        if not isinstance(data, dict):
            return None, "Backend returned an unexpected or invalid JSON response."
        return data, None
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to FastAPI. Check that the backend is running."
    except requests.exceptions.Timeout:
        return None, "Analysis timed out. The verification services may be taking too long. Please retry."
    except requests.exceptions.HTTPError:
        return None, f"Backend error ({response.status_code}): {response.text[:1000]}"
    except requests.exceptions.RequestException as exc:
        return None, f"Request failed: {exc}"


def get_health():
    data, error = api_get(HEALTH_URL)
    if error:
        return None, error
    if not isinstance(data, dict):
        return None, "Health endpoint returned an unexpected response."
    return data, None


def get_history():
    data, error = api_get(HISTORY_URL)
    if error:
        return None, error
    if not isinstance(data, list):
        return None, "History endpoint returned an unexpected response."
    return data, None


# =========================================================
# DISPLAY HELPERS
# =========================================================
def metric_card(label, value, note=""):
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    safe_note = html.escape(str(note))
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{safe_label}</div>'
        f'<div class="metric-value">{safe_value}</div><div class="metric-note">{safe_note}</div></div>',
        unsafe_allow_html=True,
    )


def verdict_style(verdict):
    mapping = {
        "HIGH_CONCERN": ("verdict-high", "HIGH CONCERN", "Potentially dangerous indicators were detected. Do not proceed without resolving them."),
        "LOW_CONCERN": ("verdict-low", "LOW CONCERN", "The configured checks passed. This is not a guarantee that the opportunity is safe."),
        "NEEDS_VERIFICATION": ("verdict-medium", "NEEDS VERIFICATION", "There is insufficient verified evidence to establish that this opportunity is genuine."),
    }
    return mapping.get(verdict, mapping["NEEDS_VERIFICATION"])


def display_verdict(verdict):
    css_class, title, description = verdict_style(verdict)
    st.markdown(
        f'<div class="verdict {css_class}"><div class="section-label">JOBSHIELD RISK ASSESSMENT</div>'
        f'<div class="verdict-title">{html.escape(title)}</div>'
        f'<div class="verdict-caption">{html.escape(description)}</div></div>',
        unsafe_allow_html=True,
    )


def display_model(model):
    st.markdown("### ML prediction")
    if not isinstance(model, dict):
        st.info("The ML model did not return a prediction for this analysis.")
        return

    score = model.get("score")
    score_type = model.get("score_type", "uncalibrated_model_score")
    
    st.metric(
        "Model score",
        f"{float(score):.4f}"
        if isinstance(score, (int, float))
        else "Not available"
    )

    st.caption(
        "This is an uncalibrated model score, not a confirmed probability of fraud. "
        f"Score type: {score_type}."
    )


def display_evidence(evidence):
    if not isinstance(evidence, list) or not evidence:
        st.info("No evidence items were returned by the backend.")
        return

    for index, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "UNKNOWN"))
        status = str(item.get("status", "UNKNOWN"))
        severity = str(item.get("severity", "UNKNOWN"))
        finding = str(item.get("finding", "No finding provided."))
        source_url = item.get("source_url")
        checked_at = item.get("checked_at")
        with st.expander(f"{index}. {category.replace('_', ' ')}  |  {status}", expanded=(severity == "HIGH")):
            col1, col2 = st.columns(2)
            col1.write(f"**Status:** `{status}`")
            col2.write(f"**Severity:** `{severity}`")
            st.write(finding)
            if isinstance(source_url, str) and source_url.startswith(("https://", "http://")):
                st.markdown(f"[Open evidence source]({source_url})")
            if checked_at:
                st.caption(f"Checked at: {checked_at}")


def display_vacancy(vacancy):
    if not isinstance(vacancy, dict):
        st.info("No vacancy verification result was returned.")
        return

    status = vacancy.get("status", "UNKNOWN")
    st.write(f"**Vacancy verification status:** `{status}`")
    st.write(vacancy.get("finding", "No finding provided."))
    if status in ("UNABLE_TO_VERIFY", "MISSING"):
        st.warning("Unable to verify does not mean the vacancy is fraudulent. The system could not confirm it using the available sources.")
    for key, label in (
        ("discovery", "Careers page discovery details"),
        ("official_job", "Official vacancy details"),
        ("description_comparisons", "Description comparison details"),
        ("search_failures", "Search adapter details"),
    ):
        value = vacancy.get(key)
        if value:
            with st.expander(label):
                st.json(value)
    st.caption(f"Checked at: {vacancy.get('checked_at', 'Not provided')}")


def display_analysis(data):
    if not isinstance(data, dict):
        st.error("Unexpected analysis response format.")
        st.write(data)
        return

    st.markdown("## Analysis result")
    analysis_id = data.get("analysis_id", "Not provided")
    verdict = data.get("verdict", "NEEDS_VERIFICATION")
    st.caption(f"Analysis ID: {analysis_id}")
    display_verdict(verdict)

    evidence = data.get("evidence") if isinstance(data.get("evidence"), list) else []
    high_count = sum(1 for item in evidence if isinstance(item, dict) and item.get("severity") == "HIGH")
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("TOTAL EVIDENCE", len(evidence), "Findings returned by backend")
    with c2:
        metric_card("HIGH SEVERITY", high_count, "High severity findings")
    with c3:
        metric_card("FINAL VERDICT", str(verdict).replace("_", " "), "Evidence-based backend decision")

    display_model(data.get("model"))
    tabs = st.tabs(["Evidence", "Vacancy verification", "Recommendations", "Limitations", "Raw response"])
    with tabs[0]:
        display_evidence(evidence)
    with tabs[1]:
        display_vacancy(data.get("vacancy_verification"))
    with tabs[2]:
        recommendations = data.get("recommendations") or []
        if recommendations:
            for recommendation in recommendations:
                st.markdown(f"- {recommendation}")
        else:
            st.info("No recommendations returned.")
    with tabs[3]:
        limitations = data.get("limitations") or []
        if limitations:
            for limitation in limitations:
                st.markdown(f"- {limitation}")
        else:
            st.info("No limitations returned.")
    with tabs[4]:
        st.json(data)


def render_history_record(item):
    title = f"{item.get('company_name') or 'Unknown company'} — {item.get('job_title') or 'Unknown role'}"
    verdict = item.get("verdict", "UNKNOWN")
    analysis_id = item.get("analysis_id", "")
    with st.expander(f"{title} | {verdict} | {analysis_id}"):
        st.write(f"**Analysis ID:** {analysis_id}")
        st.write(f"**Verdict:** `{verdict}`")
        st.write(f"**Company:** {item.get('company_name') or 'Not provided'}")
        st.write(f"**Job title:** {item.get('job_title') or 'Not provided'}")
        st.write(f"**Created at:** {item.get('created_at', 'Not provided')}")
        st.markdown("#### Evidence")
        display_evidence(item.get("evidence") or [])
        st.markdown("#### Recommendations")
        recommendations = item.get("recommendations") or []
        if recommendations:
            for recommendation in recommendations:
                st.markdown(f"- {recommendation}")
        else:
            st.caption("No recommendations stored for this record.")


# =========================================================
# NAVIGATION CALLBACKS
# =========================================================
def navigate_to_page(page_name):
    """Update the navigation radio before Streamlit recreates its widgets."""
    st.session_state.page = page_name


# =========================================================
# SESSION STATE
# =========================================================
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "latest_analysis" not in st.session_state:
    st.session_state.latest_analysis = None
if "last_analysis_error" not in st.session_state:
    st.session_state.last_analysis_error = None


# =========================================================
# SIDEBAR / NAVIGATION / HEALTH
# =========================================================
with st.sidebar:
    st.markdown(
        '<div style="padding:14px 5px 22px;display:flex;gap:10px;align-items:center">'
        '<div style="font-size:29px;background:#fee2e2;border-radius:11px;padding:7px">🛡️</div>'
        '<div><div style="font-size:19px;font-weight:800;letter-spacing:-.7px;color:#171717">JobShield <span style="color:#c51f2b">AI</span></div>'
        '<div style="color:#7b8493;font-size:9px;letter-spacing:1.5px">RECRUITMENT INTELLIGENCE</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.radio("NAVIGATION", ["Dashboard", "Analyse Job", "Analysis History"], key="page")
    st.markdown("---")
    if st.button("↻ Check backend status", use_container_width=True):
        st.session_state.health_checked_at = datetime.now().isoformat(timespec="seconds")
        st.rerun()
    health, health_error = get_health()
    if health_error:
        st.error("BACKEND OFFLINE")
        st.caption(health_error)
    else:
        st.success("BACKEND ONLINE")
        st.caption(f"API: {API_BASE_URL}")
        st.caption("ML model: Loaded" if health.get("model_loaded") is True else "ML model: Not loaded")
        if st.session_state.get("health_checked_at"):
            st.caption(f"Last manual check: {st.session_state.health_checked_at}")
    st.markdown("---")
    st.caption("JOBSHIELD AI • VERSION 1.0")
    st.caption("Recruitment fraud detection and vacancy verification")


# =========================================================
# GLOBAL HEADER
# =========================================================
st.markdown(
    '<div class="hero" style="display:flex;align-items:center;justify-content:space-between;gap:18px">'
    '<div><div class="section-label">SAFE JOBS • REAL OPPORTUNITIES • A FRAUD-FREE FUTURE</div>'
    '<div class="brand">JobShield <span>AI</span></div>'
    '<div class="hero-subtitle">Recruitment intelligence that helps you verify opportunities before you apply.</div></div>'
    '<div style="font-size:38px;background:#fee2e2;border:1px solid #fecaca;border-radius:15px;padding:12px 17px">🛡️</div></div>',
    unsafe_allow_html=True,
)


# =========================================================
# DASHBOARD
# =========================================================
if st.session_state.page == "Dashboard":
    st.markdown(
        '<div class="editorial-hero"><div class="editorial-kicker">Your recruitment safety desk</div>'
        '<div class="editorial-title">Protection for your next<br>big <span>opportunity.</span></div>'
        '<div class="editorial-copy">Review suspicious recruitment activity, cross-check job postings against employer career listings, and make better-informed decisions before sharing your details.</div></div>',
        unsafe_allow_html=True,
    )
    st.button(
        "Analyse a job opportunity  →",
        on_click=navigate_to_page,
        args=("Analyse Job",),
        key="dashboard_analyse_new_job",
    )
    st.caption("A live overview from your JobShield verification backend.")
    health, health_error = get_health()
    history, history_error = get_history()

    if health_error:
        st.error(f"Health check unavailable: {health_error}")
    if history_error:
        st.error(f"History unavailable: {history_error}")

    if history is not None:
        total = len(history)
        high = sum(1 for item in history if item.get("verdict") == "HIGH_CONCERN")
        needs = sum(1 for item in history if item.get("verdict") == "NEEDS_VERIFICATION")
        low = sum(1 for item in history if item.get("verdict") == "LOW_CONCERN")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("ANALYSES RETURNED", total, "History endpoint limit: latest 100")
        with c2:
            metric_card("HIGH CONCERN", high, "Saved high-concern verdicts")
        with c3:
            metric_card("NEEDS VERIFICATION", needs, "Saved incomplete-verification verdicts")
        with c4:
            metric_card("LOW CONCERN", low, "Saved low-concern verdicts")
    else:
        st.info("Analysis statistics are unavailable while the history service cannot be reached.")

    st.markdown('<div class="section-heading">System status</div>', unsafe_allow_html=True)
    if health is not None:
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("API STATUS", str(health.get("status", "UNKNOWN")).upper(), "FastAPI service")
        with c2:
            metric_card("DATABASE", str(health.get("database", "UNKNOWN")).upper(), "Backend-reported status")
        with c3:
            metric_card("ML MODEL", "LOADED" if health.get("model_loaded") else "NOT LOADED", "Model availability")
    else:
        st.warning("System health details could not be retrieved.")

    st.markdown('<div class="section-heading">Recent analyses</div>', unsafe_allow_html=True)
    if history:
        for item in history[:5]:
            with st.container(border=True):
                a, b, c = st.columns([2, 2, 1])
                with a:
                    st.write(f"**{item.get('company_name') or 'Unknown company'}**")
                    st.caption(item.get("job_title") or "Job title unavailable")
                with b:
                    st.write(f"`{item.get('verdict', 'UNKNOWN')}`")
                    st.caption(item.get("analysis_id", ""))
                with c:
                    st.caption(str(item.get("created_at", "")))
    elif history is not None:
        st.info("No saved analyses yet. Open Analyse Job to run your first check.")


# =========================================================
# ANALYSE JOB — request body matches JobAnalysisRequest schema
# =========================================================
elif st.session_state.page == "Analyse Job":
    st.markdown('<div class="section-heading">Analyse job opportunity</div>', unsafe_allow_html=True)
    st.caption("Only the job description is mandatory. Add the other details you have for stronger verification.")

    with st.form("job_analysis_form", clear_on_submit=False):
        st.markdown('<div class="section-heading" style="font-size:21px;margin-top:0">Job information</div>', unsafe_allow_html=True)
        job_text = st.text_area(
            "Job description / recruitment message *",
            placeholder="Paste the complete job description, recruiter message, payment instructions or offer details here...",
            height=230,
            max_chars=20000,
        )
        left, right = st.columns(2)
        with left:
            company_name = st.text_input("Company name", placeholder="e.g. Microsoft")
            job_title = st.text_input("Job title", placeholder="e.g. Software Engineer")
            job_id = st.text_input("Official job ID", placeholder="If available")
            recruiter_email = st.text_input("Recruiter email", placeholder="recruiter@company.com")
        with right:
            company_website = st.text_input("Company website", placeholder="https://company.com")
            job_location = st.text_input("Job location", placeholder="e.g. Bengaluru, India")
            job_url = st.text_input("Job posting URL", placeholder="https://...")
            careers_url = st.text_input("Careers page URL", placeholder="If known")
        submitted = st.form_submit_button("🛡️ ANALYSE JOB OPPORTUNITY", use_container_width=True)

    if submitted:
        clean_text = (job_text or "").strip()
        if len(clean_text) < 10:
            st.error("Please enter a job description containing at least 10 characters.")
        else:
            # Send only fields accepted by backend/api/schemas.py.
            payload = {
                "job_text": clean_text,
                "company_name": company_name.strip() or None,
                "company_website": company_website.strip() or None,
                "job_url": job_url.strip() or None,
                "recruiter_email": recruiter_email.strip() or None,
                "job_title": job_title.strip() or None,
                "job_location": job_location.strip() or None,
                "job_id": job_id.strip() or None,
                "careers_url": careers_url.strip() or None,
            }
            with st.spinner("Analysing the recruitment message and checking available verification sources..."):
                result, error = api_analyze(payload)
            if error:
                st.session_state.last_analysis_error = error
                st.error(error)
            else:
                st.session_state.latest_analysis = result
                st.session_state.last_analysis_error = None
                st.success("Analysis completed. The backend returned a result.")

    if st.session_state.last_analysis_error and not st.session_state.latest_analysis:
        st.caption("No successful analysis is currently available in this session.")
    if st.session_state.latest_analysis:
        st.markdown("---")
        display_analysis(st.session_state.latest_analysis)


# =========================================================
# ANALYSIS HISTORY
# =========================================================
elif st.session_state.page == "Analysis History":
    st.markdown('<div class="section-heading">Analysis history</div>', unsafe_allow_html=True)
    st.caption("Records retrieved from the FastAPI history endpoint (latest 100 records).")
    if st.button("↻ Refresh history"):
        st.rerun()
    history, error = get_history()
    if error:
        st.error(error)
    elif not history:
        st.info("No saved analysis records found. Run an analysis to populate history.")
    else:
        st.markdown(f"**{len(history)} records returned.**")
        search = st.text_input("Search by company, job title, verdict or analysis ID", placeholder="Search...")
        query = search.strip().casefold()
        filtered = [
            item for item in history
            if query in " ".join(str(item.get(key, "")) for key in ("analysis_id", "company_name", "job_title", "verdict")).casefold()
        ]
        if filtered:
            for item in filtered:
                render_history_record(item)
        else:
            st.info("No records match your search.")


# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#64748b;font-size:11px;padding:10px">'
    'JOBSHIELD AI • RECRUITMENT FRAUD DETECTION & VACANCY VERIFICATION<br>'
    'Results depend on available checks and evidence. A low-concern result is not a guarantee that a job offer is safe.'
    '</div>',
    unsafe_allow_html=True,
)
