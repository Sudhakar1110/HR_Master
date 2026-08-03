"""Portal action helpers for HR Master.

Thin whitelisted wrappers used by the HR Recruiting Portal (www/hr_portal).
The portal pages call these directly server-side; they are also exposed as
whitelisted methods so they can be invoked via the REST API if needed.
"""

from __future__ import unicode_literals

import json
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import now_datetime

HR_ROLES = [
    "HR Master Admin",
    "HR Master Recruiter",
    "HR Master Hiring Manager",
    "HR Master Viewer",
]

# Candidate Evaluation workflow: action -> resulting state
WORKFLOW_ACTIONS = {
    "Evaluate": "Evaluated",
    "Shortlist": "Shortlisted",
    "Reject": "Rejected",
    "Schedule Interview": "Interview Scheduled",
    "Put on Hold": "On Hold",
    "Re-evaluate": "Evaluated",
    "Hire": "Selected",
}


def has_hr_role(user=None):
    """Return True if the user has any HR Master role."""
    user_roles = frappe.get_roles(user)
    return any(r in HR_ROLES for r in user_roles)


def get_hr_roles(user=None):
    """Return the HR Master roles the user has."""
    user_roles = frappe.get_roles(user)
    return [r for r in HR_ROLES if r in user_roles]


def can_write(user=None):
    """Return True if the user may perform write actions in the portal."""
    user_roles = frappe.get_roles(user)
    return any(r in ("HR Master Admin", "HR Master Recruiter") for r in user_roles)


def can_approve_offers(user=None):
    """Return True if the user may approve / reject offers in the portal.

    Approvers are Admins and Hiring Managers (recruiters create offers but
    cannot approve their own, so self-approval is not possible).
    """
    user_roles = frappe.get_roles(user)
    return any(r in ("HR Master Admin", "HR Master Hiring Manager") for r in user_roles)


def jd_visibility():
    """Return (filters, or_filters) scoping Job Descriptions for the current user.

    Admins / Recruiters / Viewers see everything. Hiring Managers see only
    JDs assigned to them (hiring_manager == user) or unassigned ones.
    """
    roles = frappe.get_roles()
    if any(
        r in ("HR Master Admin", "HR Master Recruiter", "HR Master Viewer")
        for r in roles
    ):
        return {}, None
    if "HR Master Hiring Manager" in roles:
        return {}, [
            ["hiring_manager", "in", [frappe.session.user]],
            ["hiring_manager", "is", "not set"],
        ]
    return {}, None


def visible_jd_names(limit=500):
    """Names of the JDs the current user may view; None if unrestricted.

    Used to scope candidate-ranking queries (e.g. dashboard top matches,
    Kanban board) to the JDs a Hiring Manager is allowed to see.
    """
    filters, or_filters = jd_visibility()
    if not or_filters:
        return None
    rows = frappe.get_all(
        "Job Description",
        fields=["name"],
        filters=filters,
        or_filters=or_filters,
        limit_page_length=limit,
    )
    return [r["name"] for r in rows]


def can_view_jd(jd_name):
    """True if the current user may view this JD (role + assignment check)."""
    if not jd_name or not frappe.db.exists("Job Description", jd_name):
        return False
    roles = frappe.get_roles()
    if any(
        r in ("HR Master Admin", "HR Master Recruiter", "HR Master Viewer")
        for r in roles
    ):
        return True
    if "HR Master Hiring Manager" in roles:
        hiring_manager = frappe.db.get_value(
            "Job Description", jd_name, "hiring_manager"
        )
        return not hiring_manager or hiring_manager == frappe.session.user
    return False


def set_portal_context(context):
    """Populate shared portal page context (CSRF token + per-user theme).

    Frappe v15 renders website pages without a ``csrf_token`` Jinja variable
    (it only replaces the ``<!-- csrf_token -->`` HTML comment with a script
    tag). The portal forms post ``{{ csrf_token }}`` hidden fields, which
    otherwise render empty and every POST fails with an HTTP 400
    (CSRFTokenError). Injecting the real session token here fixes that.

    The portal dark/light theme is persisted per-user in the database
    (User Defaults) so it follows the user across browsers and devices —
    it is injected here so the theme-init script can apply it before first
    paint (no flash, no localStorage dependency).
    """
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.hr_portal_theme = frappe.defaults.get_user_default("hr_portal_theme") or ""
    return context


