"""Portal reports for HR Master.

Surfaces the app's Desk script reports inside the recruiting portal, plus a
Source Performance report computed here (which portal drives shortlists and
hires). Also provides CSV / PDF export for every report.
"""

from __future__ import unicode_literals

import csv
import importlib
import io

import frappe
from frappe import _

# report_key -> (title, module path). "source_performance" is computed inline.
REPORTS = [
    {"key": "source_performance", "title": "Source Performance", "module": None},
    {
        "key": "hiring_funnel",
        "title": "Hiring Funnel",
        "module": "hr_master.hr_master.report.hiring_funnel_report.hiring_funnel_report",
    },
    {
        "key": "candidate_source",
        "title": "Candidate Source",
        "module": "hr_master.hr_master.report.candidate_source_report.candidate_source_report",
    },
    {
        "key": "offer_acceptance",
        "title": "Offer Acceptance",
        "module": "hr_master.hr_master.report.offer_acceptance_report.offer_acceptance_report",
    },
    {
        "key": "time_to_hire",
        "title": "Time to Hire",
        "module": "hr_master.hr_master.report.time_to_hire_report.time_to_hire_report",
    },
    {
        "key": "recruitment_dashboard",
        "title": "Recruitment Dashboard",
        "module": "hr_master.hr_master.report.recruitment_dashboard_report.recruitment_dashboard_report",
    },
    {
        "key": "recruiter_performance",
        "title": "Recruiter Performance",
        "module": "hr_master.hr_master.report.recruiter_performance_report.recruiter_performance_report",
    },
    {
        "key": "jd_analysis",
        "title": "JD Analysis",
        "module": "hr_master.hr_master.report.jd_analysis_report.jd_analysis_report",
    },
    {
        "key": "skill_gap",
        "title": "Skill Gap Analysis",
        "module": "hr_master.hr_master.report.skill_gap_analysis_report.skill_gap_analysis_report",
    },
    {
        "key": "candidate_match",
        "title": "Candidate Match",
        "module": "hr_master.hr_master.report.candidate_match_report.candidate_match_report",
    },
    {
        "key": "interview_performance",
        "title": "Interview Performance",
        "module": "hr_master.hr_master.report.interview_performance_report.interview_performance_report",
    },
    {
        "key": "recruitment_analytics",
        "title": "Recruitment Analytics",
        "module": "hr_master.hr_master.report.recruitment_analytics_report.recruitment_analytics_report",
    },
]

_PALETTE = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#f43f5e", "#8b5cf6", "#14b8a6"]


def get_report(key):
    """Return the report meta for a key (defaults to Source Performance)."""
    for meta in REPORTS:
        if meta["key"] == key:
            return meta
    return REPORTS[0]


def get_report_data(report_key):
    """Execute a report and normalize it for the portal.

    Returns a dict with title, columns, rows, labels, datasets, max_value,
    summary and report_key — or {"error": ...} if the report failed.
    """
    meta = get_report(report_key)
    try:
        if meta["module"] is None:
            columns, data, chart, summary = _source_performance()
        else:
            module = importlib.import_module(meta["module"])
            columns, data, _message, chart, summary = module.execute()
    except Exception as e:
        frappe.log_error(
            title="HR Master: portal report failed - {0}".format(meta["key"]),
            message=frappe.get_traceback(),
        )
        return {
            "report_key": meta["key"],
            "title": meta["title"],
            "error": str(e),
        }

    return _normalize(meta, columns or [], data or [], chart or {}, summary or [])


