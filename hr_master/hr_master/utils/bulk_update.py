"""Bulk Status Update Utility for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _
import json


@frappe.whitelist()
def bulk_update_candidates(candidate_names, new_status, send_notification=True, notes=None):
    """Bulk update candidate statuses with audit logging.

    Args:
        candidate_names: List of candidate names (JSON string or list)
        new_status: New status value
        send_notification: Whether to send notifications
        notes: Optional notes to add to activity log
    """
    try:
        if isinstance(candidate_names, str):
            candidate_names = json.loads(candidate_names)

        if not candidate_names:
            return {"status": "error", "message": _("No candidates selected")}

        valid_statuses = [
            "New", "Contacted", "Screened", "Shortlisted",
            "Interview Scheduled", "Interviewed", "Selected",
            "Rejected", "On Hold", "Blacklisted"
        ]

        if new_status not in valid_statuses:
            return {"status": "error", "message": _("Invalid status: {0}").format(new_status)}

        updated = 0
        errors = []

        for candidate_name in candidate_names:
            try:
                if not frappe.db.exists("Candidate", candidate_name):
                    errors.append(_("{0}: Candidate not found").format(candidate_name))
                    continue

                old_status = frappe.db.get_value("Candidate", candidate_name, "status")
                frappe.db.set_value("Candidate", candidate_name, "status", new_status)

                # Log activity
                description = _("Status updated from {0} to {1}").format(old_status, new_status)
                if notes:
                    description += _(" - {0}").format(notes)

                from hr_master.hr_master.doctype.candidate_activity_log.candidate_activity_log import log_activity
                log_activity(
                    candidate=candidate_name,
                    activity_type="Status Changed",
                    description=description,
                )

                updated += 1
            except Exception as e:
                errors.append(_("{0}: {1}").format(candidate_name, str(e)))

        frappe.db.commit()

        result = {
            "status": "success" if not errors else "partial",
            "updated": updated,
            "total": len(candidate_names),
            "errors": errors
        }

        return result

    except Exception as e:
        frappe.log_error(message=f"Bulk update error: {str(e)}", title="Bulk Update Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def bulk_delete_candidates(candidate_names):
    """Bulk delete candidates (Admin only)."""
    try:
        if isinstance(candidate_names, str):
            candidate_names = json.loads(candidate_names)

        if "HR Master Admin" not in frappe.get_roles():
            return {"status": "error", "message": _("Only HR Master Admin can delete candidates")}

        deleted = 0
        errors = []

        for candidate_name in candidate_names:
            try:
                frappe.delete_doc("Candidate", candidate_name, force=True)
                deleted += 1
            except Exception as e:
                errors.append(_("{0}: {1}").format(candidate_name, str(e)))

        frappe.db.commit()

        return {
            "status": "success" if not errors else "partial",
            "deleted": deleted,
            "errors": errors
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def bulk_assign_jd(candidate_names, jd_name):
    """Bulk assign candidates to a job description."""
    try:
        if isinstance(candidate_names, str):
            candidate_names = json.loads(candidate_names)

        if not frappe.db.exists("Job Description", jd_name):
            return {"status": "error", "message": _("Job Description not found")}

        jd = frappe.get_doc("Job Description", jd_name)
        assigned = 0

        for candidate_name in candidate_names:
            if not frappe.db.exists("Candidate Ranking", {
                "job_description": jd_name,
                "candidate": candidate_name
            }):
                ranking = frappe.new_doc("Candidate Ranking")
                ranking.job_description = jd_name
                ranking.job_title = jd.job_title
                ranking.candidate = candidate_name
                ranking.candidate_name = frappe.db.get_value("Candidate", candidate_name, "candidate_name")
                ranking.status = "Pending"
                ranking.save(ignore_permissions=True)
                assigned += 1

        frappe.db.commit()

        return {
            "status": "success",
            "assigned": assigned,
            "message": _("{0} candidates assigned to {1}").format(assigned, jd.job_title)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