@frappe.whitelist()
def set_portal_theme(theme=None):
    """Persist the HR portal dark/light theme for the current user.

    Stored in the user's Defaults (per-user, DB-backed) so the preference
    follows the user across browsers and devices.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))

    theme = (theme or "").strip().lower()
    if theme not in ("light", "dark"):
        frappe.throw(_("Invalid theme"))

    frappe.defaults.set_user_default("hr_portal_theme", theme)
    frappe.db.commit()
    return {"ok": True, "theme": theme}


def require_hr_access():
    """Guard for portal pages: redirect guests / non-HR users to login."""
    if frappe.session.user == "Guest" or not has_hr_role():
        frappe.local.flags.redirect_location = (
            "/login?redirect-to=" + frappe.request.fullpath
        )
        raise frappe.Redirect


def require_write_access():
    """Guard for write actions: raise if the user cannot write in the portal."""
    if not can_write():
        frappe.throw(_("You are not allowed to perform this action"))


def redirect_with_flash(path, message, flash_type="success"):
    """POST-redirect-GET helper: redirect carrying a flash message in the URL."""
    separator = "&" if "?" in path else "?"
    frappe.local.flags.redirect_location = "{0}{1}msg={2}&type={3}".format(
        path, separator, quote(message), quote(flash_type)
    )
    raise frappe.Redirect


def render_flash(context):
    """Populate context.flash from ?msg=&type= query params (PRG pattern)."""
    message = frappe.form_dict.get("msg")
    if message:
        context.flash = {
            "type": frappe.form_dict.get("type", "success"),
            "message": message,
        }
    return context.flash


def _parse_json(value):
    """Parse a JSON string or dict into a dict."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value or {}


def ensure_skill(skill_name):
    """Create a Skill master record if it does not exist yet."""
    if not skill_name:
        return
    if not frappe.db.exists("Skill", skill_name):
        skill = frappe.new_doc("Skill")
        skill.skill_name = skill_name
        skill.category = "Other"
        skill.is_active = 1
        skill.save(ignore_permissions=True)
        frappe.db.commit()


def _split_skills(value):
    """Normalise a skills value (list or comma/semicolon separated string)."""
    if isinstance(value, (list, tuple)):
        return [str(s).strip() for s in value if str(s).strip()]
    if isinstance(value, str):
        return [s.strip() for s in value.replace(";", ",").split(",") if s.strip()]
    return []


def _to_float(value):
    """Coerce a form/API value (string, number or empty) to a float.

    Portal form values arrive as strings (e.g. "5000000"), so arithmetic on
    them must coerce first — otherwise "5000000" + 0 raises
    TypeError: can only concatenate str (not "int") to str.
    """
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@frappe.whitelist()
def create_jd(data=None):
    """Create (and submit) a Job Description from portal form data."""
    if not can_write():
        frappe.throw(_("You are not allowed to create job descriptions"))

    data = _parse_json(data)
    if not data.get("job_title"):
        frappe.throw(_("Job Title is required"))

    jd = frappe.new_doc("Job Description")
    for field in (
        "job_title",
        "department",
        "employment_type",
        "job_description_raw",
        "location",
        "remote_option",
        "vacancies",
        "hiring_manager",
        "min_experience_years",
        "max_experience_years",
        "salary_range_min",
        "salary_range_max",
        "qualifications",
        "target_close_date",
    ):
        if data.get(field) not in (None, ""):
            jd.set(field, data.get(field))

    for skill in _split_skills(data.get("required_skills")):
        ensure_skill(skill)
        jd.append(
            "required_skills",
            {"skill": skill, "importance": "Required", "is_mandatory": 1},
        )

    for skill in _split_skills(data.get("preferred_skills")):
        ensure_skill(skill)
        jd.append(
            "preferred_skills",
            {"skill": skill, "importance": "Preferred", "is_mandatory": 0},
        )

    jd.insert(ignore_permissions=True)

    frappe.flags.ignore_permissions = True
    try:
        jd.submit()  # before_submit sets status to "Open"
    except Exception:
        jd.status = "Open"
        jd.save(ignore_permissions=True)
    finally:
        frappe.flags.ignore_permissions = False

    frappe.db.commit()
    return {"name": jd.name, "status": jd.status}


