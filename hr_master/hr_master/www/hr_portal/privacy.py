"""HR Master Recruiting Portal - Privacy Policy page."""

from __future__ import unicode_literals

import frappe


def get_context(context):
    """Render the privacy policy (public page, no login required)."""
    context.no_cache = 1
    context.active = "legal"
    context.page_title = "Privacy Policy"

    context.company_name = (
        frappe.db.get_single_value("Global Defaults", "default_company")
        or "our organisation"
    )
    return context
