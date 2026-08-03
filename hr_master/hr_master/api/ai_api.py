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
from hr_master.utils.llm import call_llm, call_llm_json, is_llm_configured


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


def _summary_rule_based(jd):
    """Build a concise job-posting summary from the JD fields."""
    title = jd.job_title or jd.name
    company = frappe.db.get_single_value("Recruitment Settings", "company_name") or ""
    location = jd.location or "Remote"
    employment = jd.employment_type or "Full-Time"

    lines = [
        "We are hiring a {0} ({1}) to join our team{2} in {3}.".format(
            title,
            employment,
            (" at " + company) if company else "",
            location,
        )
    ]

    if jd.min_experience_years or jd.max_experience_years:
        low = jd.min_experience_years or 0
        high = jd.max_experience_years or "more"
        lines.append("Ideal candidates bring {0}–{1} years of experience.".format(low, high))

    skills = jd.get_required_skills_list()
    if skills:
        lines.append("Key skills: {0}.".format(", ".join(skills[:8])))

    raw = frappe.utils.strip_html_tags(jd.job_description_raw or "")
    if raw:
        sentences = [s.strip() for s in raw.replace("\n", " ").split(". ") if s.strip()]
        if sentences:
            lines.append(" ".join(sentences[:2]))

    return "\n\n".join(lines)


def _screening_questions_rule_based(jd, count):
    """Template phone-screen questions built from the JD."""
    title = jd.job_title or jd.name
    location = jd.location or "Remote"
    employment = jd.employment_type or "Full-Time"

    phone_screen = [
        "Walk me through your resume — what are the highlights of your experience so far?",
        "Why are you interested in the {0} role, and what do you know about our company?".format(title),
        "What is your current notice period, and what are your compensation expectations?",
        "Are you comfortable working {0} from {1}?".format(employment, location),
        "Where do you see yourself professionally in the next couple of years?",
    ]

    skill_deep_dive = [
        "Describe a project where you applied {0} — what was your role and the outcome?".format(s)
        for s in jd.get_required_skills_list()[:count]
    ]
    if not skill_deep_dive:
        skill_deep_dive = ["Which skills from the job description are you strongest in, and why?"]

    return {
        "Phone Screen": phone_screen[:count],
        "Skill Deep-Dive": skill_deep_dive[:count],
    }


def _search_keywords_rule_based(jd):
    """Build portal search keywords from the JD (title + skills + location)."""
    keywords = [jd.job_title or jd.name]
    keywords.extend(jd.get_required_skills_list()[:8])
    if jd.location:
        keywords.append(jd.location)

    seen = set()
    result = []
    for kw in keywords:
        key = kw.strip().lower()
        if kw.strip() and key not in seen:
            seen.add(key)
            result.append(kw.strip())
    return result[:12]


def _salary_rule_based(jd):
    """Salary guidance built from the JD."""
    title = jd.job_title or jd.name
    location = jd.location or "your region"
    low = jd.salary_range_min
    high = jd.salary_range_max
    if low or high:
        if low and high:
            return (
                "The JD currently lists a range of {0} – {1}. Validate this against market "
                "benchmarks for {2} roles in {3} before publishing the opening.".format(
                    low, high, title, location
                )
            )
        return (
            "The JD lists only {0}. Add an upper bound so candidates have a clear "
            "expectation.".format(low or high)
        )
    return (
        "No salary range is set on this JD. Benchmark {0} roles in {1} and set a range to "
        "attract quality applicants.".format(title, location)
    )


@frappe.whitelist()
def suggest_jd_summary(job_description_name=None):
    """Ask the LLM for a concise job-posting summary; fall back to a template."""
    _guard()
    jd = _get_jd(job_description_name)

    if is_llm_configured():
        system = "You are a recruiter writing a compelling job posting. Reply with plain text only, no markdown."
        prompt = (
            "Write a concise, engaging job posting summary (5-7 sentences) for this role. "
            "Mention the role, key responsibilities, must-have skills, and what makes it attractive.\n\n"
            "Job title: {0}\nCompany: {1}\nLocation: {2}\nEmployment type: {3}\n"
            "Experience: {4}\nDescription:\n{5}\n\nReply with the summary text only."
        ).format(
            jd.job_title or jd.name,
            frappe.db.get_single_value("Recruitment Settings", "company_name") or "our company",
            jd.location or "Remote",
            jd.employment_type or "Full-Time",
            "{0}-{1} years".format(
                jd.min_experience_years or 0, jd.max_experience_years or "more"
            ),
            (jd.job_description_raw or "")[:4000] or "No description provided.",
        )
        text = call_llm(prompt, system=system, max_tokens=400, temperature=0.4).strip()
        if text:
            return {"status": "success", "text": text}

    return {"status": "success", "text": _summary_rule_based(jd)}