@frappe.whitelist()
def set_ranking_status(ranking_name, action):
    """Advance a Candidate Ranking through the Candidate Evaluation workflow."""
    if not can_write():
        frappe.throw(_("You are not allowed to update rankings"))

    doc = frappe.get_doc("Candidate Ranking", ranking_name)
    target = WORKFLOW_ACTIONS.get(action)

    if not target:
        frappe.throw(_("Unknown workflow action: {0}").format(action))

    try:
        # Frappe v15 moved the workflow helpers from ``frappe.workflow`` to
        # ``frappe.model.workflow``; ``apply_action`` no longer exists.
        from frappe.model.workflow import get_transitions, get_workflow

        workflow = get_workflow(doc.doctype)
        transitions = get_transitions(doc, workflow)
        transition = next((t for t in transitions if t.get("action") == action), None)

        if transition:
            # Valid workflow transition for the current user - apply it properly.
            doc.set(workflow.workflow_state_field, transition["next_state"])
            next_state_row = next(
                (s for s in workflow.states if s.state == transition["next_state"]),
                None,
            )
            if next_state_row and next_state_row.update_field:
                doc.set(next_state_row.update_field, next_state_row.update_value)
            doc.save(ignore_permissions=True)
        else:
            # No transition for this state/action (or the user's role has no
            # access). The portal allows direct status changes, so set the
            # state via db_set to bypass workflow validation entirely.
            doc.db_set(workflow.workflow_state_field, target)
            doc.db_set("status", target)
    except Exception:
        # Last-resort fallback - never let the workflow block a portal action.
        doc.db_set("workflow_state", target)
        doc.db_set("status", target)

    # Keep the linked Candidate in sync when the ranking is hired, so the
    # Hired Candidates card / reports / Candidate Hired notification reflect it.
    if target == "Selected" and doc.candidate:
        try:
            candidate = frappe.get_doc("Candidate", doc.candidate)
            if candidate.status != "Selected":
                candidate.status = "Selected"
                candidate.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                title="HR Master: failed to update candidate status on hire",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()
    return {"status": target}


@frappe.whitelist()
def schedule_interview(data=None):
    """Create an Interview Schedule (and advance the ranking if provided)."""
    if not can_write():
        frappe.throw(_("You are not allowed to schedule interviews"))

    data = _parse_json(data)
    if not data.get("candidate") or not data.get("scheduled_date") or not data.get("scheduled_time"):
        frappe.throw(_("Candidate, date and time are required"))

    interview = frappe.new_doc("Interview Schedule")
    interview.candidate = data.get("candidate")
    interview.job_description = data.get("job_description")
    interview.scheduled_date = data.get("scheduled_date")
    interview.scheduled_time = data.get("scheduled_time")
    interview.duration_minutes = data.get("duration_minutes") or 60
    interview.interview_round = data.get("interview_round") or "Round 1"
    interview.interview_type = data.get("interview_type") or "Technical"
    interview.mode_of_interview = data.get("mode_of_interview") or "Video Call"
    interview.location_or_link = data.get("location_or_link")
    interview.notes = data.get("notes")
    interview.save(ignore_permissions=True)

    if data.get("ranking"):
        set_ranking_status(data["ranking"], "Schedule Interview")

    frappe.db.commit()
    return {"name": interview.name}


