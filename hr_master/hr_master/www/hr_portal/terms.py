"""HR Master Recruiting Portal - Terms of Use page."""

from __future__ import unicode_literals

import frappe

from hr_master.api.portal_actions import set_portal_context


def get_context(context):
    """Render the terms of use (public page, no login required)."""
    set_portal_context(context)
    context.no_cache = 1
    context.active = "legal"
    context.page_title = "Terms of Use"
    context.page_description = "Terms of use for the HR Master recruiting portal."

    context.company_name = (
        frappe.db.get_single_value("Global Defaults", "default_company")
        or "our organisation"
    )
    return context
