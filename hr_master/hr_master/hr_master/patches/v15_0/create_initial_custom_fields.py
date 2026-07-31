"""Patch: Create initial custom fields for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Execute the patch to create custom fields."""
    custom_fields = {
        "User": [
            {
                "fieldname": "hr_master_section",
                "label": "HR Master Settings",
                "fieldtype": "Section Break",
                "insert_after": "bio",
                "collapsible": 1,
            },
            {
                "fieldname": "hr_master_role",
                "label": "HR Master Role",
                "fieldtype": "Select",
                "options": "\nHR Master Admin\nHR Master Recruiter\nHR Master Hiring Manager\nHR Master Viewer",
                "insert_after": "hr_master_section",
                "allow_on_submit": 0,
                "in_standard_filter": 1,
            },
            {
                "fieldname": "linkedin_profile_url",
                "label": "LinkedIn Profile URL",
                "fieldtype": "Data",
                "insert_after": "hr_master_role",
            },
        ],
        "Job Description": [
            {
                "fieldname": "hr_master_section_cb",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after": "amended_from",
            },
        ],
    }

    try:
        create_custom_fields(custom_fields, ignore_validate=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            message=f"HR Master patch error: {str(e)}",
            title="HR Master Custom Fields Patch",
        )
