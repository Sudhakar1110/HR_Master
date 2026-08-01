"""AI endpoints for HR Master — JD skill suggestions & interview questions.

Whitelisted so the HR portal can call them via fetch. They rely on the
AI configuration in Recruitment Settings; when AI is disabled they return
a helpful error so the UI can prompt the user to enable it.
"""

from __future__ import unicode_literals

import frappe
from frappe import _

from hr_master.api.portal_actions import has_hr_role
from hr_master.utils.llm import call_llm_json, is_llm_configured


def _guard():
    """Ensure the caller is an HR user and AI is configured."""
    if frappe.session.user == "Guest" or not has_hr_role():
        frappe.throw(_("Not permitted"))
    if not is_llm_configured():
        frappe.throw(
            _("AI is not configured. Enable it in Desk → HR Master → Recruitment Settings → AI Configuration.")
        )


def _get_jd(job_description_name):
    if not job_description_name or not frappe.db.exists("Job Description", job_description_name):
        frappe.throw(_("Job Description not found"))
    return frappe.get_doc("Job Description", job_description_name)


@frappe.whitelist()
def suggest_jd_skills(job_description_name=None):
    """Ask the LLM to propose Required / Preferred skills for a JD."""
    _guard()
    jd = _get_jd(job_description_name)

    system = (
        "You are a senior technical recruiter. From a job description, list the skills a "
        "candidate would need. Reply with JSON only, no prose."
    )
    prompt = (
        "Read this job description and return a JSON object with two arrays:\n"
        '- "required": 6-10 must-have skills (hard requirements)\n'
        '- "preferred": 4-6 nice-to-have skills\n\n'
        "Job title: {0}\nDescription:\n{1}\n\n"
        "Reply only with: {{\"required\": [...], \"preferred\": [...]}}"
    ).format(
        jd.job_title or jd.name,
        (jd.job_description_raw or "")[:6000] or "No description provided.",
    )
    data = call_llm_json(prompt, system=system, max_tokens=700, temperature=0.2)

    return {
        "status": "success",
        "required": [s for s in (data.get("required") or []) if s][:10],
        "preferred": [s for s in (data.get("preferred") or []) if s][:6],
    }


@frappe.whitelist()
def generate_interview_questions(job_description_name=None, count=6):
    """Ask the LLM to generate tailored interview questions for a JD."""
    _guard()
    jd = _get_jd(job_description_name)

    try:
        count = max(1, min(int(count or 6), 12))
    except (TypeError, ValueError):
        count = 6

    system = (
        "You are an expert interviewer. Write specific, non-generic interview questions "
        "tailored to the role and its required skills. Reply with JSON only, no prose."
    )
    prompt = (
        "Write {0} interview questions for this role. Return a JSON object with three arrays:\n"
        '- "technical": role/skill-specific technical questions\n'
        '- "behavioral": behavioral / situational questions\n'
        '- "role_specific": questions about this exact job\n\n'
        "Job title: {1}\nRequired skills: {2}\nDescription:\n{3}\n\n"
        "Reply only with: {{\"technical\": [...], \"behavioral\": [...], \"role_specific\": [...]}}"
    ).format(
        count,
        jd.job_title or jd.name,
        ", ".join(jd.get_required_skills_list())[:500] or "n/a",
        (jd.job_description_raw or "")[:5000] or "No description provided.",
    )
    data = call_llm_json(prompt, system=system, max_tokens=1100, temperature=0.3)

    return {
        "status": "success",
        "questions": {
            "technical": [q for q in (data.get("technical") or []) if q][:6],
            "behavioral": [q for q in (data.get("behavioral") or []) if q][:4],
            "role_specific": [q for q in (data.get("role_specific") or []) if q][:4],
        },
    }
