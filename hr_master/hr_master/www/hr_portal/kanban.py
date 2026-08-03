"""HR Master Recruiting Portal - Kanban pipeline board page."""

from __future__ import unicode_literals

import frappe

from hr_master.api.portal_actions import (
    can_write,
    require_hr_access,
    set_portal_context,
)

# Kanban columns -> workflow action applied when a card is dropped there
COLUMNS = [
    {"name": "Screened", "label": "Screened", "icon": "📋", "statuses": ["Pending", "Evaluated"], "color": "blue"},
    {"name": "Shortlisted", "label": "Shortlisted", "icon": "⭐", "statuses": ["Shortlisted"], "color": "green"},
    {"name": "Interview", "label": "Interview", "icon": "🗓️", "statuses": ["Interview Scheduled"], "color": "purple"},
    {"name": "Selected", "label": "Selected / Hired", "icon": "🎉", "statuses": ["Selected"], "color": "green"},
    {"name": "On Hold", "label": "On Hold", "icon": "⏸️", "statuses": ["On Hold"], "color": "orange"},
    {"name": "Rejected", "label": "Rejected", "icon": "🚫", "statuses": ["Rejected"], "color": "red"},
]

STATUS_TO_COLUMN = {}
for col in COLUMNS:
    for status in col["statuses"]:
        STATUS_TO_COLUMN[status] = col["name"]


def get_context(context):
    """Render the pipeline board with all rankings (optionally filtered by JD)."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "kanban"
    context.can_write = can_write()

    jd_name = frappe.form_dict.get("jd")
    filters = {}
    if jd_name and frappe.db.exists("Job Description", jd_name):
        filters["job_description"] = jd_name
        context.jd = jd_name
    else:
        context.jd = ""

    context.page_title = "Candidate Pipeline"
    context.page_description = "Drag candidates between stages — Screened → Shortlisted → Interview → Selected/Hired."

    rankings = frappe.get_all(
        "Candidate Ranking",
        fields=[
            "name",
            "candidate",
            "candidate_name",
            "job_description",
            "job_title",
            "total_match_score",
            "status",
        ],
        filters=filters,
        order_by="total_match_score desc",
        limit_page_length=300,
    )

    # Candidate source / location for the cards
    names = [r["candidate"] for r in rankings if r.get("candidate")]
    cand_map = {}
    if names:
        cand_rows = frappe.get_all(
            "Candidate",
            fields=["name", "source", "location"],
            filters={"name": ["in", names]},
            limit_page_length=0,
        )
        cand_map = {row["name"]: row for row in cand_rows}

    for r in rankings:
        info = cand_map.get(r.get("candidate")) or {}
        r["source"] = info.get("source") or ""
        r["candidate_location"] = info.get("location") or ""
        r["column"] = STATUS_TO_COLUMN.get(r.get("status"), "Screened")

    context.rankings = rankings
    context.columns = COLUMNS
    context.jds = frappe.get_all(
        "Job Description",
        fields=["name", "job_title"],
        order_by="modified desc",
        limit_page_length=100,
    ) or []

    return context
