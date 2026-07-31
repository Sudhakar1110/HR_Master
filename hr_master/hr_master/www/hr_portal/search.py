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
from hr_master.api.search_api import import_search_results, import_single_search_result


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
    context.pending_count = len(
        [r for r in context.results if not r.is_imported and r.import_status == "Pending"]
    )
    context.imported_count = len([r for r in context.results if r.is_imported])
    context.page_title = "Search Results — {0}".format(search.job_title)
    context.page_description = "Raw portal search results for {0} — review before importing as candidates.".format(search.job_title)

    return context
