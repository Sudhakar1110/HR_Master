"""Daily scheduled tasks for HR Master"""

from __future__ import unicode_literals

import frappe


def auto_search_portals():
    """Daily task: Automatically search portals for all open JDs."""
    if not frappe.db.get_single_value("Job Portal Config", "auto_search_enabled"):
        return

    open_jds = frappe.get_all(
        "Job Description",
        filters={
            "status": "Open",
            "portal_search_status": ["!=", "Searching"],
        },
        fields=["name", "job_title"],
    )

    for jd in open_jds:
        try:
            from hr_master.api.search_api import search_candidates_for_jd

            search_candidates_for_jd(jd.name)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                message=f"Auto search error for {jd.name}: {str(e)}",
                title="Daily Auto Search Error",
            )

    frappe.logger().info(
        f"HR Master: Auto portal search completed for {len(open_jds)} JDs"
    )


def update_jd_statuses():
    """Daily task: Update JD statuses based on closing dates."""
    from frappe.utils import today

    expired_jds = frappe.get_all(
        "Job Description",
        filters={
            "status": "Open",
            "target_close_date": ["<", today()],
        },
        pluck="name",
    )

    for jd_name in expired_jds:
        frappe.db.set_value("Job Description", jd_name, "status", "Closed")

    if expired_jds:
        frappe.db.commit()
        frappe.logger().info(
            f"HR Master: Closed {len(expired_jds)} expired JDs"
        )
