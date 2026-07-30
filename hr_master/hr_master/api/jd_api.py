"""JD Analysis API for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _


@frappe.whitelist()
def parse_skills_from_jd(jd_text):
    """Parse and extract skills from Job Description text."""
    if not jd_text:
        return []

    from hr_master.doctype.skill.skill import extract_skills_from_text

    # Strip HTML tags
    raw_text = frappe.utils.strip_html_tags(jd_text)
    found_skills = extract_skills_from_text(raw_text)

    return found_skills


@frappe.whitelist()
def analyze_jd_complexity(jd_name):
    """Analyze the complexity and completeness of a JD."""
    jd = frappe.get_doc("Job Description", jd_name)
    if not jd:
        return {"status": "error", "message": _("JD not found")}

    analysis = {
        "completeness_score": 0,
        "has_title": bool(jd.job_title),
        "has_description": bool(jd.job_description_raw),
        "has_required_skills": bool(jd.required_skills),
        "has_experience_range": bool(jd.min_experience_years or jd.max_experience_years),
        "has_location": bool(jd.location),
        "has_employment_type": bool(jd.employment_type),
        "has_salary_range": bool(jd.salary_range_min or jd.salary_range_max),
        "total_skills_required": len(jd.required_skills) if jd.required_skills else 0,
        "total_skills_preferred": len(jd.preferred_skills) if jd.preferred_skills else 0,
    }

    # Calculate completeness score (out of 7 factors)
    completeness_factors = [
        analysis["has_title"],
        analysis["has_description"],
        analysis["has_required_skills"],
        analysis["has_experience_range"],
        analysis["has_location"],
        analysis["has_employment_type"],
        analysis["has_salary_range"],
    ]
    analysis["completeness_score"] = sum(completeness_factors) / len(completeness_factors) * 100

    return analysis


@frappe.whitelist()
def suggest_skills_for_jd(jd_name):
    """Suggest additional skills based on existing ones in the JD."""
    jd = frappe.get_doc("Job Description", jd_name)
    if not jd:
        return []

    current_skills = set()
    if jd.required_skills:
        current_skills.update(row.skill for row in jd.required_skills)
    if jd.preferred_skills:
        current_skills.update(row.skill for row in jd.preferred_skills)

    # Find related skills based on skill category
    suggestions = []
    if current_skills:
        for skill_name in current_skills:
            skill = frappe.get_doc("Skill", skill_name) if frappe.db.exists("Skill", skill_name) else None
            if skill and skill.category:
                related = frappe.get_all(
                    "Skill",
                    filters={
                        "category": skill.category,
                        "name": ["not in", list(current_skills)],
                        "is_active": 1,
                    },
                    pluck="name",
                    limit=3,
                )
                suggestions.extend(related)

    return list(set(suggestions))[:10]
