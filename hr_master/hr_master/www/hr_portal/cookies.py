"""HR Master Recruiting Portal - Cookie Policy page."""

from __future__ import unicode_literals

import frappe


def get_context(context):
    """Render the cookie policy (public page, no login required)."""
    context.no_cache = 1
    context.active = "legal"
    context.page_title = "Cookie Policy"

    context.company_name = (
        frappe.db.get_single_value("Global Defaults", "default_company")
        or "our organisation"
    )
    return context
