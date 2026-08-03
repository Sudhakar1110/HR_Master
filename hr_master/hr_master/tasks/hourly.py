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


def send_interview_reminders():
    """Hourly task: email reminders for interviews starting within the lead window.

    Uses Job Portal Config → 'Enable Interview Reminder Emails' + 'Reminder
    Lead Time (hours)' (default 24h). Each interview gets one reminder
    (reminder_sent flag prevents duplicates).
    """
    try:
        config = frappe.get_single("Job Portal Config")
        if not getattr(config, "interview_reminders_enabled", 1):
            return
        hours = int(getattr(config, "interview_reminder_hours", 0) or 24)

        from frappe.utils import now_datetime, add_to_date

        now = now_datetime()
        window_end = add_to_date(now, hours=hours)

        upcoming = frappe.get_all(
            "Interview Schedule",
            filters={"status": ["in", ["Scheduled", "Rescheduled"]], "reminder_sent": 0},
            fields=[
                "name",
                "candidate",
                "candidate_name",
                "job_title",
                "scheduled_date",
                "scheduled_time",
                "location_or_link",
                "owner",
            ],
            limit_page_length=100,
        )

        sent = 0
        for iv in upcoming:
            try:
                dt = _schedule_datetime(iv.scheduled_date, iv.scheduled_time)
                if dt is None:
                    continue
                if now <= dt <= window_end:
                    _send_reminder_for(iv)
                    frappe.db.set_value("Interview Schedule", iv.name, "reminder_sent", 1)
                    sent += 1
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error(
                    message=f"Reminder error for {iv.get('name')}: {str(e)}",
                    title="Interview Reminder Error",
                )

        if sent:
            frappe.logger().info(
                f"HR Master: sent {sent} interview reminder email(s)"
            )
    except Exception as e:
        frappe.log_error(
            message=f"Interview reminders error: {str(e)}",
            title="Interview Reminder Error",
        )


def _schedule_datetime(scheduled_date, scheduled_time):
    """Combine a Date + Time value into a datetime, or None when invalid."""
    if not scheduled_date:
        return None
    time_val = _as_time(scheduled_time) if scheduled_time else None
    if time_val is None:
        return None
    from datetime import datetime

    from frappe.utils import getdate

    return datetime.combine(getdate(scheduled_date), time_val)


def _as_time(value):
    """Normalise a Frappe Time value to datetime.time."""
    from datetime import time as dtime, timedelta

    if value is None:
        return None
    if isinstance(value, dtime):
        return value
    if isinstance(value, str) and ":" in value:
        try:
            parts = value.split(":")
            sec = int(parts[2].split(".")[0]) if len(parts) > 2 else 0
            return dtime(int(parts[0]), int(parts[1]), sec)
        except (ValueError, IndexError):
            return None
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        return dtime(total // 3600, (total % 3600) // 60)
    return None


def _send_reminder_for(iv):
    """Send the reminder email for one interview (candidate + interviewers)."""
    from hr_master.api.portal_actions import (
        _get_company_name,
        _get_recruiter_name,
        _render_email_template,
    )

    candidate = frappe.get_doc("Candidate", iv["candidate"])
    if not (candidate.email or "").strip():
        return

    context = {
        "candidate_name": candidate.candidate_name,
        "job_title": iv.get("job_title") or "",
        "company_name": _get_company_name(),
        "scheduled_date": str(iv.get("scheduled_date") or ""),
        "scheduled_time": str(iv.get("scheduled_time") or ""),
        "interview_link": iv.get("location_or_link") or "",
        "recruiter_name": _get_recruiter_name(),
    }
    subject, message = _render_email_template(
        "Interview Invitation",
        context,
        "Reminder: Interview tomorrow at {0}".format(context["scheduled_time"]),
    )
    if not subject.lower().startswith("reminder"):
        subject = "Reminder: " + subject

    recipients = [candidate.email]
    iv_doc = frappe.get_doc("Interview Schedule", iv["name"])
    for row in iv_doc.interviewers or []:
        if (row.email or "").strip() and row.email not in recipients:
            recipients.append(row.email)

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        reference_doctype="Interview Schedule",
        reference_name=iv["name"],
        now=True,
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
