"""Search index optimization tasks for HR Master

Rebuilds and optimizes Frappe's search indexes for better candidate and JD search performance.
Runs on a configurable schedule to maintain fast full-text search.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import now_datetime


def rebuild_search_index():
    """Weekly cron: Rebuild and optimize search indexes for key DocTypes."""
    try:
        doc_types = [
            "Candidate",
            "Job Description",
            "Resume",
            "Skill",
            "Interview Schedule",
            "Offer Management",
            "Candidate Ranking"
        ]

        results = {"rebuilt": [], "errors": []}

        for dt in doc_types:
            try:
                frappe.enqueue(
                    method="frappe.utils.global_search.rebuild_index_for_doctype",
                    queue="long",
                    timeout=600,
                    doctype=dt
                )
                results["rebuilt"].append(dt)
            except Exception as e:
                results["errors"].append(f"{dt}: {str(e)}")

        frappe.logger().info(
            f"HR Master Search Index: Rebuilt {len(results['rebuilt'])} indexes, "
            f"{len(results['errors'])} errors"
        )

        # Log audit entry
        from hr_master.doctype.candidate_activity_log.candidate_activity_log import log_activity
        log_activity(
            candidate="",
            activity_type="System Action",
            description=f"Search index rebuild: {', '.join(results['rebuilt'])}",
            reference_doctype="",
            reference_name=""
        )

        return results

    except Exception as e:
        frappe.log_error(
            message=f"Search index rebuild error: {str(e)}",
            title="Search Index Error"
        )


def optimize_search_queries():
    """Optimize database for common search patterns."""
    try:
        # Analyze tables used in search
        tables = [
            "tabCandidate",
            "tabJob Description",
            "tabResume",
            "tabSkill",
            "tabCandidate Ranking",
            "tabInterview Schedule",
            "tabOffer Management"
        ]

        for table in tables:
            try:
                frappe.db.sql(f"OPTIMIZE TABLE {table}")
            except Exception:
                pass

        frappe.logger().info("HR Master: Search query optimization completed")

    except Exception as e:
        frappe.log_error(
            message=f"Search optimization error: {str(e)}",
            title="Search Optimization Error"
        )


def get_search_stats():
    """Get search index statistics for monitoring."""
    from frappe.utils import now_datetime

    stats = {}
    doc_types = [
        "Candidate", "Job Description", "Resume",
        "Skill", "Interview Schedule", "Offer Management", "Candidate Ranking"
    ]

    for dt in doc_types:
        stats[dt] = frappe.db.count(dt)

    stats["last_rebuilt"] = now_datetime()
    return stats
