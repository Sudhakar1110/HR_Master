"""AI endpoints for HR Master — JD skill suggestions & interview questions.

Whitelisted so the HR portal can call them via fetch. When AI is configured
in Recruitment Settings these use the LLM; when it is not (or the LLM call
fails) they fall back to rule-based suggestions built from the JD itself, so
the portal buttons never error out with a 417/500.
"""

from __future__ import unicode_literals

import frappe
from frappe import _

from hr_master.api.portal_actions import has_hr_role
from hr_master.utils.llm import call_llm_json, is_llm_configured


def _guard():
    """Ensure the caller is an HR user."""
    if frappe.session.user == "Guest" or not has_hr_role():
        frappe.throw(_("Not permitted"))


def _get_jd(job_description_name):
    if not job_description_name or not frappe.db.exists("Job Description", job_description_name):
        frappe.throw(_("Job Description not found"))
    return frappe.get_doc("Job Description", job_description_name)


def _suggest_skills_rule_based(jd):
    """Rule-based skill suggestions used when the LLM is not available.

    Combines the skills already on the JD, related skills from the same
    category, and skills extracted from the description text.
    """
    from hr_master.hr_master.doctype.skill.skill import extract_skills_from_text

    required = list(dict.fromkeys(jd.get_required_skills_list()))
    preferred = list(dict.fromkeys(jd.get_preferred_skills_list()))
    existing = set(required + preferred)

    # Related skills in the same category as skills already on the JD
    for skill_name in list(existing)[:6]:
        if not frappe.db.exists("Skill", skill_name):
            continue
        skill = frappe.get_doc("Skill", skill_name)
        if not skill.category:
            continue
        related = frappe.get_all(
            "Skill",
            filters={
                "category": skill.category,
                "name": ["not in", list(existing)],
                "is_active": 1,
            },
            pluck="name",
            limit=3,
        )
        for related_name in related:
            if related_name not in existing:
                preferred.append(related_name)
                existing.add(related_name)

    # JD has no skills yet — extract them straight from the description
    if not required and not preferred:
        raw = frappe.utils.strip_html_tags(jd.job_description_raw or "")
        for skill in extract_skills_from_text(raw):
            if skill not in existing:
                required.append(skill)
                existing.add(skill)
            if len(required) >= 10:
                break

    return required[:10], preferred[:6]


def _questions_rule_based(jd, count):
    """Template-based interview questions generated from the JD's skills."""
    technical = []
    for skill in list(dict.fromkeys(jd.get_required_skills_list())):
        technical.append(
            "Describe a project where you applied {0} — what was your role and the outcome?".format(skill)
        )
        technical.append(
            "How do you stay current with {0}? Share a recent example of using it.".format(skill)
        )
        if len(technical) >= count:
            break

    general_technical = [
        "Walk me through the most challenging production issue you have solved and how you debugged it.",
        "How do you approach code quality, testing, and code reviews?",
        "How do you handle disagreements about technical direction?",
        "Describe how you would design a feature end-to-end, from requirements to release.",
    ]
    for question in general_technical:
        if len(technical) >= max(count, 2):
            break
        technical.append(question)

    behavioral = [
        "Tell me about a time you disagreed with a teammate or manager — how did you resolve it?",
        "Describe a situation where you had to deliver under a tight deadline with limited resources.",
        "Give an example of a failure you learned from, and what you changed afterwards.",
        "How do you prioritize when several tasks are equally urgent?",
        "Describe a time you helped a colleague grow or improve.",
    ]

    company = frappe.db.get_single_value("Recruitment Settings", "company_name") or ""
    role_title = jd.job_title or jd.name
    role_specific = [
        "Why are you interested in the {0} role at {1}?".format(role_title, company or "our company"),
        "What would your first 90 days look like if you joined as {0}?".format(role_title),
        "Which of the required skills for this role do you consider your strongest, and why?",
        "What questions do you have about the team or the role?",
    ]

    return {
        "technical": technical[:6],
        "behavioral": behavioral[:4],
        "role_specific": role_specific[:4],
    }


@frappe.whitelist()
def suggest_jd_skills(job_description_name=None):
    """Ask the LLM to propose Required / Preferred skills for a JD.

    Falls back to rule-based suggestions when AI is not configured.
    """
    _guard()
    jd = _get_jd(job_description_name)

    if is_llm_configured():
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
        if data.get("required") or data.get("preferred"):
            return {
                "status": "success",
                "required": [s for s in (data.get("required") or []) if s][:10],
                "preferred": [s for s in (data.get("preferred") or []) if s][:6],
            }

    required, preferred = _suggest_skills_rule_based(jd)
    return {"status": "success", "required": required, "preferred": preferred}


@frappe.whitelist()
def generate_interview_questions(job_description_name=None, count=6):
    """Ask the LLM to generate tailored interview questions for a JD.

    Falls back to template questions built from the JD's skills when AI is
    not configured.
    """
    _guard()
    jd = _get_jd(job_description_name)

    try:
        count = max(1, min(int(count or 6), 12))
    except (TypeError, ValueError):
        count = 6

    if is_llm_configured():
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
        if data.get("technical") or data.get("behavioral") or data.get("role_specific"):
            return {
                "status": "success",
                "questions": {
                    "technical": [q for q in (data.get("technical") or []) if q][:6],
                    "behavioral": [q for q in (data.get("behavioral") or []) if q][:4],
                    "role_specific": [q for q in (data.get("role_specific") or []) if q][:4],
                },
            }

    questions = _questions_rule_based(jd, count)
    return {"status": "success", "questions": questions}