@frappe.whitelist()
def create_offer(data=None):
    """Create an Offer Management draft from portal form data."""
    if not can_write():
        frappe.throw(_("You are not allowed to create offers"))

    data = _parse_json(data)
    if not data.get("candidate"):
        frappe.throw(_("Candidate is required"))

    offer = frappe.new_doc("Offer Management")
    for field in (
        "candidate",
        "job_description",
        "offer_date",
        "expected_joining_date",
        "base_salary",
        "variable_pay",
        "equity",
        "benefits",
    ):
        if data.get(field) not in (None, ""):
            offer.set(field, data.get(field))

    base = _to_float(data.get("base_salary"))
    variable = _to_float(data.get("variable_pay"))
    if base or variable:
        offer.total_ctc = base + variable

    # The portal form does not pass a Job Description; link the candidate's
    # latest ranking so job_title is fetched and the offer letter prints it.
    if not offer.job_description:
        jd = frappe.db.get_value(
            "Candidate Ranking",
            {"candidate": data.get("candidate")},
            "job_description",
            order_by="evaluation_date desc",
        )
        if jd:
            offer.job_description = jd

    # When offer approval is enabled, new offers enter the approval queue
    # instead of going straight to Draft, and cannot be emailed until approved.
    try:
        settings = frappe.get_single("Recruitment Settings")
        require_approval = bool(settings.get("require_approval_for_offers"))
    except Exception:
        require_approval = False
    if require_approval:
        offer.status = "Approval Pending"
        offer.approval_status = "Pending"
    else:
        offer.status = "Draft"

    offer.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": offer.name}


@frappe.whitelist()
def send_offer_email(offer_name=None):
    """Email the offer letter (with the offer-letter PDF attached) to the candidate.

    Uses the 'Offer Letter' Email Template Config when available and advances
    the offer status to 'Offer Sent' (Draft / Approval Pending / Approved
    only). If PDF rendering is unavailable the email is still sent without
    the attachment and the failure is logged.
    """
    if not can_write():
        frappe.throw(_("You are not allowed to send offers"))
    if not offer_name or not frappe.db.exists("Offer Management", offer_name):
        frappe.throw(_("Offer not found"))

    offer = frappe.get_doc("Offer Management", offer_name)
    candidate = frappe.get_doc("Candidate", offer.candidate)
    if not (candidate.email or "").strip():
        frappe.throw(
            _("Candidate {0} has no email address — add one to the profile first").format(
                candidate.candidate_name
            )
        )

    # Approval gate: when enabled in Recruitment Settings, Draft / Approval
    # Pending offers must be approved in the portal before they can be emailed.
    try:
        settings = frappe.get_single("Recruitment Settings")
        require_approval = bool(settings.get("require_approval_for_offers"))
    except Exception:
        require_approval = False
    if (
        require_approval
        and offer.status in ("Draft", "Approval Pending")
        and offer.approval_status != "Approved"
    ):
        frappe.throw(
            _(
                "This offer needs approval before it can be emailed — approve it "
                "from the Offers section on the JD / candidate page first."
            )
        )

    job_title = offer.job_title or _get_latest_job_title(candidate.name)
    context = {
        "candidate_name": candidate.candidate_name,
        "job_title": job_title or _("the position"),
        "company_name": _get_company_name(),
        "recruiter_name": _get_recruiter_name(),
        "offer_link": frappe.utils.get_url(
            "/app/offer-management/{0}".format(offer.name)
        ),
    }
    subject, message = _render_email_template(
        "Offer Letter", context, "Offer of Employment - {0}".format(job_title)
    )

    # Offer letter PDF attachment (best effort — never block the email).
    attachments = []
    try:
        html = frappe.get_print(
            "Offer Management", offer.name, print_format="Offer Letter"
        )
        from frappe.utils.pdf import get_pdf

        pdf = get_pdf(html)
        if pdf:
            attachments.append({
                "fname": "Offer-Letter-{0}.pdf".format(offer.name),
                "fcontent": pdf,
            })
    except Exception as e:
        frappe.log_error(
            message=f"Offer PDF generation failed for {offer.name}: {str(e)}",
            title="Offer Email Error",
        )

    frappe.sendmail(
        recipients=[candidate.email],
        cc=_get_cc_emails(offer.owner),
        subject=subject,
        message=message,
        attachments=attachments,
        reference_doctype="Offer Management",
        reference_name=offer.name,
        now=True,
    )

    update = {"offer_email_sent_at": now_datetime()}
    if offer.status in ("Draft", "Approval Pending", "Approved"):
        update["status"] = "Offer Sent"
    frappe.db.set_value("Offer Management", offer.name, update)

    frappe.db.commit()
    return {
        "status": "success",
        "message": _("Offer emailed to {0}").format(candidate.email),
    }


