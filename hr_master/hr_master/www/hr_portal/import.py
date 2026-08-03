"""HR Master Recruiting Portal - Bulk candidate CSV import page."""

from __future__ import unicode_literals

import frappe

from hr_master.api.portal_actions import (
    require_hr_access,
    set_portal_context,
    can_write,
    jd_visibility,
)


def get_context(context):
    """Render the CSV import page (upload -> import_candidates_from_csv)."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "import"
    context.can_write = can_write()
    context.page_title = "Import Candidates"
    context.page_description = "Bulk-import candidates from a CSV file — optionally linked to a Job Description so they appear in its ranking list."

    jd_filters, jd_or_filters = jd_visibility()
    context.jds = frappe.get_all(
        "Job Description",
        fields=["name", "job_title"],
        filters=jd_filters,
        or_filters=jd_or_filters,
        order_by="modified desc",
        limit_page_length=100,
    ) or []

    return context
