"""Boot configuration for HR Master - sets boot context for frontend"""

from __future__ import unicode_literals

import frappe


def set_boot_config(bootinfo):
    """Set boot session configuration for HR Master."""
    if not frappe.session.user or frappe.session.user == "Guest":
        return

    user_roles = frappe.get_roles(frappe.session.user)

    # Check if user has HR Master roles
    hr_roles = [
        "HR Master Admin",
        "HR Master Recruiter",
        "HR Master Hiring Manager",
        "HR Master Viewer",
    ]

    has_hr_role = any(role in user_roles for role in hr_roles)

    if has_hr_role:
        bootinfo["hr_master"] = {
            "has_access": True,
            "user_roles": [r for r in user_roles if r in hr_roles],
            "config_available": frappe.db.exists("DocType", "Job Portal Config"),
            "app_version": frappe.get_module("hr_master").__version__,
        }
    else:
        bootinfo["hr_master"] = {"has_access": False}