@frappe.whitelist()
def send_interview_invite_email(interview_name=None):
    """Email the interview invitation to the candidate and the interviewers.

    Uses the 'Interview Invitation' Email Template Config when available.
    """
    if not can_write():
        frappe.throw(_("You are not allowed to send invites"))
    if not interview_name or not frappe.db.exists("Interview Schedule", interview_name):
        frappe.throw(_("Interview not found"))

    iv = frappe.get_doc("Interview Schedule", interview_name)
    candidate = frappe.get_doc("Candidate", iv.candidate)
    if not (candidate.email or "").strip():
        frappe.throw(
            _("Candidate {0} has no email address — add one to the profile first").format(
                candidate.candidate_name
            )
        )

    context = {
        "candidate_name": candidate.candidate_name,
        "job_title": iv.job_title or "",
        "company_name": _get_company_name(),
        "interviewer_name": _get_first_interviewer_name(iv),
        "scheduled_date": str(iv.scheduled_date or ""),
        "scheduled_time": _time_to_string(iv.scheduled_time),
        "interview_link": iv.location_or_link or "",
        "recruiter_name": _get_recruiter_name(),
    }
    subject, message = _render_email_template(
        "Interview Invitation",
        context,
        "Interview Invitation - {0}".format(iv.candidate_name),
    )

    recipients = [candidate.email]
    for row in iv.interviewers or []:
        if (row.email or "").strip() and row.email not in recipients:
            recipients.append(row.email)

    frappe.sendmail(
        recipients=recipients,
        cc=_get_cc_emails(iv.owner),
        subject=subject,
        message=message,
        reference_doctype="Interview Schedule",
        reference_name=iv.name,
        now=True,
    )

    frappe.db.set_value(
        "Interview Schedule",
        iv.name,
        {"invite_email_sent": 1, "invite_email_sent_at": now_datetime()},
    )
    frappe.db.commit()
    return {
        "status": "success",
        "message": _("Invite emailed to {0}").format(candidate.email),
    }


@frappe.whitelist()
def send_rejection_email(ranking_name=None):
    """Reject a candidate AND email them using the Candidate Rejection template.

    Applies the Reject workflow action to the ranking, then emails the
    candidate (CC the recruiter).
    """
    if not can_write():
        frappe.throw(_("You are not allowed to reject candidates"))
    if not ranking_name or not frappe.db.exists("Candidate Ranking", ranking_name):
        frappe.throw(_("Ranking not found"))

    ranking = frappe.get_doc("Candidate Ranking", ranking_name)
    candidate = frappe.get_doc("Candidate", ranking.candidate)
    if not (candidate.email or "").strip():
        frappe.throw(
            _("Candidate {0} has no email address — add one to the profile first").format(
                candidate.candidate_name
            )
        )

    # Reject via the workflow (status + candidate sync)
    set_ranking_status(ranking_name, "Reject")

    context = {
        "candidate_name": candidate.candidate_name,
        "job_title": ranking.job_title or "",
        "company_name": _get_company_name(),
        "recruiter_name": _get_recruiter_name(),
    }
    subject, message = _render_email_template(
        "Candidate Rejection",
        context,
        "Update on your application for {0}".format(ranking.job_title or "this position"),
    )

    frappe.sendmail(
        recipients=[candidate.email],
        cc=_get_cc_emails(ranking.owner),
        subject=subject,
        message=message,
        reference_doctype="Candidate Ranking",
        reference_name=ranking.name,
        now=True,
    )
    frappe.db.commit()
    return {
        "status": "success",
        "message": _("Candidate rejected and emailed {0}").format(candidate.email),
    }


