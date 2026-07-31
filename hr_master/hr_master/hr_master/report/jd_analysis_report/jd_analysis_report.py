"""JD Analysis Report Script for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
    """Execute the JD Analysis Report."""
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    """Return report columns."""
    return [
        {
            "fieldname": "job_title",
            "label": _("Job Title"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "posting_date",
            "label": _("Posting Date"),
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "fieldname": "vacancies",
            "label": _("Vacancies"),
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "fieldname": "total_candidates",
            "label": _("Total Candidates"),
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "fieldname": "avg_match_score",
            "label": _("Avg Match Score"),
            "fieldtype": "Percent",
            "width": 120,
        },
        {
            "fieldname": "shortlisted",
            "label": _("Shortlisted"),
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "fieldname": "interviews_scheduled",
            "label": _("Interviews"),
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "fieldname": "selected",
            "label": _("Selected"),
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "fieldname": "portal_search_status",
            "label": _("Search Status"),
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "fieldname": "name",
            "label": _("JD ID"),
            "fieldtype": "Link",
            "options": "Job Description",
            "width": 120,
        },
    ]


def get_data(filters):
    """Fetch report data based on filters."""
    conditions = get_conditions(filters)

    data = frappe.db.sql(
        f"""
        SELECT
            jd.name,
            jd.job_title,
            jd.department,
            jd.status,
            jd.posting_date,
            jd.vacancies,
            jd.portal_search_status,
            COALESCE(cr_stats.total_candidates, 0) as total_candidates,
            COALESCE(cr_stats.avg_score, 0) as avg_match_score,
            COALESCE(cr_stats.shortlisted, 0) as shortlisted,
            COALESCE(cr_stats.interviews, 0) as interviews_scheduled,
            COALESCE(cr_stats.selected, 0) as selected
        FROM
            `tabJob Description` jd
        LEFT JOIN (
            SELECT
                cr.job_description,
                COUNT(cr.name) as total_candidates,
                AVG(cr.total_match_score) as avg_score,
                SUM(CASE WHEN cr.status = 'Shortlisted' THEN 1 ELSE 0 END) as shortlisted,
                SUM(CASE WHEN cr.status = 'Interview Scheduled' THEN 1 ELSE 0 END) as interviews,
                SUM(CASE WHEN cr.status = 'Selected' THEN 1 ELSE 0 END) as selected
            FROM
                `tabCandidate Ranking` cr
            WHERE
                cr.docstatus < 2
            GROUP BY
                cr.job_description
        ) cr_stats ON cr_stats.job_description = jd.name
        WHERE
            jd.docstatus < 2
            {conditions}
        ORDER BY
            jd.posting_date DESC,
            jd.job_title ASC
        """,
        as_dict=True,
    )

    return data or []


def get_conditions(filters):
    """Build WHERE clause from filters."""
    conditions = ""
    if not filters:
        return conditions

    if filters.get("department"):
        conditions += f" AND jd.department = '{frappe.db.escape(filters['department'])}'"

    if filters.get("status"):
        conditions += f" AND jd.status = '{frappe.db.escape(filters['status'])}'"

    if filters.get("from_date"):
        conditions += f" AND jd.posting_date >= '{filters['from_date']}'"

    if filters.get("to_date"):
        conditions += f" AND jd.posting_date <= '{filters['to_date']}'"

    if filters.get("job_title"):
        conditions += f" AND jd.job_title LIKE '%{frappe.db.escape(filters['job_title'])}%'"

    return conditions


def get_chart(data):
    """Generate chart data."""
    if not data:
        return None

    labels = [d.job_title[:25] for d in data[:10]]
    total_candidates = [d.total_candidates or 0 for d in data[:10]]
    shortlisted = [d.shortlisted or 0 for d in data[:10]]
    interviews = [d.interviews_scheduled or 0 for d in data[:10]]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Candidates",
                    "values": total_candidates,
                    "chartType": "bar",
                },
                {
                    "name": "Shortlisted",
                    "values": shortlisted,
                    "chartType": "bar",
                },
                {
                    "name": "Interviews",
                    "values": interviews,
                    "chartType": "bar",
                },
            ],
        },
        "type": "bar",
        "height": 300,
        "colors": ["#2490ef", "#5cb85c", "#f0ad4e"],
        "axisOptions": {"x-axis-mode": "tick"},
        "barOptions": {"stacked": True},
    }


def get_summary(data):
    """Generate summary statistics."""
    if not data:
        return []

    total_jds = len(data)
    total_vacancies = sum(d.vacancies or 0 for d in data)
    total_candidates = sum(d.total_candidates or 0 for d in data)
    total_shortlisted = sum(d.shortlisted or 0 for d in data)
    total_selected = sum(d.selected or 0 for d in data)

    open_jds = sum(1 for d in data if d.status == "Open")
    filled_jds = sum(1 for d in data if d.status == "Filled")

    return [
        {
            "value": total_jds,
            "label": _("Total JDs"),
            "indicator": "Blue",
        },
        {
            "value": open_jds,
            "label": _("Open JDs"),
            "indicator": "Green",
        },
        {
            "value": total_vacancies,
            "label": _("Total Vacancies"),
            "indicator": "Blue",
        },
        {
            "value": total_candidates,
            "label": _("Total Candidates"),
            "indicator": "Blue",
        },
        {
            "value": total_shortlisted,
            "label": _("Shortlisted"),
            "indicator": "Green",
        },
        {
            "value": total_selected,
            "label": _("Selected"),
            "indicator": "Green",
        },
    ]
