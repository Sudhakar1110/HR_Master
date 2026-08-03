"""HR Master Recruiting Portal - Dashboard page."""

from __future__ import unicode_literals

import frappe

from hr_master.api.portal_actions import (
    require_hr_access,
    set_portal_context,
    jd_visibility,
    visible_jd_names,
)


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

    jd_filters, jd_or_filters = jd_visibility()
    context.recent_jds = frappe.get_all(
        "Job Description",
        fields=["name", "job_title", "status", "location", "posting_date", "portal_search_status"],
        filters=jd_filters,
        or_filters=jd_or_filters,
        order_by="posting_date desc",
        limit=6,
    )

    # Hiring Managers should not see top matches from JDs outside their scope.
    visible = visible_jd_names()
    if visible is None:
        ranking_filters = {}
    else:
        ranking_filters = (
            {"job_description": ["in", visible]}
            if visible
            else {"job_description": "__no_visible_jd__"}
        )
    context.top_rankings = frappe.get_all(
        "Candidate Ranking",
        fields=["name", "candidate", "candidate_name", "job_title", "total_match_score", "status"],
        filters=ranking_filters,
        order_by="total_match_score desc",
        limit=6,
    )

    # ---- Chart data (rendered as pure CSS/SVG so the portal needs no CDN) ----
    context.funnel = _funnel_data()
    context.source_segments, context.source_total = _source_mix()
    context.offer_pipeline = _offer_pipeline()


def _funnel_data():
    """Progression of rankings through the pipeline + hired offers."""
    rows = frappe.db.sql(
        "SELECT status, COUNT(*) AS count FROM `tabCandidate Ranking` GROUP BY status",
        as_dict=True,
    )
    counts = {r.status: r.count for r in rows}
    hired = frappe.db.count("Offer Management", filters={"status": "Accepted"})

    stages = [
        ("Evaluated", counts.get("Pending", 0) + counts.get("Evaluated", 0), "#6366f1"),
        ("Shortlisted", counts.get("Shortlisted", 0), "#8b5cf6"),
        ("Interview", counts.get("Interview Scheduled", 0), "#3b82f6"),
        ("Selected", counts.get("Selected", 0), "#10b981"),
        ("Hired", hired, "#059669"),
    ]
    # Drop empty stages so the funnel stays clean and max is never 0
    return [{"label": label, "count": count, "color": color} for label, count, color in stages if count]


_SOURCE_PALETTE = [
    "#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#f43f5e",
    "#8b5cf6", "#06b6d4", "#ec4899", "#14b8a6", "#f97316",
]


def _source_mix(limit=7):
    """Candidate counts per source — capped, with the tail merged into 'Other'."""
    rows = frappe.db.sql(
        """SELECT source, COUNT(*) AS count FROM `tabCandidate`
        WHERE source IS NOT NULL AND source != ''
        GROUP BY source ORDER BY count DESC, source""",
        as_dict=True,
    )
    if len(rows) > limit:
        head = rows[: limit - 1]
        rest = sum(r.count for r in rows[limit - 1:])
        head.append({"source": "Other", "count": rest})
        rows = head

    total = sum(r.count for r in rows)
    if not total:
        return [], 0

    import math

    radius = 52.0
    circumference = 2 * math.pi * radius
    segments = []
    offset = 0.0
    for i, row in enumerate(rows):
        frac = row.count / float(total)
        seg = circumference * frac
        segments.append({
            "label": row.source or "Unknown",
            "count": row.count,
            "pct": round(frac * 100, 1),
            "color": _SOURCE_PALETTE[i % len(_SOURCE_PALETTE)],
            "dash": "%.4f %.4f" % (seg, circumference - seg),
            "offset": "%.4f" % (-offset),
        })
        offset += seg
    return segments, total


_OFFER_ORDER = [
    "Draft", "Approval Pending", "Approved", "Offer Sent",
    "Negotiation", "Accepted", "Declined", "Withdrawn",
]
_OFFER_COLORS = {
    "Draft": "#64748b",
    "Approval Pending": "#f59e0b",
    "Approved": "#3b82f6",
    "Offer Sent": "#6366f1",
    "Negotiation": "#8b5cf6",
    "Accepted": "#10b981",
    "Declined": "#f43f5e",
    "Withdrawn": "#94a3b8",
}


def _offer_pipeline():
    """Offers grouped by status, in pipeline order (zeros skipped)."""
    rows = frappe.db.sql(
        "SELECT status, COUNT(*) AS count FROM `tabOffer Management` GROUP BY status",
        as_dict=True,
    )
    by_status = {r.status: r.count for r in rows}
    result = []
    for status in _OFFER_ORDER:
        if by_status.get(status):
            result.append({"status": status, "count": by_status[status], "color": _OFFER_COLORS.get(status, "#64748b")})
    for status, count in by_status.items():
        if status not in _OFFER_ORDER and count:
            result.append({"status": status, "count": count, "color": "#64748b"})
    return result


def _avg_match_score():
    value = frappe.db.sql(
        "SELECT AVG(total_match_score) FROM `tabCandidate Ranking` "
        "WHERE total_match_score IS NOT NULL"
    )
    return round(value[0][0] or 0, 1) if value and value[0][0] else 0
