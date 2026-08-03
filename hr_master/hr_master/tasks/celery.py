"""Background job tasks for HR Master using Frappe's queue system"""

from __future__ import unicode_literals

import frappe
from frappe import _


def process_candidate_search(search_name, job_description_name):
    """Background job: Process candidate search across all enabled portals.

    This runs as a long queue job and handles the actual API calls
    to job portals.
    """
    if not search_name:
        # Defensive guard: this function must be enqueued with a Job Portal
        # Search record name (created by search_candidates_for_jd). Without
        # one there is nothing to persist results against, so log clearly
        # instead of crashing confusingly.
        frappe.log_error(
            message=(
                "process_candidate_search called without a search_name "
                f"(job_description={job_description_name}). Use "
                "search_candidates_for_jd() to create a Job Portal Search "
                "record first."
            ),
            title="Process Search Error",
        )
        return

    try:
        search = frappe.get_doc("Job Portal Search", search_name)
        search.status = "In Progress"
        search.save(ignore_permissions=True)

        jd = frappe.get_doc("Job Description", job_description_name)
        keywords = search.search_keywords or jd.job_title

        from hr_master.api.search_api import (
            search_linkedin,
            search_naukri,
            search_indeed,
            search_monster,
            search_serpapi,
            search_adzuna,
            search_remotive,
            search_arbeitnow,
            search_demo,
        )

        total_results = 0
        errors = []

        # Search each enabled portal
        portal_searches = []

        if search.search_linkedin:
            portal_searches.append(("LinkedIn", search_linkedin))

        if search.search_naukri:
            portal_searches.append(("Naukri", search_naukri))

        if search.search_indeed:
            portal_searches.append(("Indeed", search_indeed))

        if search.search_monster:
            portal_searches.append(("Monster", search_monster))

        if search.search_serpapi:
            portal_searches.append(("SerpAPI", search_serpapi))

        if search.search_adzuna:
            portal_searches.append(("Adzuna", search_adzuna))

        if search.search_remotive:
            portal_searches.append(("Remotive", search_remotive))

        if search.search_arbeitnow:
            portal_searches.append(("Arbeitnow", search_arbeitnow))

        if search.search_demo:
            portal_searches.append(("Demo", search_demo))

        for portal_name, search_func in portal_searches:
            try:
                results = search_func(
                    search_name, job_description_name, keywords
                )

                if results:
                    _append_search_results(search, portal_name, results)
                    total_results += len(results)

            except Exception as e:
                error_msg = f"{portal_name}: {str(e)}"
                errors.append(error_msg)
                frappe.log_error(
                    message=error_msg,
                    title=f"{portal_name} Search Error",
                )

        # Last-resort fallback: if every enabled portal errored and returned
        # nothing, fall back to Demo data (zero-key, local) so the search never
        # dead-ends as "Failed" — the original errors stay visible in error_log.
        if total_results == 0 and errors:
            try:
                if not frappe.db.get_single_value("Job Portal Config", "demo_enabled"):
                    # Use set_value (not doc.save) so validate_api_configs()
                    # can't throw for a placeholder portal missing its key.
                    frappe.db.set_value(
                        "Job Portal Config", "Job Portal Config", "demo_enabled", 1
                    )
                    frappe.db.commit()
                if not search.search_demo:
                    demo_results = search_demo(
                        search_name, job_description_name, keywords
                    )
                    _append_search_results(search, "Demo", demo_results)
                    total_results += len(demo_results or [])
                    errors.append("Demo: fallback used after all portals failed")
            except Exception:
                pass

        # Update search record
        search.total_candidates_found = total_results
        if errors:
            search.error_log = "\n".join(errors)
            search.status = "Partial" if total_results > 0 else "Failed"
        else:
            search.status = "Completed"

        search.save(ignore_permissions=True)

        # Update JD status
        jd.db_set("portal_search_status", "Searched")
        jd.db_set("status", "In Progress")

        # Trigger ranking for imported candidates
        if total_results > 0:
            import_results_and_rank(search, jd)

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(
            message=f"Process search error: {str(e)}",
            title="Process Search Error",
        )

        # Update status to failed — persist the real error message on the
        # search record too, so the portal can show it instead of generic
        # boilerplate.
        try:
            frappe.db.set_value(
                "Job Portal Search",
                search_name,
                {"status": "Failed", "error_log": f"Process search error: {str(e)}"},
            )
            frappe.db.set_value(
                "Job Description", job_description_name,
                "portal_search_status", "Error"
            )
            frappe.db.commit()
        except Exception:
            pass


def _append_search_results(search, portal_name, results):
    """Append raw portal results as child rows on a Job Portal Search."""
    for result in results or []:
        search.append("search_results", {
            "candidate_name": result.get("name", ""),
            "source": portal_name,
            "profile_url": result.get("url", ""),
            "current_title": result.get("title", ""),
            "current_company": result.get("company", ""),
            "location": result.get("location", ""),
            "skills_summary": result.get("skills", ""),
            "experience_years": result.get("experience", 0),
        })


def import_results_and_rank(search, jd):
    """Import search results and trigger ranking."""
    try:
        imported = search.import_results_to_candidates()

        if imported > 0:
            from hr_master.api.ranking_api import rank_candidates

            rank_candidates(jd)
    except Exception as e:
        frappe.log_error(
            message=f"Import and rank error: {str(e)}",
            title="Import & Rank Error",
        )


def rank_candidates_batch(search_name):
    """Background job: Rank a batch of candidates."""
    try:
        search = frappe.get_doc("Job Portal Search", search_name)
        jd = frappe.get_doc("Job Description", search.job_description)

        from hr_master.api.ranking_api import rank_candidates

        rank_candidates(jd)

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(
            message=f"Batch ranking error: {str(e)}",
            title="Batch Ranking Error",
        )