@frappe.whitelist()
def suggest_screening_questions(job_description_name=None, count=5):
    """Ask the LLM for phone-screen questions; fall back to a template."""
    _guard()
    jd = _get_jd(job_description_name)

    try:
        count = max(1, min(int(count or 5), 8))
    except (TypeError, ValueError):
        count = 5

    if is_llm_configured():
        system = "You are a recruiter running phone screens. Reply with JSON only, no prose."
        prompt = (
            "Write {0} phone-screen interview questions for this role. Return a JSON object with two arrays:\n"
            '- "phone_screen": introductory / logistics questions\n'
            '- "skill_deep_dive": questions probing the required skills\n\n'
            "Job title: {1}\nRequired skills: {2}\nDescription:\n{3}\n\n"
            "Reply only with: {{\"phone_screen\": [...], \"skill_deep_dive\": [...]}}"
        ).format(
            count,
            jd.job_title or jd.name,
            ", ".join(jd.get_required_skills_list())[:500] or "n/a",
            (jd.job_description_raw or "")[:4000] or "No description provided.",
        )
        data = call_llm_json(prompt, system=system, max_tokens=600, temperature=0.3)
        if data.get("phone_screen") or data.get("skill_deep_dive"):
            return {
                "status": "success",
                "questions": {
                    "Phone Screen": [q for q in (data.get("phone_screen") or []) if q][:count],
                    "Skill Deep-Dive": [q for q in (data.get("skill_deep_dive") or []) if q][:count],
                },
            }

    return {"status": "success", "questions": _screening_questions_rule_based(jd, count)}


@frappe.whitelist()
def suggest_search_keywords(job_description_name=None):
    """Ask the LLM for portal search keywords; fall back to JD-derived terms."""
    _guard()
    jd = _get_jd(job_description_name)

    if is_llm_configured():
        system = "You are a sourcing specialist. Reply with JSON only, no prose."
        prompt = (
            "Suggest 10-12 search keywords for a job-portal candidate search for this role. "
            "Return a JSON object with one array:\n- \"keywords\": concise search terms (role, skills, variants)\n\n"
            "Job title: {0}\nRequired skills: {1}\nLocation: {2}\n\n"
            "Reply only with: {{\"keywords\": [...]}}"
        ).format(
            jd.job_title or jd.name,
            ", ".join(jd.get_required_skills_list())[:500] or "n/a",
            jd.location or "Remote",
        )
        data = call_llm_json(prompt, system=system, max_tokens=300, temperature=0.3)
        if data.get("keywords"):
            return {
                "status": "success",
                "keywords": [k for k in (data.get("keywords") or []) if k][:12],
            }

    return {"status": "success", "keywords": _search_keywords_rule_based(jd)}


@frappe.whitelist()
def suggest_salary_range(job_description_name=None):
    """Ask the LLM for a salary benchmark; fall back to JD-based guidance."""
    _guard()
    jd = _get_jd(job_description_name)

    if is_llm_configured():
        system = "You are a compensation analyst. Reply with plain text only, no markdown."
        prompt = (
            "Give a practical salary benchmark (a range plus 1-2 sentences of rationale) for a "
            "{0} role requiring {1} years of experience in {2}. Reply with the benchmark text only."
        ).format(
            jd.job_title or jd.name,
            "{0}-{1}".format(jd.min_experience_years or 0, jd.max_experience_years or "more"),
            jd.location or "Remote",
        )
        text = call_llm(prompt, system=system, max_tokens=250, temperature=0.3).strip()
        if text:
            return {"status": "success", "text": text}

    return {"status": "success", "text": _salary_rule_based(jd)}
