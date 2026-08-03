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


# ------------------------------------------
# Chat-style AI assistant (type a question → get an answer)
# ------------------------------------------


def _jd_context_for_prompt(jd):
    """Compact JD summary used as context for the chat assistant."""
    lines = [
        "Job title: {0}".format(jd.job_title or jd.name),
        "Location: {0}".format(jd.location or "Remote"),
        "Employment type: {0}".format(jd.employment_type or "Full-Time"),
        "Experience required: {0}-{1} years".format(
            jd.min_experience_years or 0, jd.max_experience_years or "more"
        ),
    ]
    if jd.salary_range_min or jd.salary_range_max:
        lines.append(
            "Salary range: {0} - {1}".format(
                jd.salary_range_min or "?", jd.salary_range_max or "?"
            )
        )
    required = jd.get_required_skills_list()
    preferred = jd.get_preferred_skills_list()
    if required:
        lines.append("Required skills: {0}".format(", ".join(required[:12])))
    if preferred:
        lines.append("Preferred skills: {0}".format(", ".join(preferred[:12])))
    raw = frappe.utils.strip_html_tags(jd.job_description_raw or "")
    if raw:
        lines.append("Description: {0}".format(raw[:2500]))
    return "\n".join(lines)


def _chat_rule_based(jd, message):
    """Rule-based chat reply used when the LLM is unavailable.

    Routes the user's question to the matching JD tool (screening, questions,
    skills, keywords, salary, summary); anything else gets a JD digest plus
    guidance.
    """
    import re

    msg = " ".join(message.lower().split())

    def bullet(items):
        return "\n".join("- {0}".format(i) for i in items)

    def has_word(word):
        # Word-boundary match so "pay" doesn't match "payment" and "search"
        # doesn't match "research".
        return bool(re.search(r"\b{0}\b".format(re.escape(word)), msg))

    if "screen" in msg:
        q = _screening_questions_rule_based(jd, 5)
        parts = []
        for label, items in q.items():
            if items:
                parts.append("{0}:\n{1}".format(label, bullet(items)))
        return "\n\n".join(parts) or "No screening questions yet — add skills to this JD first."

    if "interview" in msg or "question" in msg:
        q = _questions_rule_based(jd, 6)
        parts = []
        for label, items in (
            ("Technical", q["technical"]),
            ("Behavioral", q["behavioral"]),
            ("Role-specific", q["role_specific"]),
        ):
            if items:
                parts.append("{0}:\n{1}".format(label, bullet(items)))
        return "\n\n".join(parts) or "No interview questions yet — add skills to this JD first."

    if "skill" in msg:
        required, preferred = _suggest_skills_rule_based(jd)
        parts = []
        if required:
            parts.append("Required skills:\n{0}".format(bullet(required)))
        if preferred:
            parts.append("Preferred skills:\n{0}".format(bullet(preferred)))
        return "\n\n".join(parts) or "No skills found — add skills to this JD first."

    if "keyword" in msg or has_word("search"):
        return "Search keywords:\n{0}".format(bullet(_search_keywords_rule_based(jd)))

    if "salary" in msg or "compensation" in msg or has_word("pay"):
        return _salary_rule_based(jd)

    if any(k in msg for k in ("summar", "overview", "describe", "about this job")):
        return _summary_rule_based(jd)

    # Generic fallback: JD digest + guidance
    return (
        "Here's a quick overview of this job:\n\n{0}\n\n"
        "I can also draft interview questions, screening questions, skill "
        "suggestions, search keywords or a salary benchmark — just ask. For "
        "fully AI-generated answers to any question, enable an AI provider in "
        "Desk → Recruitment Settings → AI Configuration."
    ).format(_summary_rule_based(jd))


@frappe.whitelist()
def ask_ai(job_description_name=None, message=None):
    """Chat-style AI assistant for a JD (free-form questions).

    Uses the configured LLM when available; falls back to a rule-based reply
    so the chat box always answers and never 417s/errors.
    """
    _guard()
    jd = _get_jd(job_description_name)
    message = (message or "").strip()
    if not message:
        frappe.throw(_("Message is required"))

    if is_llm_configured():
        system = (
            "You are an expert recruiting assistant embedded in HR Master, a "
            "Frappe/ERPNext app. The user manages the job description shown in "
            "the context. Answer concisely, practically and directly. Use the "
            "job context; if the question is unrelated to recruiting, steer it "
            "back helpfully."
        )
        prompt = (
            "JOB CONTEXT:\n{0}\n\nUSER QUESTION:\n{1}\n\nReply with a helpful, "
            "concise answer."
        ).format(_jd_context_for_prompt(jd), message[:2000])
        text = call_llm(prompt, system=system, max_tokens=600, temperature=0.4).strip()
        if text:
            return {"status": "success", "reply": text}

    return {"status": "success", "reply": _chat_rule_based(jd, message)}


