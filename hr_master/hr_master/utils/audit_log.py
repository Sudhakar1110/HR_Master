"""Audit Log Module for HR Master

Provides comprehensive audit trail for all HR-related actions including
candidate updates, ranking changes, offer modifications, and system config changes.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist()
def log_audit_entry(action, resource_type, resource_id, details=None, user=None):
    """Create an audit log entry.
    
    Args:
        action: Action performed (Created, Updated, Deleted, Submitted, Cancelled, etc.)
        resource_type: DocType name
        resource_id: Document name/ID
        details: Additional details about the action
        user: User who performed the action (defaults to current user)
    """
    try:
        audit = frappe.new_doc("Candidate Activity Log")
        audit.activity_type = map_action_to_activity(action)
        audit.description = format_description(action, resource_type, resource_id, details)
        audit.activity_date = frappe.utils.today()
        audit.activity_time = frappe.utils.nowtime()
        audit.reference_doctype = resource_type
        audit.reference_name = resource_id
        audit.user = user or frappe.session.user
        audit.save(ignore_permissions=True)
        return audit.name
    except Exception as e:
        frappe.log_error(message=f"Audit log error: {str(e)}", title="Audit Log Error")
        return None


def map_action_to_activity(action):
    """Map generic actions to Candidate Activity Log types."""
    mapping = {
        "Created": "Created",
        "Updated": "Status Changed",
        "Deleted": "Other",
        "Submitted": "Status Changed",
        "Cancelled": "Other",
        "Ranked": "Rank Updated",
        "Shortlisted": "Shortlisted",
        "Hired": "Hired",
        "Rejected": "Rejected",
        "Offer Generated": "Offer Made",
        "Offer Accepted": "Offer Accepted",
        "Offer Declined": "Other",
        "Interview Scheduled": "Interview Scheduled",
        "Feedback Submitted": "Feedback Submitted",
        "Email Sent": "Email Sent",
        "Note Added": "Note Added",
        "Resume Uploaded": "Resume Uploaded",
        "Bulk Update": "Status Changed",
        "Imported": "Created",
        "Merged": "Other"
    }
    return mapping.get(action, "Other")


def format_description(action, resource_type, resource_id, details=None):
    """Format a human-readable description for the audit entry."""
    parts = [f"{action} - {resource_type}: {resource_id}"]
    if details:
        if isinstance(details, dict):
            changed = []
            for key, value in details.items():
                changed.append(f"{key}: {value}")
            if changed:
                parts.append(" | ".join(changed))
        else:
            parts.append(str(details))
    return " | ".join(parts)


def get_audit_trail(candidate_name=None, resource_type=None, resource_id=None, 
                    start_date=None, end_date=None, limit=100):
    """Retrieve audit trail entries with optional filters."""
    filters = {}

    if candidate_name:
        filters["candidate"] = candidate_name
    if resource_type:
        filters["reference_doctype"] = resource_type
    if resource_id:
        filters["reference_name"] = resource_id
    if start_date:
        filters["activity_date"] = [">=", start_date]
    if end_date:
        if "activity_date" in filters:
            filters["activity_date"] = [filters["activity_date"], ["<=", end_date]]
        else:
            filters["activity_date"] = ["<=", end_date]

    return frappe.get_all(
        "Candidate Activity Log",
        filters=filters or None,
        fields=["name", "activity_type", "description", "activity_date", 
                "activity_time", "user", "reference_doctype", "reference_name",
                "candidate", "candidate_name"],
        order_by="activity_date desc, activity_time desc",
        limit=limit
    )


@frappe.whitelist()
def get_audit_stats():
    """Get audit log statistics."""
    today = frappe.utils.today()

    return {
        "total_entries": frappe.db.count("Candidate Activity Log"),
        "today_entries": frappe.db.count("Candidate Activity Log", 
            filters={"activity_date": today}),
        "by_type": frappe.db.sql("""
            SELECT activity_type, COUNT(*) as count
            FROM `tabCandidate Activity Log`
            GROUP BY activity_type
            ORDER BY count DESC
        """, as_dict=True),
        "recent_users": frappe.db.sql("""
            SELECT user, COUNT(*) as count
            FROM `tabCandidate Activity Log`
            WHERE activity_date >= %s
            GROUP BY user
            ORDER BY count DESC
            LIMIT 10
        """, frappe.utils.add_days(today, -7), as_dict=True)
    }
