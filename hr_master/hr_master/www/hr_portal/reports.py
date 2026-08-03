"""HR Master Recruiting Portal - Reports page (charts + tables + export)."""

from __future__ import unicode_literals

import frappe

from hr_master.api.portal_actions import (
    require_hr_access,
    set_portal_context,
)
from hr_master.api.portal_reports import REPORTS, get_report_data


def get_context(context):
    """Render the selected portal report with chart, table and export buttons."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "reports"
    context.page_title = "Reports"
    context.page_description = "Recruitment analytics — funnel, sources, offers, time-to-hire and more, with CSV / PDF export."

    report_key = frappe.form_dict.get("r") or "source_performance"
    context.reports_list = REPORTS
    context.report = get_report_data(report_key)

    return context
