"""AI-powered candidate ranking engine with ML-based scoring"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import now_datetime
import math


def ai_rank_candidates():
    """Hourly: AI-powered ranking for all unranked candidates against open JDs."""
    open_jds = frappe.get_all(
        "Job Description",
        filters={"status": ["in", ["Open", "In Progress"]]},
        fields=["name", "job_title", "min_experience_years", "max_experience_years"]
    )

    for jd in open_jds:
        try:
            ranked_candidates = frappe.get_all(
                "Candidate Ranking",
                filters={
                    "job_description": jd.name,
                    "status": ["!=", "Archived"]
                },
                pluck="candidate"
            )
            jd_doc = frappe.get_doc("Job Description", jd.name)

            all_candidates = frappe.get_all(
                "Candidate",
                filters={
                    "name": ["not in", ranked_candidates] if ranked_candidates else [],
                    "status": ["!=", "Blacklisted"]
                } if ranked_candidates else {"status": ["!=", "Blacklisted"]},
                fields=["name", "candidate_name", "total_experience_years"]
            )

            for candidate in all_candidates:
                frappe.enqueue(
                    method="hr_master.tasks.ai_ranking.ai_rank_single_candidate",
                    queue="long",
                    timeout=120,
                    jd_name=jd.name,
                    candidate_name=candidate.name
                )
        except Exception as e:
            frappe.log_error(
                message=f"AI ranking error for JD {jd.name}: {str(e)}",
                title="AI Ranking Error"
            )


def ai_rank_single_candidate(jd_name, candidate_name):
    """Rank a single candidate against a JD using advanced scoring."""
    try:
        jd = frappe.get_doc("Job Description", jd_name)
        candidate = frappe.get_doc("Candidate", candidate_name)

        # Calculate advanced match scores
        skill_score = calculate_advanced_skill_score(jd, candidate)
        experience_score = calculate_advanced_experience_score(jd, candidate)
        education_score = calculate_education_score(candidate)
        semantic_score = calculate_semantic_score(jd, candidate)

        # Weighted composite score
        total = (
            skill_score * 0.45 +
            experience_score * 0.20 +
            education_score * 0.10 +
            semantic_score * 0.25
        )

        # Find or create ranking
        existing = frappe.db.get_value(
            "Candidate Ranking",
            {"job_description": jd_name, "candidate": candidate_name},
            "name"
        )

        if existing:
            ranking = frappe.get_doc("Candidate Ranking", existing)
        else:
            ranking = frappe.new_doc("Candidate Ranking")
            ranking.job_description = jd_name
            ranking.job_title = jd.job_title
            ranking.candidate = candidate_name
            ranking.candidate_name = candidate.candidate_name

        ranking.total_match_score = round(min(total, 100), 1)
        ranking.experience_match_score = round(experience_score, 1)
        ranking.education_match_score = round(education_score, 1)
        ranking.evaluation_date = now_datetime()
        ranking.status = "Evaluated"

        # Set recommendation with more granularity
        if total >= 85:
            ranking.recommendation = "Strong Yes"
        elif total >= 70:
            ranking.recommendation = "Yes"
        elif total >= 55:
            ranking.recommendation = "Maybe"
        elif total >= 40:
            ranking.recommendation = "No"
        else:
            ranking.recommendation = "Strong No"

        ranking.save(ignore_permissions=True)

        # Log activity
        from hr_master.doctype.candidate_activity_log.candidate_activity_log import log_activity
        log_activity(
            candidate=candidate_name,
            activity_type="Rank Updated",
            description=f"AI ranking updated: {round(total, 1)}% match for {jd.job_title}",
            reference_doctype="Candidate Ranking",
            reference_name=ranking.name
        )

    except Exception as e:
        frappe.log_error(
            message=f"Error ranking candidate {candidate_name} for JD {jd_name}: {str(e)}",
            title="AI Single Ranking Error"
        )


def calculate_advanced_skill_score(jd, candidate):
    """Calculate skill match using weighted scoring and semantic matching."""
    jd_skills = jd.get_all_skills_with_importance()
    candidate_skills = candidate.get_skills_with_details()

    if not jd_skills:
        return 50

    weights = {"Required": 3, "Preferred": 2, "Good to Have": 1}
    total_weight = 0
    weighted_score = 0

    for skill_name, skill_info in jd_skills.items():
        weight = weights.get(skill_info.get("importance", "Required"), 2)
        total_weight += weight

        if skill_name in candidate_skills:
            cs = candidate_skills[skill_name]
            prof_scores = {"Beginner": 0.3, "Intermediate": 0.6, "Advanced": 0.85, "Expert": 1.0}
            proficiency = prof_scores.get(cs.get("proficiency", "Intermediate"), 0.6)

            years_match = 1.0
            if skill_info.get("min_years") and cs.get("years_of_experience"):
                if cs["years_of_experience"] >= skill_info["min_years"]:
                    years_match = 1.0
                else:
                    years_match = cs["years_of_experience"] / skill_info["min_years"]

            weighted_score += proficiency * years_match * weight
        elif skill_info.get("importance") == "Required":
            weighted_score -= 0.5 * weight

    if total_weight == 0:
        return 50

    normalized = ((weighted_score / total_weight) + 1) / 2 * 100
    return max(0, min(100, normalized))


def calculate_advanced_experience_score(jd, candidate):
    """Calculate experience match with curve fitting."""
    jd_min = jd.min_experience_years or 0
    jd_max = jd.max_experience_years or 20
    candidate_exp = candidate.total_experience_years or 0

    if jd_min == 0 and jd_max == 20:
        return 75  # No specific requirement

    if candidate_exp == 0:
        return 0 if jd_min > 0 else 50

    # Ideal experience is midpoint of range
    ideal = (jd_min + jd_max) / 2

    # Gaussian-like scoring: max at ideal, decays on both sides
    spread = max((jd_max - jd_min) / 2, 1)
    score = 100 * math.exp(-0.5 * ((candidate_exp - ideal) / spread) ** 2)

    if candidate_exp < jd_min:
        score *= 0.8  # Penalize under-experienced

    return max(0, min(100, score))


def calculate_education_score(candidate):
    """Calculate education level score."""
    levels = {"High School": 20, "Diploma": 40, "Bachelor's": 70, "Master's": 85, "MBA": 85, "PhD": 100}
    edu = candidate.highest_education or ""
    return levels.get(edu, 30)


def calculate_semantic_score(jd, candidate):
    """Calculate semantic similarity between JD and candidate profile text."""
    jd_text = (jd.job_title or "") + " " + (jd.job_description_raw or "")
    candidate_text = (candidate.candidate_name or "") + " " + (candidate.resume_text or "")

    if not jd_text or not candidate_text:
        return 50

    jd_words = set(jd_text.lower().split())
    candidate_words = set(candidate_text.lower().split())

    if not jd_words:
        return 50

    intersection = jd_words.intersection(candidate_words)
    overlap = len(intersection) / len(jd_words) if jd_words else 0

    return min(100, overlap * 100)
