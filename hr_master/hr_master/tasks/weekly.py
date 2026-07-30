"""Weekly scheduled tasks for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.utils import now_datetime, add_days


def generate_weekly_report():
    """Weekly task: Generate and send weekly HR report."""
    from frappe.utils import today, getdate

    week_start = getdate(add_days(today(), -7))
    week_end = getdate(today())

    # Gather statistics
    new_jds = frappe.db.count(
        "Job Description",
        filters={"creation": [">=", week_start]},
    )

    new_candidates = frappe.db.count(
        "Candidate",
        filters={"creation": [">=", week_start]},
    )

    new_rankings = frappe.db.count(
        "Candidate Ranking",
        filters={"creation": [">=", week_start]},
    )

    interviews_conducted = frappe.db.count(
        "Interview Schedule",
        filters={
            "status": "Completed",
            "modified": [">=", week_start],
        },
    )

    selections = frappe.db.count(
        "Candidate",
        filters={
            "status": "Selected",
            "modified": [">=", week_start],
        },
    )

    report_data = {
        "week_start": week_start,
        "week_end": week_end,
        "new_jds": new_jds,
        "new_candidates": new_candidates,
        "new_rankings": new_rankings,
        "interviews_conducted": interviews_conducted,
        "selections": selections,
        "generated_on": now_datetime(),
    }

    # Log the report
    frappe.logger().info(f"Weekly HR Report: {report_data}")

    # Notify admin users
    admin_users = frappe.get_all(
        "User",
        filters={"role": "HR Master Admin"},
        pluck="email",
    )

    if admin_users:
        subject = f"Weekly HR Report ({week_start} - {week_end})"
        message = f"""
        <h3>Weekly HR Summary</h3>
        <table style="border-collapse: collapse; width: 100%;">
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>New JDs Posted</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{new_jds}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>New Candidates Sourced</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{new_candidates}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Candidates Ranked</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{new_rankings}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Interviews Conducted</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{interviews_conducted}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Selections Made</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{selections}</td>
            </tr>
        </table>
        """

        frappe.sendmail(
            recipients=admin_users,
            subject=subject,
            message=message,
        )

    return report_data


def archive_old_searches():
    """Weekly task: Archive old portal searches."""
    from frappe.utils import add_months

    cutoff_date = add_months(now_datetime(), -3)

    old_searches = frappe.get_all(
        "Job Portal Search",
        filters={"creation": ["<", cutoff_date]},
        pluck="name",
    )

    archived = 0
    for search_name in old_searches:
        try:
            search = frappe.get_doc("Job Portal Search", search_name)
            search.status = "Archived"  # Add archived status
            search.save(ignore_permissions=True)
            archived += 1
        except Exception:
            continue

    if archived > 0:
        frappe.db.commit()
        frappe.logger().info(
            f"HR Master: Archived {archived} old portal searches"
        )
