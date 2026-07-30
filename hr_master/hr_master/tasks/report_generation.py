"""Scheduled report generation and email distribution for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import today, now_datetime, add_days, getdate, format_date


def generate_daily_report():
    """Cron: Generate and email daily recruitment digest."""
    try:
        settings = frappe.get_single("Recruitment Settings")
        if not settings.daily_digest_enabled:
            return

        report_data = collect_daily_metrics()
        recipients = get_report_recipients(settings)

        if recipients:
            send_report_email(
                recipients=recipients,
                subject=_("Daily Recruitment Digest - {0}").format(format_date(today())),
                template="daily_digest",
                data=report_data
            )

        frappe.logger().info("HR Master: Daily digest report generated")

    except Exception as e:
        frappe.log_error(
            message=f"Daily report generation error: {str(e)}",
            title="Report Generation Error"
        )


def generate_weekly_report():
    """Cron: Generate and email weekly recruitment report."""
    try:
        settings = frappe.get_single("Recruitment Settings")
        if not settings.weekly_report_enabled:
            return

        report_data = collect_weekly_metrics()
        recipients = get_report_recipients(settings)

        if recipients:
            send_report_email(
                recipients=recipients,
                subject=_("Weekly Recruitment Report - Week of {0}").format(format_date(today())),
                template="weekly_report",
                data=report_data
            )

        frappe.logger().info("HR Master: Weekly recruitment report generated")

    except Exception as e:
        frappe.log_error(
            message=f"Weekly report generation error: {str(e)}",
            title="Report Generation Error"
        )


def collect_daily_metrics():
    """Collect daily recruitment metrics."""
    today_date = today()

    return {
        "new_candidates": frappe.db.count("Candidate", filters={
            "creation": [">=", today_date + " 00:00:00"],
            "creation": ["<=", today_date + " 23:59:59"]
        }),
        "interviews_today": frappe.db.count("Interview Schedule", filters={
            "scheduled_date": today_date,
            "status": "Scheduled"
        }),
        "new_applications": frappe.db.count("Candidate", filters={
            "status": "New",
            "creation": [">=", today_date + " 00:00:00"]
        }),
        "offers_sent_today": frappe.db.count("Offer Management", filters={
            "offer_date": today_date,
            "status": "Offer Sent"
        }),
        "offers_accepted_today": frappe.db.count("Offer Management", filters={
            "candidate_response_date": today_date,
            "status": "Accepted"
        }),
        "open_positions": frappe.db.count("Job Description", filters={
            "status": ["in", ["Open", "In Progress"]]
        }),
        "date": format_date(today_date)
    }


def collect_weekly_metrics():
    """Collect weekly recruitment metrics."""
    week_start = add_days(today(), -7)

    return {
        "new_candidates_week": frappe.db.count("Candidate", filters={
            "creation": [">=", week_start + " 00:00:00"]
        }),
        "interviews_scheduled_week": frappe.db.count("Interview Schedule", filters={
            "creation": [">=", week_start + " 00:00:00"]
        }),
        "offers_generated_week": frappe.db.count("Offer Management", filters={
            "creation": [">=", week_start + " 00:00:00"]
        }),
        "offers_accepted_week": frappe.db.count("Offer Management", filters={
            "status": "Accepted",
            "candidate_response_date": [">=", week_start]
        }),
        "hires_week": frappe.db.count("Candidate", filters={
            "status": "Selected",
            "modified": [">=", week_start + " 00:00:00"]
        }),
        "top_skills": get_top_skills_this_week(),
        "week_start": format_date(week_start),
        "week_end": format_date(today()),
        "open_positions": frappe.db.count("Job Description", filters={
            "status": ["in", ["Open", "In Progress"]]
        })
    }


def get_top_skills_this_week():
    """Get top skills from JDs created this week."""
    week_start = add_days(today(), -7)
    skills = frappe.db.sql("""
        SELECT sd.skill, COUNT(sd.parent) as count
        FROM `tabJD Skill Detail` sd
        INNER JOIN `tabJob Description` jd ON jd.name = sd.parent
        WHERE jd.creation >= %s
        GROUP BY sd.skill
        ORDER BY count DESC
        LIMIT 10
    """, week_start + " 00:00:00", as_dict=True)

    return [s.skill for s in skills] if skills else []


def get_report_recipients(settings):
    """Get list of report email recipients."""
    recipients = []
    cc = settings.get("cc_emails", "")
    if cc:
        recipients = [email.strip() for email in cc.split(",") if email.strip()]
    return recipients


def send_report_email(recipients, subject, template, data):
    """Send report email using Frappe's email system."""
    from frappe.utils import get_url

    if not recipients:
        return

    message = f"<h2>{subject}</h2><hr>"
    message += "<table style='width:100%; border-collapse: collapse;'>"

    for key, value in data.items():
        if isinstance(value, list):
            message += f"<tr><td style='padding:8px; border-bottom:1px solid #eee;'><strong>{_(key.replace('_', ' ').title())}</strong></td>"
            message += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{', '.join(value) if value else 'N/A'}</td></tr>"
        else:
            message += f"<tr><td style='padding:8px; border-bottom:1px solid #eee;'><strong>{_(key.replace('_', ' ').title())}</strong></td>"
            message += f"<td style='padding:8px; border-bottom:1px solid #eee;'>{value}</td></tr>"

    message += "</table><hr>"
    message += f"<p><small>Generated by <a href='{get_url()}'>HR Master</a> on {format_date(today())}</small></p>"

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        header=[subject, "blue"],
        now=True
    )
