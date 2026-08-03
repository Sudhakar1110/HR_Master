"""HR Master Recruiting Portal - Candidate detail & actions page."""

from __future__ import unicode_literals

import json

import frappe
from frappe import _

from hr_master.api.portal_actions import (
    require_hr_access,
    can_write,
    require_write_access,
    set_ranking_status,
    schedule_interview,
    create_offer,
    send_offer_email,
    send_interview_invite_email,
    send_rejection_email,
    submit_feedback,
    redirect_with_flash,
    render_flash,
    set_portal_context,
    can_approve_offers,
    review_offer,
)


def get_context(context):
    """Render candidate details; handle workflow / interview / offer / feedback actions."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "candidates"
    context.can_write = can_write()

    candidate_name = frappe.form_dict.get("name")
    if not candidate_name or not frappe.db.exists("Candidate", candidate_name):
        frappe.local.flags.redirect_location = "/hr_portal"
        raise frappe.Redirect

    # Handle POST actions - PRG pattern with server-side write guard
    if frappe.request.method == "POST":
        action = frappe.form_dict.get("action")
        base_path = "/hr_portal/candidate?name={0}".format(candidate_name)
        try:
            # Offer approval is done by Admins / Hiring Managers — it must NOT
            # require the write role, so it runs before require_write_access().
            if action in ("approve_offer", "reject_offer"):
                offer_name = frappe.form_dict.get("offer")
                result = review_offer(
                    offer_name,
                    approve=(action == "approve_offer"),
                )
                message = result.get("message") or (
                    "Offer approved" if action == "approve_offer" else "Offer rejected"
                )
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash(base_path, message, flash_type)

            require_write_access()

            if action in (
                "Evaluate",
                "Shortlist",
                "Reject",
                "Schedule Interview",
                "Put on Hold",
                "Re-evaluate",
                "Hire",
            ):
                ranking_name = frappe.form_dict.get("ranking")
                if ranking_name and frappe.db.exists("Candidate Ranking", ranking_name):
                    set_ranking_status(ranking_name, action)
                    redirect_with_flash(base_path, "Status updated: {0}".format(action))
                else:
                    frappe.throw(_("Ranking not found"))
            elif action == "schedule_interview":
                data = {k: v for k, v in frappe.form_dict.items() if k != "csrf_token"}
                result = schedule_interview(json.dumps(data))
                redirect_with_flash(
                    base_path, "Interview scheduled: {0}".format(result.get("name"))
                )
            elif action == "create_offer":
                data = {k: v for k, v in frappe.form_dict.items() if k != "csrf_token"}
                result = create_offer(json.dumps(data))
                redirect_with_flash(
                    base_path, "Offer created: {0}".format(result.get("name"))
                )
            elif action == "submit_feedback":
                data = {k: v for k, v in frappe.form_dict.items() if k != "csrf_token"}
                result = submit_feedback(json.dumps(data))
                redirect_with_flash(
                    base_path, "Feedback submitted: {0}".format(result.get("name"))
                )
            elif action == "send_offer":
                result = send_offer_email(frappe.form_dict.get("offer"))
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash(
                    base_path, result.get("message") or "Offer email sent", flash_type
                )
            elif action == "send_invite":
                result = send_interview_invite_email(frappe.form_dict.get("interview"))
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash(
                    base_path, result.get("message") or "Invite emailed", flash_type
                )
            elif action == "RejectEmail":
                result = send_rejection_email(frappe.form_dict.get("ranking"))
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash(
                    base_path, result.get("message") or "Candidate rejected", flash_type
                )
            else:
                frappe.throw(_("Unknown action"))
        except frappe.Redirect:
            raise
        except Exception as e:
            context.flash = {"type": "error", "message": str(e)}

    render_flash(context)

    candidate = frappe.get_doc("Candidate", candidate_name)
    context.candidate = candidate
    context.page_title = candidate.candidate_name
    context.page_description = "Candidate profile — skills, rankings, interviews, offers and feedback for {0}.".format(candidate.candidate_name)

    context.rankings = frappe.get_all(
        "Candidate Ranking",
        fields=[
            "name",
            "job_description",
            "job_title",
            "total_match_score",
            "experience_match_score",
            "education_match_score",
            "status",
            "recommendation",
            "evaluation_date",
        ],
        filters={"candidate": candidate_name},
        order_by="evaluation_date desc",
        limit_page_length=50,
    )

    context.interviews = frappe.get_all(
        "Interview Schedule",
        fields=[
            "name",
            "job_title",
            "scheduled_date",
            "scheduled_time",
            "interview_round",
            "interview_type",
            "status",
            "result",
            "invite_email_sent",
            "invite_email_sent_at",
            "reminder_sent",
            "reminder_sent_at",
        ],
        filters={"candidate": candidate_name},
        order_by="scheduled_date desc",
        limit_page_length=50,
    )

    context.can_approve_offers = can_approve_offers()
    context.offers = frappe.get_all(
        "Offer Management",
        fields=[
            "name",
            "job_title",
            "status",
            "approval_status",
            "approved_by",
            "approval_date",
            "total_ctc",
            "offer_date",
            "expected_joining_date",
            "offer_email_sent_at",
        ],
        filters={"candidate": candidate_name},
        order_by="offer_date desc",
        limit_page_length=20,
    )
    try:
        settings = frappe.get_single("Recruitment Settings")
        _require_approval = bool(settings.get("require_approval_for_offers"))
    except Exception:
        _require_approval = False
    for o in context.offers:
        o["needs_approval"] = (
            _require_approval
            and o.get("status") in ("Draft", "Approval Pending")
            and o.get("approval_status") != "Approved"
        )
        o["sendable"] = o.get("status") in ("Draft", "Approval Pending", "Approved") and not o["needs_approval"]

    context.feedback_list = frappe.get_all(
        "Interview Feedback",
        fields=["name", "interview_schedule", "interviewer", "recommendation", "result", "submitted_date"],
        filters={"candidate": candidate_name},
        order_by="submitted_date desc",
        limit_page_length=20,
    )

    context.users = frappe.get_all(
        "User",
        filters={"enabled": 1, "name": ["!=", "Guest"]},
        pluck="name",
        limit_page_length=0,
    ) or []

    return context
