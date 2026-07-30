"""Background Job Monitoring for HR Master

Provides visibility into background job execution status, failures,
and performance metrics.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date


@frappe.whitelist()
def get_job_stats(days=7):
    """Get background job statistics for the past N days."""
    try:
        start_date = add_to_date(now_datetime(), days=-days)

        stats = frappe.db.sql("""
            SELECT 
                COALESCE(SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END), 0) as completed,
                COALESCE(SUM(CASE WHEN status = 'Running' THEN 1 ELSE 0 END), 0) as running,
                COALESCE(SUM(CASE WHEN status = 'Queued' THEN 1 ELSE 0 END), 0) as queued,
                COALESCE(SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END), 0) as failed,
                COALESCE(SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END), 0) as cancelled,
                COUNT(*) as total
            FROM `tabScheduled Job Log`
            WHERE creation >= %s
        """, start_date, as_dict=True)[0]

        # Get failure details
        failures = frappe.db.sql("""
            SELECT name, job_type, method_name, status, `error`, creation, modified
            FROM `tabScheduled Job Log`
            WHERE status = 'Failed'
                AND creation >= %s
            ORDER BY creation DESC
            LIMIT 20
        """, start_date, as_dict=True)

        success_rate = 0
        if stats.get("total", 0) > 0:
            success_rate = round(
                (stats.get("completed", 0) / stats.get("total", 0)) * 100, 1
            )

        return {
            "status": "success",
            "stats": {
                "total": stats.get("total", 0),
                "completed": stats.get("completed", 0),
                "running": stats.get("running", 0),
                "queued": stats.get("queued", 0),
                "failed": stats.get("failed", 0),
                "cancelled": stats.get("cancelled", 0),
                "success_rate": success_rate
            },
            "recent_failures": failures,
            "period_days": days
        }

    except Exception as e:
        frappe.log_error(message=f"Job monitor error: {str(e)}", title="Job Monitor Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_running_jobs():
    """Get currently running background jobs."""
    try:
        jobs = frappe.db.sql("""
            SELECT name, job_type, method_name, `status`, creation, 
                   modified, `owner`
            FROM `tabScheduled Job Log`
            WHERE status IN ('Running', 'Queued')
            ORDER BY creation DESC
            LIMIT 50
        """, as_dict=True)

        return {
            "status": "success",
            "running_jobs": jobs,
            "count": len(jobs)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def retry_failed_job(job_name):
    """Retry a failed background job (Admin only)."""
    try:
        if "HR Master Admin" not in frappe.get_roles():
            return {"status": "error", "message": _("Permission denied")}

        log = frappe.get_doc("Scheduled Job Log", job_name)
        if log.status != "Failed":
            return {"status": "error", "message": _("Job is not in Failed status")}

        frappe.enqueue(
            method=log.method_name,
            queue="long" if "long" in log.job_type.lower() else "default",
            timeout=300
        )

        return {"status": "success", "message": _("Job re-queued: {0}").format(log.method_name)}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_job_performance(job_method=None, days=30):
    """Get performance metrics for background jobs."""
    try:
        start_date = add_to_date(now_datetime(), days=-days)

        filters = {"creation": [">=", start_date]}
        if job_method:
            filters["method_name"] = job_method

        job_data = frappe.db.sql("""
            SELECT method_name,
                   COUNT(*) as runs,
                   COALESCE(SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END), 0) as successes,
                   COALESCE(AVG(CASE WHEN status = 'Completed' THEN duration ELSE NULL END), 0) as avg_duration_seconds,
                   MAX(creation) as last_run
            FROM `tabScheduled Job Log`
            WHERE creation >= %s
                {method_filter}
            GROUP BY method_name
            ORDER BY runs DESC
            LIMIT 20
        """.format(
            method_filter="AND method_name = %(method)s" if job_method else ""
        ), [start_date, job_method] if job_method else [start_date], as_dict=True)

        return {
            "status": "success",
            "jobs": job_data,
            "period_days": days
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
