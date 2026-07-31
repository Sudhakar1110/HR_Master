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