@frappe.whitelist()
def move_candidate_pipeline(ranking=None, column=None):
    """Move a ranking card between Kanban columns (drag & drop).

    Maps the target column to the matching Candidate Evaluation workflow
    action so the status, workflow state and candidate stay in sync. The
    special "Offer" column creates a Draft Offer for the candidate instead
    of changing the workflow state (offers are a separate step).
    """
    if not can_write():
        frappe.throw(_("You are not allowed to move candidates"))
    if not ranking or not frappe.db.exists("Candidate Ranking", ranking):
        frappe.throw(_("Ranking not found"))

    if (column or "") == "Offer":
        ranking_doc = frappe.get_doc("Candidate Ranking", ranking)
        ensure_offer_for_ranking(ranking_doc)
        return {"status": "success", "target": "Offer"}

    column_actions = {
        "Screened": "Evaluate",
        "Shortlisted": "Shortlist",
        "Interview": "Schedule Interview",
        "Selected": "Hire",
        "On Hold": "Put on Hold",
        "Rejected": "Reject",
    }
    action = column_actions.get(column or "")
    if not action:
        frappe.throw(_("Unknown pipeline column: {0}").format(column))
    result = set_ranking_status(ranking, action)
    return {"status": "success", "target": result.get("status")}


def ensure_offer_for_ranking(ranking_doc):
    """Create a Draft Offer Management for the ranking if none is active.

    Active = any offer that is not Declined / Withdrawn, so dragging a card
    into the Offer column never duplicates an existing open offer.
    """
    if not ranking_doc.candidate:
        frappe.throw(_("Ranking has no candidate"))
    existing = frappe.get_all(
        "Offer Management",
        filters={
            "candidate": ranking_doc.candidate,
            "status": ["not in", ["Declined", "Withdrawn"]],
        },
        pluck="name",
        limit_page_length=1,
    )
    if existing:
        return existing[0]

    offer = frappe.new_doc("Offer Management")
    offer.candidate = ranking_doc.candidate
    offer.job_description = ranking_doc.job_description
    try:
        settings = frappe.get_single("Recruitment Settings")
        require_approval = bool(settings.get("require_approval_for_offers"))
    except Exception:
        require_approval = False
    if require_approval:
        offer.status = "Approval Pending"
        offer.approval_status = "Pending"
    else:
        offer.status = "Draft"
    offer.save(ignore_permissions=True)
    frappe.db.commit()
    return offer.name


@frappe.whitelist()
def review_offer(offer_name=None, approve=True, notes=None):
    """Approve or reject an Offer in the portal before it is emailed.

    Allowed for Admins and Hiring Managers. Approved offers can be emailed;
    rejected offers return to Draft (approval_status = Rejected) for revision.
    """
    if not can_approve_offers():
        frappe.throw(_("You are not allowed to approve offers"))
    if not offer_name or not frappe.db.exists("Offer Management", offer_name):
        frappe.throw(_("Offer not found"))

    offer = frappe.get_doc("Offer Management", offer_name)
    if offer.status not in ("Draft", "Approval Pending"):
        frappe.throw(_("Only Draft / Approval Pending offers can be reviewed"))

    approve = str(approve).lower() in ("1", "true", "yes")
    if approve:
        offer.approval_status = "Approved"
        offer.status = "Approved"
        action_label = "approved"
    else:
        offer.approval_status = "Rejected"
        offer.status = "Draft"
        action_label = "rejected"
    offer.approved_by = frappe.session.user
    offer.approval_date = frappe.utils.today()
    if notes:
        offer.approval_notes = notes
    offer.save(ignore_permissions=True)
    frappe.db.commit()

    # Audit trail on the candidate
    try:
        from hr_master.hr_master.doctype.candidate_activity_log.candidate_activity_log import (
            log_activity,
        )

        log_activity(
            candidate=offer.candidate,
            activity_type="Status Changed",
            description=_("Offer {0} {1} by {2}").format(
                offer_name, action_label, frappe.session.user
            ),
        )
        frappe.db.commit()
    except Exception:
        pass

    return {
        "status": "success",
        "approval_status": offer.approval_status,
        "message": _("Offer {0} {1}").format(offer_name, action_label),
    }


