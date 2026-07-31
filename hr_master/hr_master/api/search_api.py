"""Search API for HR Master - Job Portal Integration"""

from __future__ import unicode_literals

import frappe
from frappe import _
from hr_master.security.rate_limiter import rate_limit_decorator

# ------------------------------------------
# Search Endpoints
# ------------------------------------------


@frappe.whitelist()
@rate_limit_decorator
def search_candidates_for_jd(job_description_name):
    """Trigger candidate search across enabled job portals for a JD."""
    try:
        jd = frappe.get_doc("Job Description", job_description_name)

        if not jd:
            return {"status": "error", "message": _("Job Description not found")}

        # Create a new Job Portal Search record
        search = frappe.new_doc("Job Portal Search")
        search.job_description = job_description_name
        search.job_title = jd.job_title
        search.search_keywords = generate_search_keywords(jd)
        search.status = "Queued"

        # Determine which portals to search
        config = frappe.get_single("Job Portal Config")
        portals = config.get_enabled_portals()
        search.search_linkedin = 1 if "LinkedIn" in portals else 0
        search.search_naukri = 1 if "Naukri" in portals else 0
        search.search_indeed = 1 if "Indeed" in portals else 0
        search.search_monster = 1 if "Monster" in portals else 0
        search.search_serpapi = 1 if "SerpAPI" in portals else 0
        search.search_demo = 1 if "Demo" in portals else 0

        search.save(ignore_permissions=True)

        # Update JD status
        jd.db_set("portal_search_status", "Searching")

        # Enqueue background job for actual searching
        frappe.enqueue(
            method="hr_master.tasks.celery.process_candidate_search",
            queue="long",
            timeout=600,
            search_name=search.name,
            job_description_name=job_description_name,
        )

        return {
            "status": "success",
            "message": _("Search initiated for {0}").format(jd.job_title),
            "search_name": search.name,
        }

    except Exception as e:
        frappe.log_error(
            message=f"Error initiating search: {str(e)}",
            title="Portal Search Error",
        )
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
@rate_limit_decorator
def import_search_results(search_name):
    """Import search results as Candidate documents."""
    try:
        search = frappe.get_doc("Job Portal Search", search_name)
        if not search:
            return {"status": "error", "message": _("Search record not found")}

        imported = search.import_results_to_candidates()

        return {
            "status": "success",
            "imported_count": imported,
            "message": _("{0} candidates imported successfully").format(imported),
        }

    except Exception as e:
        frappe.log_error(
            message=f"Error importing search results: {str(e)}",
            title="Candidate Import Error",
        )
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
@rate_limit_decorator
def import_single_search_result(search_name, result_name):
    """Import a single portal search result row as a Candidate document."""
    try:
        search = frappe.get_doc("Job Portal Search", search_name)
        if not search:
            return {"status": "error", "message": _("Search record not found")}

        result = next(
            (r for r in search.search_results if r.name == result_name),
            None,
        )
        if not result:
            return {"status": "error", "message": _("Result row not found")}

        imported = search.import_result_to_candidate(result)
        if imported:
            search.save(ignore_permissions=True)
            return {
                "status": "success",
                "imported_count": 1,
                "message": _("Imported {0}").format(result.candidate_name),
            }

        # Not imported: either it was already imported (is_imported / Imported)
        # or the import attempt failed (import_status set to Failed on the row).
        if result.is_imported or result.import_status == "Imported":
            return {"status": "error", "message": _("Result already imported")}
        return {"status": "error", "message": _("Import failed — check the Error Log")}

    except Exception as e:
        frappe.log_error(
            message=f"Error importing single result: {str(e)}",
            title="Candidate Import Error",
        )
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
@rate_limit_decorator
def get_search_status(search_name):
    """Get the status of a portal search."""
    try:
        search = frappe.get_doc("Job Portal Search", search_name)
        return {
            "status": search.status,
            "total_found": search.total_candidates_found,
            "linkedin": search.linkedin_results,
            "naukri": search.naukri_results,
            "indeed": search.indeed_results,
            "monster": search.monster_results,
            "serpapi": search.serpapi_results,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_jd_search_status(job_description_name):
    """Get the live search state for a JD (used by the portal page poller).

    Returns whether any background search is still in progress plus the latest
    per-portal counts and the number of ranked candidates, so the JD page can
    auto-refresh itself once the queued search finishes.
    """
    from hr_master.api.portal_actions import has_hr_role

    if frappe.session.user == "Guest" or not has_hr_role():
        return {"status": "error", "message": _("Not permitted")}

    try:
        jd = frappe.get_doc("Job Description", job_description_name)
        searches = frappe.get_all(
            "Job Portal Search",
            fields=[
                "name",
                "status",
                "total_candidates_found",
                "linkedin_results",
                "naukri_results",
                "indeed_results",
                "monster_results",
                "serpapi_results",
            ],
            filters={"job_description": job_description_name},
            order_by="search_date desc",
            limit_page_length=20,
        )
        in_progress = jd.portal_search_status == "Searching" or any(
            s.status in ("Queued", "In Progress") for s in searches
        )
        return {
            "status": "success",
            "in_progress": bool(in_progress),
            "portal_search_status": jd.portal_search_status,
            "searches": searches,
            "ranking_count": frappe.db.count(
                "Candidate Ranking", filters={"job_description": job_description_name}
            ),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ------------------------------------------
# Helper Functions
# ------------------------------------------


def generate_search_keywords(jd):
    """Generate search keywords from a Job Description."""
    keywords = [jd.job_title]

    if jd.required_skills:
        for skill in jd.required_skills:
            skill_name = frappe.db.get_value("Skill", skill.skill, "skill_name")
            if skill_name:
                keywords.append(skill_name)

    if jd.location:
        keywords.append(jd.location)

    return ", ".join(keywords)


# ------------------------------------------
# Portal Search Implementations
# ------------------------------------------


def search_linkedin(search_name, jd_name, keywords):
    """Search LinkedIn for candidates matching the JD."""
    config = frappe.get_single("Job Portal Config")
    if not config.linkedin_enabled:
        return []

    try:
        # Simulated LinkedIn API call - replace with actual API integration
        results = []

        if config.linkedin_api_key:
            # TODO: Implement actual LinkedIn API v2 search
            # Example: LinkedIn People Search API
            pass

        return results

    except Exception as e:
        frappe.log_error(
            message=f"LinkedIn search error: {str(e)}",
            title="LinkedIn Search Error",
        )
        return []


def search_naukri(search_name, jd_name, keywords):
    """Search Naukri for candidates matching the JD."""
    config = frappe.get_single("Job Portal Config")
    if not config.naukri_enabled:
        return []

    try:
        results = []

        if config.naukri_api_key:
            # TODO: Implement actual Naukri API integration
            pass

        return results

    except Exception as e:
        frappe.log_error(
            message=f"Naukri search error: {str(e)}",
            title="Naukri Search Error",
        )
        return []


def search_indeed(search_name, jd_name, keywords):
    """Search Indeed for candidates matching the JD (legacy Publisher API).

    Note: Indeed retired the free Publisher API program; this endpoint only
    still works for Publisher IDs obtained before the shutdown. It fails
    gracefully (returns []) when the API is unavailable or the ID is invalid.
    """
    config = frappe.get_single("Job Portal Config")
    if not config.indeed_enabled:
        return []

    publisher_id = config.indeed_publisher_id
    if not publisher_id:
        return []

    try:
        import requests

        limit = config.indeed_search_limit or 25
        country = config.default_country or ""
        user_ip = _get_client_ip()

        params = {
            "publisher": publisher_id,
            "v": "2",
            "format": "json",
            "q": keywords,
            "l": country,
            "co": country,
            "userip": user_ip,
            "useragent": _get_user_agent(),
            "start": "0",
            "limit": str(limit),
            "sort": "relevance",
        }

        response = requests.get(
            "https://api.indeed.com/ads/apisearch",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for job in (data.get("results") or [])[:limit]:
            results.append({
                "name": job.get("jobtitle") or job.get("company") or "Unknown",
                "url": job.get("url") or "",
                "title": job.get("jobtitle") or "",
                "company": job.get("company") or "",
                "location": job.get("formattedLocation") or "",
                "skills": job.get("snippet") or "",
                "experience": 0,
                "source_url": job.get("url") or "",
            })

        return results

    except Exception as e:
        frappe.log_error(
            message=f"Indeed search error: {str(e)}",
            title="Indeed Search Error",
        )
        return []


def search_serpapi(search_name, jd_name, keywords):
    """Search SerpAPI (Google Jobs) for candidates matching the JD.

    SerpAPI's Google Jobs engine returns live job postings; each posting is
    mapped into a candidate-like search result so the existing import & rank
    pipeline works unchanged. Requires a SerpAPI API key (free tier: 100
    searches/month).
    """
    config = frappe.get_single("Job Portal Config")
    if not config.serpapi_enabled:
        return []

    api_key = config.serpapi_api_key
    if not api_key:
        return []

    try:
        import requests

        limit = config.serpapi_search_limit or 10
        country = config.serpapi_country or config.default_country or "us"

        params = {
            "engine": "google_jobs",
            "q": keywords,
            "gl": country,
            "hl": "en",
            "api_key": api_key,
        }

        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            frappe.log_error(
                message=f"SerpAPI returned an error: {data['error']}",
                title="SerpAPI Search Error",
            )
            return []

        results = []
        for job in (data.get("jobs_results") or [])[:limit]:
            description = job.get("description") or ""
            skills = _extract_skills_from_description(description)

            results.append({
                "name": job.get("company_name") or job.get("title") or "Unknown",
                "url": job.get("job_id") or job.get("apply_link") or "",
                "title": job.get("title") or "",
                "company": job.get("company_name") or "",
                "location": job.get("location") or "",
                "skills": skills,
                "experience": _extract_experience_years(description),
                "source_url": job.get("apply_link") or job.get("job_id") or "",
            })

        return results

    except Exception as e:
        frappe.log_error(
            message=f"SerpAPI search error: {str(e)}",
            title="SerpAPI Search Error",
        )
        return []


def _get_client_ip():
    """Best-effort client IP for APIs that require userip."""
    try:
        return frappe.local.request_ip or "1.2.3.4"
    except Exception:
        return "1.2.3.4"


def _get_user_agent():
    """User agent for the Indeed Publisher API."""
    return "Mozilla/5.0 (HR Master Recruiting; +frappe)"


def _extract_skills_from_description(description):
    """Extract a concise skills/snippet summary from a job description."""
    if not description:
        return ""
    # Truncate to a reasonable length to keep the search record tidy
    return " ".join(description.split())[:1500]


def _extract_experience_years(description):
    """Best-effort numeric years of experience from a job description."""
    if not description:
        return 0
    import re

    match = re.search(r"(\d+)\s*\+?\s*(?:years|yrs)", description, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0
    return 0


def search_monster(search_name, jd_name, keywords):
    """Search Monster for candidates matching the JD."""
    config = frappe.get_single("Job Portal Config")
    if not config.monster_enabled:
        return []

    try:
        results = []

        if config.monster_api_key:
            # TODO: Implement Monster API integration
            pass

        return results

    except Exception as e:
        frappe.log_error(
            message=f"Monster search error: {str(e)}",
            title="Monster Search Error",
        )
        return []


# ------------------------------------------
# Demo Data Mode (zero-key sample candidates)
# ------------------------------------------

DEMO_CANDIDATES = [
    {"name": "Aarav Sharma", "title": "Senior Full Stack Developer", "company": "TechNova Solutions", "location": "Bengaluru", "skills": ["Python", "React", "Node.js", "SQL", "Docker", "AWS"], "experience": 7},
    {"name": "Priya Patel", "title": "Backend Developer", "company": "CloudPeak Systems", "location": "Pune", "skills": ["Python", "Django", "PostgreSQL", "AWS", "REST API"], "experience": 5},
    {"name": "Rohan Mehta", "title": "Frontend Developer", "company": "PixelWorks", "location": "Mumbai", "skills": ["React", "TypeScript", "JavaScript", "Next.js", "Tailwind CSS"], "experience": 4},
    {"name": "Sneha Reddy", "title": "Data Scientist", "company": "InsightLabs", "location": "Hyderabad", "skills": ["Python", "SQL", "TensorFlow", "Pandas", "Machine Learning", "Statistics"], "experience": 6},
    {"name": "Vikram Singh", "title": "DevOps Engineer", "company": "InfraCore", "location": "Gurugram", "skills": ["Docker", "Kubernetes", "AWS", "CI/CD", "Terraform", "Linux"], "experience": 8},
    {"name": "Ananya Iyer", "title": "Data Analyst", "company": "MarketPulse Analytics", "location": "Chennai", "skills": ["SQL", "Excel", "Tableau", "Power BI", "Python"], "experience": 3},
    {"name": "Karthik Nair", "title": "Mobile App Developer", "company": "AppFleet", "location": "Kochi", "skills": ["Flutter", "Dart", "React Native", "Firebase", "Kotlin"], "experience": 5},
    {"name": "Divya Krishnan", "title": "Machine Learning Engineer", "company": "NeuralEdge AI", "location": "Bengaluru", "skills": ["Python", "PyTorch", "Scikit-learn", "NLP", "AWS"], "experience": 4},
    {"name": "Rahul Verma", "title": "Java Developer", "company": "BankSys Technologies", "location": "Noida", "skills": ["Java", "Spring Boot", "Hibernate", "Microservices", "MySQL"], "experience": 9},
    {"name": "Neha Gupta", "title": "QA Engineer", "company": "QualityFirst", "location": "Delhi", "skills": ["Selenium", "JIRA", "Python", "Postman", "Test Automation"], "experience": 4},
    {"name": "Arjun Menon", "title": "Product Manager", "company": "ProductHub", "location": "Bengaluru", "skills": ["JIRA", "Agile", "SQL", "Analytics", "Roadmapping"], "experience": 6},
    {"name": "Ishita Bose", "title": "UX Designer", "company": "DesignCraft", "location": "Kolkata", "skills": ["Figma", "Sketch", "User Research", "Prototyping", "Design Systems"], "experience": 4},
    {"name": "Manish Kumar", "title": "Cloud Engineer", "company": "CloudBridge", "location": "Pune", "skills": ["AWS", "Azure", "Kubernetes", "Docker", "Networking"], "experience": 7},
    {"name": "Pooja Shah", "title": "HR Manager", "company": "PeopleFirst HR", "location": "Ahmedabad", "skills": ["Recruitment", "HRMS", "Payroll", "Employee Relations", "Talent Acquisition"], "experience": 8},
    {"name": "Suresh Pillai", "title": "Sales Manager", "company": "GrowthWorks", "location": "Mumbai", "skills": ["CRM", "Salesforce", "Negotiation", "Account Management", "B2B Sales"], "experience": 6},
    {"name": "Kavita Joshi", "title": "Digital Marketing Specialist", "company": "MediaNest", "location": "Jaipur", "skills": ["SEO", "Google Ads", "Content Marketing", "Analytics", "Social Media"], "experience": 5},
    {"name": "Amit Desai", "title": "System Administrator", "company": "NetServe", "location": "Surat", "skills": ["Linux", "Windows Server", "Networking", "Active Directory", "VMware"], "experience": 6},
    {"name": "Rekha Nambiar", "title": "Finance Analyst", "company": "FinEdge Consulting", "location": "Chennai", "skills": ["Excel", "Financial Modeling", "SAP", "Budgeting", "Forecasting"], "experience": 5},
    {"name": "Nikhil Chawla", "title": "Business Analyst", "company": "BizInsights", "location": "Gurugram", "skills": ["SQL", "Excel", "Power BI", "JIRA", "Requirements Analysis"], "experience": 4},
    {"name": "Deepak Rao", "title": "Data Engineer", "company": "DataStream", "location": "Bengaluru", "skills": ["Python", "Spark", "Airflow", "Snowflake", "ETL", "AWS"], "experience": 6},
    {"name": "Swati Kulkarni", "title": "Node.js Backend Engineer", "company": "APIWorks", "location": "Pune", "skills": ["Node.js", "Express", "MongoDB", "GraphQL", "Docker"], "experience": 4},
    {"name": "Farhan Ali", "title": "Full Stack Engineer", "company": "WebForge", "location": "Lucknow", "skills": ["JavaScript", "React", "Express", "PostgreSQL", "Node.js"], "experience": 5},
    {"name": "Lakshmi Venkatesan", "title": "Project Coordinator", "company": "BuildRight", "location": "Coimbatore", "skills": ["MS Project", "JIRA", "Agile", "Communication", "Risk Management"], "experience": 4},
    {"name": "Gaurav Bhatia", "title": "Cybersecurity Analyst", "company": "SecureShield", "location": "Bengaluru", "skills": ["Penetration Testing", "Firewalls", "SIEM", "Network Security", "Compliance"], "experience": 5},
]


def search_demo(search_name, jd_name, keywords):
    """Return realistic sample candidates matched to the JD (zero-key mode).

    Demo Data mode lets users experience the full search → review → import →
    rank pipeline without any API keys. Candidates are matched against the JD
    title + skills so results look like a real search.
    """
    config = frappe.get_single("Job Portal Config")
    if not getattr(config, "demo_enabled", 0):
        return []

    limit = getattr(config, "demo_search_limit", 0) or 15

    try:
        jd = frappe.get_doc("Job Description", jd_name)
        jd_skills = list(jd.get_all_skills_with_importance().keys()) if jd else []
    except Exception:
        jd = None
        jd_skills = []

    haystack_keywords = (keywords or "").lower().replace(",", " ").split()

    scored = []
    for cand in DEMO_CANDIDATES:
        score = 0
        haystack = " ".join([cand["title"], " ".join(cand["skills"])]).lower()
        for kw in haystack_keywords:
            kw = kw.strip()
            if kw and len(kw) > 2 and kw in haystack:
                score += 1
        for skill in jd_skills:
            if skill and skill.lower() in haystack:
                score += 2
        scored.append((score, cand))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for index, (score, cand) in enumerate(scored[:limit]):
        results.append({
            "name": cand["name"],
            "url": "https://demo.hrmaster.local/candidates/{0}".format(index + 1),
            "title": cand["title"],
            "company": cand["company"],
            "location": cand["location"],
            "skills": ", ".join(cand["skills"]),
            "experience": cand["experience"],
            "source_url": "https://demo.hrmaster.local/candidates/{0}".format(index + 1),
        })

    return results


def score_result_against_jd(jd, result):
    """Compute a smart match % for a raw portal result against a JD.

    Uses weighted skill overlap (Required/Preferred/Good to Have) plus an
    experience-range match, mirroring the main ranking formula so HR sees a
    meaningful percentage before importing.
    """
    jd_skills = jd.get_all_skills_with_importance() if jd else {}
    weights = {"Required": 3, "Preferred": 2, "Good to Have": 1}

    result_text = " ".join(filter(None, [
        result.get("skills_summary") or result.get("skills") or "",
        result.get("current_title") or result.get("title") or "",
        result.get("current_company") or result.get("company") or "",
    ])).lower()

    matched = []
    missing = []
    weighted_sum = 0
    total_weight = 0

    for skill_name, info in (jd_skills or {}).items():
        weight = weights.get(info.get("importance", "Required"), 1)
        total_weight += weight * 100
        if skill_name and skill_name.lower() in result_text:
            matched.append(skill_name)
            weighted_sum += 100 * weight
        else:
            missing.append(skill_name)
            if info.get("importance") == "Required":
                weighted_sum -= 10 * weight

    skill_score = (weighted_sum / total_weight * 100) if total_weight else 50

    # Experience match (mirrors ranking_api.calculate_experience_match)
    jd_min = (jd.min_experience_years or 0) if jd else 0
    jd_max = (jd.max_experience_years or 20) if jd else 20
    cand_exp = result.get("experience_years") or 0

    if cand_exp == 0:
        exp_score = 40  # unknown experience → neutral
    elif jd_min <= cand_exp <= jd_max:
        exp_score = 100
    elif cand_exp < jd_min:
        gap = jd_min - cand_exp
        exp_score = max(0, 100 - (gap / max(jd_min, 1) * 100))
    else:
        exp_score = 90  # over-qualified

    # Education can't be inferred from a raw result → neutral 50 (15% weight)
    total = skill_score * 0.60 + exp_score * 0.25 + 50 * 0.15
    total = round(min(total, 100), 1)

    return {
        "match_score": total,
        "skill_score": round(skill_score, 1),
        "experience_score": round(exp_score, 1),
        "matched_skills": matched,
        "missing_skills": missing,
    }
