"""HR Master Recruiting Portal - Dashboard page."""

from __future__ import unicode_literals

import frappe

from hr_master.api.portal_actions import require_hr_access, set_portal_context


def get_context(context):
    """Render the dashboard with live KPIs, recent JDs and top matches."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "dashboard"
    context.page_title = "HR Dashboard"
    context.page_description = "Live recruitment overview — track candidates, job descriptions, shortlists, interviews, offers and average match scores at a glance."

    context.kpis = {
        "total_candidates": frappe.db.count("Candidate"),
        "active_jds": frappe.db.count(
            "Job Description",
            filters={"status": ["in", ["Open", "In Progress"]]},
        ),
        "shortlisted": frappe.db.count(
            "Candidate Ranking", filters={"status": "Shortlisted"}
        ),
        "interviews": frappe.db.count(
            "Interview Schedule",
            filters={"status": ["in", ["Scheduled", "Rescheduled", "In Progress"]]},
        ),
        "offers_released": frappe.db.count(
            "Offer Management",
            filters={"status": ["in", ["Offer Sent", "Negotiation", "Accepted", "Approved"]]},
        ),
        "hired": frappe.db.count("Offer Management", filters={"status": "Accepted"}),
        "avg_match": _avg_match_score(),
    }

    context.recent_jds = frappe.get_all(
        "Job Description",
        fields=["name", "job_title", "status", "location", "posting_date", "portal_search_status"],
        order_by="posting_date desc",
        limit=6,
    )

    context.top_rankings = frappe.get_all(
        "Candidate Ranking",
        fields=["name", "candidate_name", "job_title", "total_match_score", "status"],
        order_by="total_match_score desc",
        limit=6,
    )


def _avg_match_score():
    value = frappe.db.sql(
        "SELECT AVG(total_match_score) FROM `tabCandidate Ranking` "
        "WHERE total_match_score IS NOT NULL"
    )
    return round(value[0][0] or 0, 1) if value and value[0][0] else 0
