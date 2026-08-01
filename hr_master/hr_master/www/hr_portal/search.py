"""HR Master Recruiting Portal - Raw portal search results review page."""

from __future__ import unicode_literals

import frappe
from frappe import _

from hr_master.api.portal_actions import (
    require_hr_access,
    can_write,
    require_write_access,
    redirect_with_flash,
    render_flash,
    set_portal_context,
)
from hr_master.api.search_api import (
    import_search_results,
    import_single_search_result,
    score_result_against_jd,
)


def get_context(context):
    """Render raw portal results for a search; import all or a single row via POST."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "jds"
    context.can_write = can_write()

    search_name = frappe.form_dict.get("name")
    if not search_name or not frappe.db.exists("Job Portal Search", search_name):
        frappe.local.flags.redirect_location = "/hr_portal/jds"
        raise frappe.Redirect

    # Handle POST (import all / import single) - PRG pattern
    if frappe.request.method == "POST":
        action = frappe.form_dict.get("action")
        base_path = "/hr_portal/search?name={0}".format(search_name)
        try:
            require_write_access()

            if action == "import_all":
                result = import_search_results(search_name)
                message = result.get("message") or str(result)
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash(base_path, message, flash_type)
            elif action == "import_one":
                result_name = frappe.form_dict.get("result_name")
                if not result_name:
                    frappe.throw(_("No result selected"))
                result = import_single_search_result(search_name, result_name)
                message = result.get("message") or str(result)
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash(base_path, message, flash_type)
            else:
                frappe.throw(_("Unknown action"))
        except frappe.Redirect:
            raise
        except Exception as e:
            context.flash = {"type": "error", "message": str(e)}

    render_flash(context)

    search = frappe.get_doc("Job Portal Search", search_name)
    context.search = search

    if not search.job_description or not frappe.db.exists("Job Description", search.job_description):
        frappe.local.flags.redirect_location = "/hr_portal/jds"
        raise frappe.Redirect

    context.jd = frappe.get_doc("Job Description", search.job_description)
    context.results = search.search_results or []

    # Smart match % per result (skills + experience vs the JD), best matches first
    scored = []
    for r in context.results:
        score_info = score_result_against_jd(context.jd, r)
        scored.append({
            "name": r.name,
            "candidate_name": r.candidate_name,
            "source": r.source,
            "profile_url": r.profile_url,
            "current_title": r.current_title,
            "current_company": r.current_company,
            "location": r.location,
            "skills_summary": r.skills_summary,
            "experience_years": r.experience_years,
            "is_imported": r.is_imported,
            "import_status": r.import_status,
            "match_score": score_info["match_score"],
            "skill_score": score_info["skill_score"],
            "experience_score": score_info["experience_score"],
            "matched_skills": score_info["matched_skills"],
            "missing_skills": score_info["missing_skills"],
        })
    scored.sort(key=lambda x: x["match_score"], reverse=True)
    context.results = scored

    # context.results is a list of dicts (the scored list above), so use
    # dict access, not attribute access.
    context.pending_count = len(
        [r for r in context.results if not r["is_imported"] and r["import_status"] == "Pending"]
    )
    context.imported_count = len([r for r in context.results if r["is_imported"]])
    context.avg_match = round(
        sum(r["match_score"] for r in context.results) / len(context.results), 1
    ) if context.results else 0
    context.page_title = "Search Results — {0}".format(search.job_title)
    context.page_description = "Raw portal search results for {0} — review before importing as candidates.".format(search.job_title)

    return context
