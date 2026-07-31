"""HR Master Recruiting Portal - Data Protection & Consent page."""

from __future__ import unicode_literals

import frappe

from hr_master.api.portal_actions import set_portal_context


def get_context(context):
    """Render the data protection policy (public page, no login required)."""
    set_portal_context(context)
    context.no_cache = 1
    context.active = "legal"
    context.page_title = "Data Protection Policy"
    context.page_description = "Data protection, retention and candidate rights under the HR Master data policy."

    context.company_name = (
        frappe.db.get_single_value("Global Defaults", "default_company")
        or "our organisation"
    )
    return context