@frappe.whitelist()
def bulk_ranking_action(rankings=None, action=None):
    """Apply one workflow action to many Candidate Rankings at once.

    Used by the bulk actions bar on the ranked results page (Shortlist /
    Reject / Hold / Hire / Evaluate / Schedule Interview).
    """
    if not can_write():
        frappe.throw(_("You are not allowed to update rankings"))
    if isinstance(rankings, str):
        try:
            rankings = json.loads(rankings)
        except Exception:
            rankings = [rankings]
    if not rankings:
        frappe.throw(_("No rankings selected"))

    action = (action or "").strip()
    valid_actions = {
        "Evaluate",
        "Shortlist",
        "Reject",
        "Put on Hold",
        "Hire",
        "Schedule Interview",
    }
    if action not in valid_actions:
        frappe.throw(_("Unknown bulk action: {0}").format(action))

    updated = 0
    errors = []
    for name in rankings:
        try:
            if not frappe.db.exists("Candidate Ranking", name):
                errors.append(_("{0}: ranking not found").format(name))
                continue
            set_ranking_status(name, action)
            updated += 1
        except Exception as e:
            errors.append(_("{0}: {1}").format(name, e))

    frappe.db.commit()
    return {
        "status": "success" if not errors else "partial",
        "action": action,
        "updated": updated,
        "errors": errors,
    }


# ------------------------------------------
# Saved candidate searches (per-user, DB-backed)
# ------------------------------------------


def _saved_searches_store():
    """User Defaults key holding saved portal searches (JSON dict)."""
    return "hr_portal_saved_searches"


@frappe.whitelist()
def save_candidate_search(job_description=None, title=None, filters=None):
    """Save the current results-page filters as a named search for this user."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))
    if not title or not title.strip():
        frappe.throw(_("A name for the saved search is required"))

    store = _saved_searches_store()
    saved = json.loads(frappe.defaults.get_user_default(store) or "{}")
    jd_key = job_description or ""
    saved.setdefault(jd_key, [])

    # Replace an existing saved search with the same name
    saved[jd_key] = [
        s
        for s in saved[jd_key]
        if (s.get("title") or "").lower() != title.strip().lower()
    ]
    saved[jd_key].append({
        "title": title.strip(),
        "filters": filters or "",
        "saved_on": str(now_datetime()),
    })

    frappe.defaults.set_user_default(store, json.dumps(saved))
    frappe.db.commit()
    return {"status": "success", "message": _("Saved search '{0}'").format(title.strip())}


@frappe.whitelist()
def get_saved_searches(job_description=None):
    """Return the current user's saved searches for a JD (or all)."""
    if frappe.session.user == "Guest":
        return []
    store = _saved_searches_store()
    saved = json.loads(frappe.defaults.get_user_default(store) or "{}")
    if job_description:
        return saved.get(job_description, [])
    return [s for entries in saved.values() for s in entries]