def _to_float(value):
    """Safe float coercion for chart values."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalize(meta, columns, data, chart, summary):
    """Convert a script-report result into portal-friendly structures."""
    labels = []
    datasets = []
    max_value = 0

    chart_data = (chart or {}).get("data") or {}
    if chart_data.get("labels") and chart_data.get("datasets"):
        labels = list(chart_data["labels"])
        for ds in chart_data["datasets"]:
            values = [_to_float(v) for v in (ds.get("values") or [])]
            if len(values) != len(labels):
                values = (values + [0] * len(labels))[: len(labels)]
            datasets.append({"name": ds.get("name") or "", "values": values})
        for ds in datasets:
            for v in ds["values"]:
                if v > max_value:
                    max_value = v
    else:
        # No usable chart — derive one from the numeric columns so every
        # report still renders a chart (labels come from the first column).
        numeric_cols = [
            c
            for c in columns[1:]
            if (c.get("fieldtype") or "").lower()
            in ("int", "float", "currency", "percent")
        ]
        if numeric_cols and data:
            first_col = columns[0]["fieldname"]
            labels = [str(r.get(first_col, "")) for r in data[:20]]
            for col in numeric_cols:
                values = [_to_float(r.get(col["fieldname"])) for r in data[:20]]
                datasets.append({"name": col["label"], "values": values})
                for v in values:
                    if v > max_value:
                        max_value = v

    for i, ds in enumerate(datasets):
        ds["color"] = _PALETTE[i % len(_PALETTE)]

    return {
        "report_key": meta["key"],
        "title": meta["title"],
        "columns": columns,
        "rows": data[:100],
        "labels": labels,
        "datasets": datasets,
        "max_value": max_value,
        "summary": summary,
    }


def _source_performance():
    """Which source drives the pipeline: candidates -> shortlisted -> hired."""
    columns = [
        {"fieldname": "source", "label": _("Source"), "fieldtype": "Data", "width": 160},
        {"fieldname": "candidates", "label": _("Candidates"), "fieldtype": "Int", "width": 90},
        {"fieldname": "shortlisted", "label": _("Shortlisted"), "fieldtype": "Int", "width": 90},
        {"fieldname": "interviewed", "label": _("Interviewed"), "fieldtype": "Int", "width": 90},
        {"fieldname": "offers", "label": _("Offers"), "fieldtype": "Int", "width": 80},
        {"fieldname": "hired", "label": _("Hired"), "fieldtype": "Int", "width": 80},
        {"fieldname": "conversion_rate", "label": _("Hire Rate %"), "fieldtype": "Percent", "width": 90},
    ]
    data = frappe.db.sql(
        """
        SELECT
            c.source AS source,
            COUNT(DISTINCT c.name) AS candidates,
            COUNT(DISTINCT CASE WHEN r.status IN ('Shortlisted','Interview Scheduled','Selected')
                                THEN c.name END) AS shortlisted,
            COUNT(DISTINCT CASE WHEN i.name IS NOT NULL AND i.status != 'Cancelled'
                                THEN c.name END) AS interviewed,
            COUNT(DISTINCT CASE WHEN o.name IS NOT NULL AND o.status NOT IN ('Declined','Withdrawn')
                                THEN c.name END) AS offers,
            COUNT(DISTINCT CASE WHEN o.status = 'Accepted' THEN c.name END) AS hired
        FROM `tabCandidate` c
        LEFT JOIN `tabCandidate Ranking` r ON r.candidate = c.name
        LEFT JOIN `tabInterview Schedule` i ON i.candidate = c.name
        LEFT JOIN `tabOffer Management` o ON o.candidate = c.name
        WHERE c.source IS NOT NULL AND c.source != '' AND c.docstatus < 2
        GROUP BY c.source
        ORDER BY candidates DESC, c.source
        """,
        as_dict=True,
    )
    for d in data:
        d["conversion_rate"] = round(
            (d["hired"] / d["candidates"] * 100) if d["candidates"] else 0, 1
        )

    chart = {
        "data": {
            "labels": [d["source"] for d in data],
            "datasets": [
                {"name": _("Candidates"), "values": [d["candidates"] for d in data]},
                {"name": _("Hired"), "values": [d["hired"] for d in data]},
            ],
        }
    }
    summary = [
        {
            "value": sum(d["candidates"] for d in data),
            "label": _("Candidates"),
            "indicator": "Blue",
        },
        {
            "value": sum(d["shortlisted"] for d in data),
            "label": _("Shortlisted"),
            "indicator": "Green",
        },
        {
            "value": sum(d["hired"] for d in data),
            "label": _("Hired"),
            "indicator": "Green",
        },
    ]
    return columns, data, chart, summary


@frappe.whitelist()
def export_report(report_key=None, file_format="csv"):
    """Export a portal report as CSV or PDF and return the private file URL."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))
    report_key = report_key or "source_performance"
    file_format = (file_format or "csv").lower()

    result = get_report_data(report_key)
    if result.get("error"):
        return {"status": "error", "message": result["error"]}

    headers = [(c.get("label") or c.get("fieldname") or "") for c in result["columns"]]
    fields = [c.get("fieldname") or "" for c in result["columns"]]
    rows = result["rows"]
    base_name = "{0}_{1}".format(
        report_key, frappe.utils.now_datetime().strftime("%Y%m%d_%H%M")
    )

    try:
        from frappe.utils.file_manager import save_file

        if file_format == "pdf":
            html = _report_html(result["title"], headers, fields, rows)
            from frappe.utils.pdf import get_pdf

            pdf = get_pdf(html)
            file_doc = save_file(
                fname="{0}.pdf".format(base_name),
                content=pdf,
                dt=None,
                dn=None,
                is_private=1,
            )
        else:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([row.get(f, "") for f in fields])
            content = output.getvalue()
            output.close()
            file_doc = save_file(
                fname="{0}.csv".format(base_name),
                content=content.encode("utf-8-sig"),
                dt=None,
                dn=None,
                is_private=1,
            )

        return {
            "status": "success",
            "file_url": file_doc.file_url,
            "file_name": file_doc.file_name,
            "rows": len(rows),
        }
    except Exception as e:
        frappe.log_error(
            title="HR Master: report export failed",
            message=frappe.get_traceback(),
        )
        return {
            "status": "error",
            "message": _(
                "Export failed: {0}. If you requested PDF, PDF rendering may not "
                "be installed on this server — use CSV instead."
            ).format(e),
        }


def _report_html(title, headers, fields, rows):
    """Minimal HTML table used for PDF export."""
    thead = "".join("<th>{0}</th>".format(frappe.utils.escape_html(h)) for h in headers)
    body = []
    for row in rows:
        body.append(
            "<tr>{0}</tr>".format(
                "".join(
                    "<td>{0}</td>".format(frappe.utils.escape_html(str(row.get(f, ""))))
                    for f in fields
                )
            )
        )
    return """
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
      body {{ font-family: sans-serif; color: #222; padding: 24px; }}
      h2 {{ margin-bottom: 4px; }}
      p {{ color: #666; font-size: 12px; margin-bottom: 16px; }}
      table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
      th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
      th {{ background: #f1f5f9; }}
    </style></head><body>
    <h2>{title}</h2>
    <p>Generated by HR Master · {date}</p>
    <table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>
    </body></html>
    """.format(
        title=frappe.utils.escape_html(title),
        date=frappe.utils.now_datetime().strftime("%d %b %Y %H:%M"),
        thead=thead,
        tbody="".join(body),
    )
