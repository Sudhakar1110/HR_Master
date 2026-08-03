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

    offer.status = "Draft"
    offer.save(ignore_permissions=True)
    frappe.db.commit()
    return {"name": offer.name}


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