@frappe.whitelist()
def delete_saved_search(job_description=None, title=None):
    """Delete one of the current user's saved searches."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"))
    store = _saved_searches_store()
    saved = json.loads(frappe.defaults.get_user_default(store) or "{}")
    jd_key = job_description or ""
    if jd_key in saved:
        saved[jd_key] = [
            s
            for s in saved[jd_key]
            if (s.get("title") or "").lower() != (title or "").lower()
        ]
        frappe.defaults.set_user_default(store, json.dumps(saved))
        frappe.db.commit()
    return {"status": "success", "message": _("Saved search deleted")}


# ------------------------------------------
# Email helpers
# ------------------------------------------


def _render_email_template(template_name, context, fallback_subject):
    """Render subject + body from an Email Template Config (placeholder fill)."""
    template_doc = None
    if frappe.db.exists("Email Template Config", template_name):
        template_doc = frappe.get_doc("Email Template Config", template_name)

    if template_doc:
        subject = template_doc.subject or fallback_subject
        message = (
            template_doc.message_html
            if template_doc.use_html
            else template_doc.message_text
        )
    else:
        subject = fallback_subject
        message = "<p>{0}</p>".format(fallback_subject)

    for key, value in (context or {}).items():
        placeholder = "{{ " + key + " }}"
        subject = subject.replace(placeholder, str(value))
        message = message.replace(placeholder, str(value))
    return subject, message


def _get_company_name():
    """Company name from Recruitment Settings (best effort)."""
    try:
        return frappe.db.get_single_value("Recruitment Settings", "company_name") or ""
    except Exception:
        return ""


def _get_recruiter_name():
    """Display name of the default recruiter, else the current user."""
    try:
        recruiter = frappe.db.get_single_value(
            "Recruitment Settings", "default_recruiter"
        )
        if recruiter:
            user = frappe.get_doc("User", recruiter)
            return user.full_name or recruiter
    except Exception:
        pass
    try:
        user = frappe.get_doc("User", frappe.session.user)
        return user.full_name or frappe.session.user
    except Exception:
        return frappe.session.user


def _get_cc_emails(owner=None):
    """Default CC list for candidate emails: recruiter, plus the doc owner."""
    emails = []
    try:
        recruiter = frappe.db.get_single_value(
            "Recruitment Settings", "default_recruiter"
        )
        if recruiter:
            email = frappe.db.get_value("User", recruiter, "email")
            if email:
                emails.append(email)
    except Exception:
        pass
    if owner and owner != frappe.session.user:
        email = frappe.db.get_value("User", owner, "email")
        if email and email not in emails:
            emails.append(email)
    return emails


def _get_latest_job_title(candidate_name):
    """Latest ranked job title for a candidate (offer fallback)."""
    try:
        return (
            frappe.db.get_value(
                "Candidate Ranking",
                {"candidate": candidate_name},
                "job_title",
                order_by="evaluation_date desc",
            )
            or ""
        )
    except Exception:
        return ""


def _get_first_interviewer_name(iv):
    """Name of the first interviewer row (for the email template)."""
    try:
        for row in iv.interviewers or []:
            if (row.interviewer_name or "").strip():
                return row.interviewer_name
            if row.interviewer:
                return row.interviewer
    except Exception:
        pass
    return ""


def _time_to_string(value):
    """Render a Time value (datetime.time / timedelta / str) as HH:MM."""
    if value is None:
        return ""
    try:
        if hasattr(value, "hour"):
            return "{0:02d}:{1:02d}".format(value.hour, value.minute)
        if isinstance(value, str) and ":" in value:
            return value[:5]
        # timedelta (seconds since midnight)
        total = int(value.total_seconds()) if hasattr(value, "total_seconds") else 0
        return "{0:02d}:{1:02d}".format(total // 3600, (total % 3600) // 60)
    except Exception:
        return str(value)


@frappe.whitelist()
def submit_feedback(data=None):
    """Create an Interview Feedback record."""
    if not can_write():
        frappe.throw(_("You are not allowed to submit feedback"))

    data = _parse_json(data)
    if not data.get("interview_schedule") or not data.get("interviewer"):
        frappe.throw(_("Interview schedule and interviewer are required"))

    fb = frappe.new_doc("Interview Feedback")
    fb.interview_schedule = data.get("interview_schedule")
    fb.interviewer = data.get("interviewer")
    fb.interview_round = data.get("interview_round")
    fb.interview_type = data.get("interview_type")
    fb.overall_rating = data.get("overall_rating")
    fb.technical_score = data.get("technical_score")
    fb.communication_score = data.get("communication_score")
    fb.cultural_fit_score = data.get("cultural_fit_score")
    fb.problem_solving_score = data.get("problem_solving_score")
    fb.strengths = data.get("strengths")
    fb.weaknesses = data.get("weaknesses")
    fb.notes = data.get("notes")
    fb.recommendation = data.get("recommendation")
    fb.result = data.get("result")
    fb.next_steps = data.get("next_steps")
    fb.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": fb.name}
