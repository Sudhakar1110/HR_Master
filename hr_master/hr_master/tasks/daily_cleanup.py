"""Daily cleanup tasks for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.utils import now_datetime, add_months


def archive_old_searches():
    """Daily long task: Archive and cleanup old portal searches."""
    cutoff_date = add_months(now_datetime(), -3)

    old_searches = frappe.get_all(
        "Job Portal Search",
        filters={
            "creation": ["<", cutoff_date],
            "status": ["!=", "Archived"],
        },
        pluck="name",
    )

    archived = 0
    for search_name in old_searches:
        try:
            search = frappe.get_doc("Job Portal Search", search_name)
            search.db_set("status", "Archived")
            archived += 1
        except Exception:
            continue

    if archived > 0:
        frappe.logger().info(
            f"HR Master: Archived {archived} old portal searches"
        )

    # Clean up old pending searches that are stuck
    stuck_searches = frappe.get_all(
        "Job Portal Search",
        filters={
            "status": ["in", ["Queued", "In Progress"]],
            "modified": ["<", add_months(now_datetime(), -1)],
        },
        pluck="name",
    )

    for search_name in stuck_searches:
        try:
            frappe.db.set_value("Job Portal Search", search_name, "status", "Failed")
            frappe.db.set_value(
                "Job Portal Search",
                search_name,
                "error_log",
                "Auto-failed: Search stuck in progress for over a month",
            )
        except Exception:
            continue
