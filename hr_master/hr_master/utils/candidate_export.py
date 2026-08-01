"""Candidate Export Utility for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _
import csv
import io


@frappe.whitelist()
def export_candidates(filters=None, fields=None, file_format="CSV"):
    """Export candidate data to CSV or Excel format.

    Args:
        filters: Optional dict of filters to apply
        fields: Optional list of fields to export. Defaults to common fields.
        file_format: "CSV" or "Excel"
    """
    try:
        if isinstance(filters, str):
            filters = frappe.parse_json(filters) if filters else {}
        if isinstance(fields, str):
            fields = frappe.parse_json(fields) if fields else []

        if not fields:
            fields = [
                "name", "candidate_name", "email", "phone", "status",
                "current_title", "current_company", "source", "source_url",
                "total_experience_years", "highest_education",
                "total_match_score", "location", "current_salary",
                "expected_salary", "notice_period_days", "creation"
            ]

        candidates = frappe.get_all(
            "Candidate",
            filters=filters or {},
            fields=fields,
            order_by="creation desc"
        )

        if not candidates:
            return {"status": "error", "message": _("No candidates found")}

        if file_format == "CSV":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            for c in candidates:
                row = {f: c.get(f, "") for f in fields}
                writer.writerow(row)

            content = output.getvalue()
            output.close()

            # Create file attachment
            from frappe.utils.file_manager import save_file
            file_name = f"candidates_export_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"
            file_doc = save_file(
                fname=file_name,
                content=content.encode("utf-8-sig"),
                dt=None,
                dn=None,
                is_private=1
            )

            return {
                "status": "success",
                "file_url": file_doc.file_url,
                "file_name": file_name,
                "count": len(candidates)
            }

        else:
            return {
                "status": "success",
                "data": candidates,
                "count": len(candidates)
            }

    except Exception as e:
        frappe.log_error(message=f"Export error: {str(e)}", title="Candidate Export Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def export_candidate_activity(candidate_name):
    """Export full activity timeline for a candidate."""
    try:
        activities = frappe.get_all(
            "Candidate Activity Log",
            filters={"candidate": candidate_name},
            fields=["activity_type", "description", "activity_date", "activity_time", "user", "reference_doctype", "reference_name"],
            order_by="activity_date desc, activity_time desc"
        )

        if not activities:
            return {"status": "error", "message": _("No activities found")}

        output = io.StringIO()
        fields = ["activity_type", "description", "activity_date", "activity_time", "user", "reference_doctype", "reference_name"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for a in activities:
            writer.writerow({f: a.get(f, "") for f in fields})

        content = output.getvalue()
        output.close()

        cand_name = frappe.db.get_value("Candidate", candidate_name, "candidate_name")
        from frappe.utils.file_manager import save_file
        file_name = f"activity_{candidate_name}_{frappe.utils.now_datetime().strftime('%Y%m%d')}.csv"
        file_doc = save_file(
            fname=file_name,
            content=content.encode("utf-8-sig"),
            dt="Candidate",
            dn=candidate_name,
            is_private=1
        )

        return {
            "status": "success",
            "file_url": file_doc.file_url,
            "file_name": file_name,
            "count": len(activities)
        }

    except Exception as e:
        frappe.log_error(message=f"Activity export error: {str(e)}", title="Export Error")
        return {"status": "error", "message": str(e)}
