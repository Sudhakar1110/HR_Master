"""Hourly scheduled tasks for HR Master"""

from __future__ import unicode_literals

import frappe


def auto_rank_pending_candidates():
    """Hourly task: Auto-rank candidates that haven't been ranked yet."""
    pending_rankings = frappe.get_all(
        "Candidate Ranking",
        filters={"status": "Pending"},
        fields=["name", "job_description", "candidate"],
        limit=50,
    )

    ranked_count = 0
    for ranking in pending_rankings:
        try:
            jd = frappe.get_doc("Job Description", ranking.job_description)
            candidate = frappe.get_doc("Candidate", ranking.candidate)

            from hr_master.api.ranking_api import calculate_and_save_ranking

            calculate_and_save_ranking(jd, candidate.as_dict())
            ranked_count += 1
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                message=f"Auto-rank error for {ranking.name}: {str(e)}",
                title="Hourly Auto-Rank Error",
            )

    if ranked_count > 0:
        frappe.logger().info(
            f"HR Master: Auto-ranked {ranked_count} pending candidates"
        )


def process_pending_search_results():
    """Hourly task: Process pending search results and import candidates."""
    pending_imports = frappe.get_all(
        "Portal Search Result",
        filters={"import_status": "Pending"},
        fields=["parent", "name"],
        limit=100,
    )

    processed = set()
    for result in pending_imports:
        if result.parent not in processed:
            try:
                from hr_master.api.search_api import import_search_results

                import_search_results(result.parent)
                processed.add(result.parent)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(
                    message=f"Import error for {result.parent}: {str(e)}",
                    title="Hourly Import Error",
                )