# ------------------------------------------
# Chat assistant for a specific candidate profile
# ------------------------------------------


def _candidate_digest(candidate):
    """Plain-language summary of a candidate profile."""
    lines = [
        "{0} is a {1}{2} with {3} year(s) of experience{4}.".format(
            candidate.candidate_name,
            candidate.current_title or "professional",
            (" at " + candidate.current_company) if candidate.current_company else "",
            candidate.total_experience_years or 0,
            (" from " + candidate.location) if candidate.location else "",
        ),
    ]
    if candidate.highest_education:
        lines.append("Education: {0}.".format(candidate.highest_education))
    skills = candidate.get_skills_with_details()
    if skills:
        lines.append("Key skills: {0}.".format(", ".join(skills)[:300]))
    if candidate.expected_salary:
        lines.append("Salary expectations: {0}.".format(candidate.expected_salary))
    if candidate.notice_period_days:
        lines.append("Notice period: {0} days.".format(candidate.notice_period_days))
    resume = frappe.utils.strip_html_tags(candidate.resume_text or "")
    if resume:
        sentences = [s.strip() for s in resume.replace("\n", " ").split(". ") if s.strip()]
        if sentences:
            lines.append(" ".join(sentences[:2]))
    return "\n".join(lines)


def _candidate_context_for_prompt(candidate):
    """Compact candidate profile used as context for the chat assistant."""
    lines = [
        "Candidate name: {0}".format(candidate.candidate_name or candidate.name),
        "Current title: {0}".format(candidate.current_title or "n/a"),
        "Current company: {0}".format(candidate.current_company or "n/a"),
        "Location: {0}".format(candidate.location or "n/a"),
        "Experience: {0} years".format(candidate.total_experience_years or 0),
        "Education: {0}".format(candidate.highest_education or "n/a"),
        "Status: {0}".format(candidate.status or "n/a"),
        "Source: {0}".format(candidate.source or "n/a"),
        "Notice period: {0} days".format(candidate.notice_period_days or 0),
    ]
    if candidate.current_salary:
        lines.append("Current salary: {0}".format(candidate.current_salary))
    if candidate.expected_salary:
        lines.append("Expected salary: {0}".format(candidate.expected_salary))
    skills = candidate.get_skills_with_details()
    if skills:
        skill_lines = []
        for skill_name, info in skills.items():
            parts = [str(skill_name)]
            if info.get("proficiency"):
                parts.append(info["proficiency"])
            if info.get("years_of_experience"):
                parts.append("{0}y".format(info["years_of_experience"]))
            if info.get("is_primary"):
                parts.append("primary")
            skill_lines.append(", ".join(parts))
        lines.append("Skills: {0}".format("; ".join(skill_lines)[:1200]))
    resume = frappe.utils.strip_html_tags(candidate.resume_text or "")
    if resume:
        lines.append("Resume summary: {0}".format(resume[:2500]))
    return "\n".join(lines)


