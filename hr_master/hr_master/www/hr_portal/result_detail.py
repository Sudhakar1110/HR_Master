"""HR Master Recruiting Portal - Candidate search result detail page.

Shows the full profile captured for a single portal search result (opened in
a new window from the search results table) with its smart match score and an
Import button, so recruiters can review a candidate before importing.
"""

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
from hr_master.api.search_api import import_single_search_result, score_result_against_jd


def get_context(context):
    """Render a single portal search result's details; allow importing it."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "jds"
    context.can_write = can_write()

    search_name = frappe.form_dict.get("search")
    result_name = frappe.form_dict.get("result")

    if not search_name or not result_name or not frappe.db.exists("Job Portal Search", search_name):
        frappe.local.flags.redirect_location = "/hr_portal/jds"
        raise frappe.Redirect

    search = frappe.get_doc("Job Portal Search", search_name)
    result = next((r for r in search.search_results if r.name == result_name), None)
    if result is None:
        frappe.local.flags.redirect_location = "/hr_portal/search?name={0}".format(search_name)
        raise frappe.Redirect

    base_path = "/hr_portal/result_detail?search={0}&result={1}".format(
        search_name, result_name
    )

    # Handle POST (import this result) - PRG pattern
    if frappe.request.method == "POST":
        try:
            require_write_access()
            action = frappe.form_dict.get("action")
            if action == "import_one":
                outcome = import_single_search_result(search_name, result_name)
                message = outcome.get("message") or str(outcome)
                flash_type = "success" if outcome.get("status") == "success" else "error"
                redirect_with_flash(base_path, message, flash_type)
            else:
                frappe.throw(_("Unknown action"))
        except frappe.Redirect:
            raise
        except Exception as e:
            context.flash = {"type": "error", "message": str(e)}

    render_flash(context)

    if not search.job_description or not frappe.db.exists("Job Description", search.job_description):
        frappe.local.flags.redirect_location = "/hr_portal/search?name={0}".format(search_name)
        raise frappe.Redirect

    context.search = search
    context.jd = frappe.get_doc("Job Description", search.job_description)
    context.result = result
    context.score_info = score_result_against_jd(context.jd, result)

    # Link to the full Candidate profile once this result has been imported.
    candidate_link = ""
    if result.is_imported or result.import_status == "Imported":
        candidate_doc = frappe.db.get_value(
            "Candidate",
            {"candidate_name": result.candidate_name, "source": result.source},
            "name",
            order_by="creation desc",
        )
        if candidate_doc:
            candidate_link = "/hr_portal/candidate?name={0}".format(candidate_doc)
    context.candidate_link = candidate_link

    context.page_title = "{0} — Search Result".format(result.candidate_name)
    context.page_description = "Candidate search result details for {0} ({1}) — review before importing.".format(
        result.candidate_name, search.job_title
    )

    return context
