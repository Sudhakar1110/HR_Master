"""Error Logging Dashboard for HR Master

Provides a searchable interface for viewing and analyzing application errors.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date


@frappe.whitelist()
def get_error_logs(filters=None, page=1, page_size=50):
    """Get error logs with filtering and pagination.

    Args:
        filters: Dict with optional keys: search_text, from_date, to_date, 
                 error_type, reference_doctype
        page: Page number (1-indexed)
        page_size: Results per page
    """
    try:
        if isinstance(filters, str):
            filters = frappe.parse_json(filters) if filters else {}

        conditions = []
        params = {}

        if filters:
            search = filters.get("search_text", "")
            if search:
                conditions.append("""
                    (e.title LIKE %(search)s
                    OR e.method LIKE %(search)s
                    OR e.error LIKE %(search)s
                    OR e.reference_doctype LIKE %(search)s)
                """)
                params["search"] = f"%{search}%"

            from_date = filters.get("from_date", "")
            if from_date:
                conditions.append("e.creation >= %(from_date)s")
                params["from_date"] = f"{from_date} 00:00:00"

            to_date = filters.get("to_date", "")
            if to_date:
                conditions.append("e.creation <= %(to_date)s")
                params["to_date"] = f"{to_date} 23:59:59"

            error_type = filters.get("error_type", "")
            if error_type:
                conditions.append("e.title LIKE %(error_type)s")
                params["error_type"] = f"%{error_type}%"

            doctype_filter = filters.get("reference_doctype", "")
            if doctype_filter:
                conditions.append("e.reference_doctype = %(doctype)s")
                params["doctype"] = doctype_filter

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Count total
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `tabError Log` e
            WHERE {where_clause}
        """
        total = frappe.db.sql(count_query, params)[0].total

        # Get results
        offset = (page - 1) * page_size
        query = f"""
            SELECT e.name, e.title, e.method, e.error, e.reference_doctype,
                   e.reference_name, e.creation, e.owner,
                   LEFT(e.error, 200) as error_preview
            FROM `tabError Log` e
            WHERE {where_clause}
            ORDER BY e.creation DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """
        params["limit"] = page_size
        params["offset"] = offset

        results = frappe.db.sql(query, params, as_dict=True)

        return {
            "status": "success",
            "logs": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_error_stats(days=30):
    """Get error log statistics for the past N days."""
    try:
        start_date = add_to_date(now_datetime(), days=-days)

        stats = frappe.db.sql("""
            SELECT 
                COUNT(*) as total_errors,
                COUNT(DISTINCT title) as unique_errors,
                MAX(creation) as latest_error
            FROM `tabError Log`
            WHERE creation >= %s
        """, start_date, as_dict=True)[0]

        by_type = frappe.db.sql("""
            SELECT title as error_type, COUNT(*) as count, MAX(creation) as last_occurrence
            FROM `tabError Log`
            WHERE creation >= %s
            GROUP BY title
            ORDER BY count DESC
            LIMIT 15
        """, start_date, as_dict=True)

        by_date = frappe.db.sql("""
            SELECT DATE(creation) as date, COUNT(*) as count
            FROM `tabError Log`
            WHERE creation >= %s
            GROUP BY DATE(creation)
            ORDER BY date DESC
            LIMIT 30
        """, start_date, as_dict=True)

        return {
            "status": "success",
            "stats": stats,
            "by_type": by_type,
            "by_date": by_date,
            "period_days": days
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def clear_old_error_logs(retention_days=90):
    """Clear error logs older than retention period (Admin only)."""
    try:
        if "HR Master Admin" not in frappe.get_roles():
            return {"status": "error", "message": _("Permission denied")}

        cutoff = add_to_date(now_datetime(), days=-retention_days)
        deleted = frappe.db.delete("Error Log", {
            "creation": ["<", cutoff]
        })

        return {
            "status": "success",
            "deleted": deleted,
            "message": _("Deleted {0} error logs older than {1} days").format(deleted, retention_days)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
