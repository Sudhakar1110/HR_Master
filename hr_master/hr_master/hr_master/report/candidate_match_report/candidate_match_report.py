"""Candidate Match Report Script for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
    """Execute the Candidate Match Report."""
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    """Return report columns."""
    return [
        {
            "fieldname": "ranking_order",
            "label": _("Rank"),
            "fieldtype": "Int",
            "width": 60,
        },
        {
            "fieldname": "candidate_name",
            "label": _("Candidate Name"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "job_title",
            "label": _("Job Title"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "total_match_score",
            "label": _("Match Score (%)"),
            "fieldtype": "Percent",
            "width": 120,
        },
        {
            "fieldname": "experience_match_score",
            "label": _("Experience Match"),
            "fieldtype": "Percent",
            "width": 120,
        },
        {
            "fieldname": "education_match_score",
            "label": _("Education Match"),
            "fieldtype": "Percent",
            "width": 120,
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "recommendation",
            "label": _("Recommendation"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "evaluation_date",
            "label": _("Evaluation Date"),
            "fieldtype": "Datetime",
            "width": 150,
        },
        {
            "fieldname": "job_description",
            "label": _("Job Description"),
            "fieldtype": "Link",
            "options": "Job Description",
            "width": 150,
        },
    ]


def get_data(filters):
    """Fetch report data based on filters."""
    conditions = get_conditions(filters)

    data = frappe.db.sql(
        f"""
        SELECT
            cr.ranking_order,
            cr.candidate_name,
            cr.job_title,
            cr.total_match_score,
            cr.experience_match_score,
            cr.education_match_score,
            cr.status,
            cr.recommendation,
            cr.evaluation_date,
            cr.job_description,
            cr.name as ranking_name
        FROM
            `tabCandidate Ranking` cr
        WHERE
            cr.docstatus < 2
            {conditions}
        ORDER BY
            cr.total_match_score DESC,
            cr.ranking_order ASC
        """,
        as_dict=True,
    )

    return data or []


def get_conditions(filters):
    """Build WHERE clause from filters."""
    conditions = ""
    if not filters:
        return conditions

    if filters.get("job_description"):
        conditions += f" AND cr.job_description = '{frappe.db.escape(filters['job_description'])}'"

    if filters.get("candidate"):
        conditions += f" AND cr.candidate = '{frappe.db.escape(filters['candidate'])}'"

    if filters.get("status"):
        conditions += f" AND cr.status = '{frappe.db.escape(filters['status'])}'"

    if filters.get("min_score"):
        conditions += f" AND cr.total_match_score >= {float(filters['min_score'])}"

    if filters.get("max_score"):
        conditions += f" AND cr.total_match_score <= {float(filters['max_score'])}"

    if filters.get("from_date"):
        conditions += f" AND cr.evaluation_date >= '{filters['from_date']}'"

    if filters.get("to_date"):
        conditions += f" AND cr.evaluation_date <= '{filters['to_date']}'"

    if filters.get("recommendation"):
        conditions += f" AND cr.recommendation = '{frappe.db.escape(filters['recommendation'])}'"

    return conditions


def get_chart(data):
    """Generate chart data."""
    if not data:
        return None

    labels = [d.candidate_name[:20] for d in data[:10]]
    scores = [d.total_match_score or 0 for d in data[:10]]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Match Score",
                    "values": scores,
                    "chartType": "bar",
                }
            ],
        },
        "type": "bar",
        "height": 300,
        "colors": ["#2490ef"],
        "axisOptions": {"x-axis-mode": "tick"},
    }


def get_summary(data):
    """Generate summary statistics."""
    if not data:
        return []

    total_ranked = len(data)
    avg_score = sum(d.total_match_score or 0 for d in data) / total_ranked if total_ranked > 0 else 0

    shortlisted = sum(1 for d in data if d.status == "Shortlisted")
    evaluated = sum(1 for d in data if d.status == "Evaluated")

    return [
        {
            "value": total_ranked,
            "label": _("Total Ranked"),
            "indicator": "Blue",
        },
        {
            "value": f"{avg_score:.1f}%",
            "label": _("Average Match Score"),
            "indicator": "Green" if avg_score >= 60 else "Orange",
        },
        {
            "value": shortlisted,
            "label": _("Shortlisted"),
            "indicator": "Green",
        },
        {
            "value": evaluated,
            "label": _("Evaluated"),
            "indicator": "Blue",
        },
    ]