def _candidate_chat_rule_based(candidate, message):
    """Rule-based chat reply about a candidate when the LLM is unavailable.

    Routes the question to the matching profile analysis (summary, strengths,
    skills, experience, salary, interview questions, fit); anything else gets
    a candidate digest plus guidance.
    """
    import re

    msg = " ".join(message.lower().split())

    def bullet(items):
        return "\n".join("- {0}".format(i) for i in items)

    def has_word(word):
        return bool(re.search(r"\b{0}\b".format(re.escape(word)), msg))

    skills = candidate.get_skills_with_details()

    def fmt_skill(skill_name, info):
        return "{0} ({1}, {2}y)".format(
            skill_name,
            info.get("proficiency") or "n/a",
            info.get("years_of_experience") or 0,
        )

    # Strengths / weaknesses / development areas
    if "strength" in msg or "weakness" in msg or "good at" in msg:
        strong = []
        gaps = []
        for s, i in skills.items():
            prof = (i.get("proficiency") or "").lower()
            years = i.get("years_of_experience") or 0
            if prof in ("expert", "advanced") or years >= 3:
                strong.append(fmt_skill(s, i))
            elif prof == "beginner" or years <= 1:
                gaps.append(fmt_skill(s, i))
        parts = []
        parts.append(
            "Likely strengths:\n{0}".format(bullet(strong))
            if strong
            else "No standout strengths found in the listed skills yet."
        )
        if gaps:
            parts.append("Possible gaps / development areas:\n{0}".format(bullet(gaps)))
        return "\n\n".join(parts)

    # Experience analysis
    if "experience" in msg or "years" in msg:
        exp_lines = [
            "{0} has {1} year(s) of total experience.".format(
                candidate.candidate_name, candidate.total_experience_years or 0
            )
        ]
        if skills:
            by_year = sorted(
                skills.items(),
                key=lambda kv: kv[1].get("years_of_experience") or 0,
                reverse=True,
            )[:5]
            exp_lines.append(
                "Most experienced in:\n{0}".format(
                    bullet(fmt_skill(s, i) for s, i in by_year)
                )
            )
        return "\n".join(exp_lines)

    # Skill list
    if "skill" in msg:
        if not skills:
            return "This candidate has no skills listed yet."
        return "Skills:\n{0}".format(bullet(fmt_skill(s, i) for s, i in skills.items()))

    # Salary expectations
    if "salary" in msg or "compensation" in msg or has_word("pay"):
        parts = []
        if candidate.current_salary:
            parts.append("Current salary: {0}".format(candidate.current_salary))
        if candidate.expected_salary:
            parts.append("Expected salary: {0}".format(candidate.expected_salary))
        if not parts:
            parts.append(
                "No salary expectations recorded for this candidate yet — check "
                "with the recruiter or during the phone screen."
            )
        else:
            parts.append(
                "Use these as a starting point for the offer, benchmarked "
                "against the role's market range."
            )
        return "\n".join(parts)

    # Interview questions tailored to this candidate
    if "interview" in msg or "question" in msg:
        if not skills:
            return (
                "Tailor questions to this candidate's resume: ask them to walk "
                "through their background, their most complex project, and why "
                "they're interested in the role. No skills are listed yet, so "
                "start with their experience."
            )
        qs = []
        for s, i in list(skills.items())[:5]:
            qs.append(
                "Describe a project where you applied {0} — what was your role and the outcome?".format(s)
            )
            if i.get("years_of_experience"):
                qs.append(
                    "You have ~{0} years with {1} — what has been the hardest problem you solved with it?".format(
                        i["years_of_experience"], s
                    )
                )
        qs.append("What are your salary expectations and notice period?")
        return "Interview questions for {0}:\n{1}".format(
            candidate.candidate_name, bullet(qs[:6])
        )

    # Fit assessment (no JD context in this chat)
    if has_word("fit") or "match" in msg:
        if not skills:
            return (
                "No skills are listed for this candidate yet, so I can't assess "
                "fit — add skills or ask the recruiter for their resume."
            )
        strong_count = sum(
            1
            for i in skills.values()
            if (i.get("proficiency") or "").lower() in ("expert", "advanced")
            or (i.get("years_of_experience") or 0) >= 3
        )
        return (
            "Quick fit read on {0}:\n- {1} skills listed\n- {2} of them are "
            "strong (Expert/Advanced or 3+ years)\n- {3} years total experience\n\n"
            "For a proper fit %, rank this candidate against a specific JD — "
            "this chat has no JD context."
        ).format(candidate.candidate_name, len(skills), strong_count, candidate.total_experience_years or 0)

    # Profile summary / digest
    if any(k in msg for k in ("summar", "overview", "describe", "profile", "about this candidate")):
        return _candidate_digest(candidate)

    # Generic fallback: digest + guidance
    return (
        "Here's a quick overview of this candidate:\n\n{0}\n\n"
        "Ask me about their skills, strengths, experience, interview "
        "questions, salary expectations or fit — or any custom question. For "
        "fully AI-generated answers, enable an AI provider in Desk → "
        "Recruitment Settings → AI Configuration."
    ).format(_candidate_digest(candidate))


@frappe.whitelist()
def ask_ai_about_candidate(candidate_name=None, message=None):
    """Chat-style AI assistant for a specific candidate profile.

    Uses the configured LLM when available; falls back to a rule-based reply
    built from the candidate's profile so the chat always answers.
    """
    _guard()
    if not candidate_name or not frappe.db.exists("Candidate", candidate_name):
        frappe.throw(_("Candidate not found"))
    candidate = frappe.get_doc("Candidate", candidate_name)
    message = (message or "").strip()
    if not message:
        frappe.throw(_("Message is required"))

    if is_llm_configured():
        system = (
            "You are an expert recruiting assistant embedded in HR Master, a "
            "Frappe/ERPNext app. The user is evaluating the candidate shown in "
            "the context. Answer concisely, practically and directly. Base "
            "your answer on the candidate profile; if the question is "
            "unrelated, steer it back helpfully."
        )
        prompt = (
            "CANDIDATE PROFILE:\n{0}\n\nUSER QUESTION:\n{1}\n\nReply with a "
            "helpful, concise answer."
        ).format(_candidate_context_for_prompt(candidate), message[:2000])
        text = call_llm(prompt, system=system, max_tokens=600, temperature=0.4).strip()
        if text:
            return {"status": "success", "reply": text}

    return {"status": "success", "reply": _candidate_chat_rule_based(candidate, message)}
