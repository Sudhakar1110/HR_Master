"""HR Master Recruiting Portal - Job Description detail & portal search page."""

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
from hr_master.api.search_api import search_candidates_for_jd, import_search_results
from hr_master.api.ranking_api import rank_all_candidates_for_jd


def get_context(context):
    """Render JD details, trigger portal search/import/rank via POST."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "jds"
    context.can_write = can_write()

    jd_name = frappe.form_dict.get("name")
    if not jd_name or not frappe.db.exists("Job Description", jd_name):
        frappe.local.flags.redirect_location = "/hr_portal/jds"
        raise frappe.Redirect

    # Handle POST actions (search / import / rank) - PRG pattern
    if frappe.request.method == "POST":
        action = frappe.form_dict.get("action")
        try:
            require_write_access()

            if action == "search":
                result = search_candidates_for_jd(jd_name)
                message = result.get("message") or "Search queued"
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash("/hr_portal/jd?name={0}".format(jd_name), message, flash_type)
            elif action == "import":
                search_name = frappe.form_dict.get("search_name")
                result = import_search_results(search_name) if search_name else {"status": "error", "message": "No search selected"}
                message = result.get("message") or str(result)
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash("/hr_portal/jd?name={0}".format(jd_name), message, flash_type)
            elif action == "rank":
                result = rank_all_candidates_for_jd(jd_name)
                message = result.get("message") or str(result)
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash("/hr_portal/jd?name={0}".format(jd_name), message, flash_type)
            else:
                frappe.throw(_("Unknown action"))
        except frappe.Redirect:
            raise
        except Exception as e:
            context.flash = {"type": "error", "message": str(e)}

    if frappe.form_dict.get("msg") == "created":
        context.flash = {"type": "success", "message": "Job Description created successfully."}
    else:
        render_flash(context)

    jd = frappe.get_doc("Job Description", jd_name)
    context.jd = jd
    context.page_title = jd.job_title
    context.page_description = "{0} — search candidate portals, import results and rank applicants by match percentage.".format(jd.job_title)

    context.searches = frappe.get_all(
        "Job Portal Search",
        fields=[
            "name",
            "status",
            "search_date",
            "total_candidates_found",
            "linkedin_results",
            "naukri_results",
            "indeed_results",
            "monster_results",
            "serpapi_results",
        ],
        filters={"job_description": jd_name},
        order_by="search_date desc",
        limit_page_length=20,
    )

    context.ranking_count = frappe.db.count(
        "Candidate Ranking", filters={"job_description": jd_name}
    )

    # Whether a background portal search is still running (drives auto-refresh polling)
    context.search_in_progress = (
        jd.portal_search_status == "Searching"
        or any(s.status in ("Queued", "In Progress") for s in context.searches)
    )

    return context
