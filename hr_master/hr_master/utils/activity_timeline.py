"""Activity Timeline UI Utility for HR Master

Provides timeline-structured data for rendering candidate activity history
in the Frappe UI using Timeline components.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import date_diff, today, format_date, format_time


@frappe.whitelist()
def get_candidate_timeline(candidate_name, limit=50):
    """Get structured timeline data for a candidate.

    Returns timeline entries grouped by date for UI rendering.
    """
    try:
        activities = frappe.get_all(
            "Candidate Activity Log",
            filters={"candidate": candidate_name},
            fields=[
                "name", "activity_type", "description", "activity_date",
                "activity_time", "user", "creation",
                "reference_doctype", "reference_name"
            ],
            order_by="activity_date desc, activity_time desc",
            limit=limit
        )

        if not activities:
            return {"status": "success", "timeline": [], "message": _("No activities recorded")}

        # Group by date
        grouped = {}
        for act in activities:
            date_key = str(act.activity_date) if act.activity_date else str(act.creation.date())

            if date_key not in grouped:
                date_label = get_date_label(date_key)
                grouped[date_key] = {
                    "date": date_key,
                    "label": date_label,
                    "activities": []
                }

            grouped[date_key]["activities"].append({
                "name": act.name,
                "type": act.activity_type,
                "icon": get_activity_icon(act.activity_type),
                "color": get_activity_color(act.activity_type),
                "description": act.description,
                "time": format_time(act.activity_time) if act.activity_time else "",
                "user": act.user,
                "reference_doctype": act.reference_doctype,
                "reference_name": act.reference_name
            })

        timeline = list(grouped.values())

        # Add resume info
        candidate = frappe.get_doc("Candidate", candidate_name)

        return {
            "status": "success",
            "timeline": timeline,
            "candidate": {
                "name": candidate.name,
                "candidate_name": candidate.candidate_name,
                "status": candidate.status,
                "total_match_score": candidate.total_match_score,
                "creation": str(candidate.creation)
            }
        }

    except Exception as e:
        frappe.log_error(message=f"Timeline error: {str(e)}", title="Timeline Error")
        return {"status": "error", "message": str(e)}


def get_date_label(date_str):
    """Get a human-readable label for a date."""
    days_ago = date_diff(today(), date_str)

    if days_ago == 0:
        return _("Today")
    elif days_ago == 1:
        return _("Yesterday")
    elif days_ago < 7:
        return _("{0} days ago").format(days_ago)
    elif days_ago < 30:
        weeks = days_ago // 7
        return _("{0} week(s) ago").format(weeks)
    else:
        return format_date(date_str)


def get_activity_icon(activity_type):
    """Get Font Awesome icon class for activity type."""
    icons = {
        "Created": "user-plus",
        "Contacted": "phone",
        "Screened": "search",
        "Shortlisted": "check-circle",
        "Interview Scheduled": "calendar",
        "Interview Completed": "calendar-check",
        "Feedback Submitted": "comment",
        "Offer Made": "gift",
        "Offer Accepted": "thumbs-up",
        "Offer Rejected": "thumbs-down",
        "Hired": "user-check",
        "Rejected": "user-times",
        "Rank Updated": "chart-line",
        "Resume Uploaded": "file-upload",
        "Status Changed": "exchange-alt",
        "Note Added": "sticky-note",
        "Email Sent": "envelope",
        "System Action": "cog",
        "Other": "circle"
    }
    return icons.get(activity_type, "circle")


def get_activity_color(activity_type):
    """Get color for activity type."""
    colors = {
        "Created": "blue",
        "Contacted": "orange",
        "Screened": "purple",
        "Shortlisted": "green",
        "Interview Scheduled": "cyan",
        "Interview Completed": "green",
        "Feedback Submitted": "blue",
        "Offer Made": "yellow",
        "Offer Accepted": "green",
        "Offer Rejected": "red",
        "Hired": "green",
        "Rejected": "red",
        "Rank Updated": "blue",
        "Resume Uploaded": "purple",
        "Status Changed": "orange",
        "Note Added": "gray",
        "Email Sent": "blue",
        "System Action": "darkgrey",
        "Other": "gray"
    }
    return colors.get(activity_type, "gray")


@frappe.whitelist()
def add_timeline_note(candidate_name, note):
    """Add a manual note to candidate timeline."""
    try:
        from hr_master.hr_master.doctype.candidate_activity_log.candidate_activity_log import log_activity
        log_name = log_activity(
            candidate=candidate_name,
            activity_type="Note Added",
            description=note,
        )
        return {"status": "success", "name": log_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_timeline_stats(candidate_name):
    """Get timeline statistics for a candidate."""
    try:
        total = frappe.db.count("Candidate Activity Log", filters={"candidate": candidate_name})

        by_type = frappe.db.sql("""
            SELECT activity_type, COUNT(*) as count
            FROM `tabCandidate Activity Log`
            WHERE candidate = %s
            GROUP BY activity_type
            ORDER BY count DESC
        """, candidate_name, as_dict=True)

        today_count = frappe.db.count("Candidate Activity Log", filters={
            "candidate": candidate_name,
            "activity_date": today()
        })

        return {
            "status": "success",
            "total_activities": total,
            "today": today_count,
            "breakdown": by_type
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
