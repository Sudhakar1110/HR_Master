"""Ranking API for HR Master - AI-powered Candidate Scoring"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import now_datetime
from hr_master.security.rate_limiter import rate_limit_decorator


@frappe.whitelist()
@rate_limit_decorator
def rank_all_candidates_for_jd(job_description_name):
    """Rank all candidates associated with a JD."""
    try:
        jd = frappe.get_doc("Job Description", job_description_name)
        if not jd:
            return {"status": "error", "message": _("Job Description not found")}

        rank_candidates(jd)

        return {
            "status": "success",
            "message": _("Candidates ranked for {0}").format(jd.job_title),
        }

    except Exception as e:
        frappe.log_error(
            message=f"Error ranking candidates: {str(e)}",
            title="Candidate Ranking Error",
        )
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
@rate_limit_decorator
def rank_candidates_from_search(search_name):
    """Rank candidates from a portal search against the JD."""
    try:
        search = frappe.get_doc("Job Portal Search", search_name)
        if not search:
            return {"status": "error", "message": _("Search not found")}

        jd = frappe.get_doc("Job Description", search.job_description)
        if not jd:
            return {"status": "error", "message": _("Job Description not found")}

        rank_candidates(jd)

        return {
            "status": "success",
            "message": _("Candidates ranked successfully"),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
@rate_limit_decorator
def get_candidate_ranking_summary(jd_name):
    """Get a summary of candidate rankings for a JD."""
    rankings = frappe.get_all(
        "Candidate Ranking",
        filters={"job_description": jd_name},
        fields=[
            "name",
            "candidate_name",
            "total_match_score",
            "ranking_order",
            "status",
            "recommendation",
        ],
        order_by="total_match_score desc",
        limit=20,
    )

    return rankings


# ------------------------------------------
# Core Ranking Logic
# ------------------------------------------


def rank_candidates(jd):
    """Main ranking logic - calculate match scores for all candidates."""
    # Get all candidates sourced for this JD
    candidates = get_candidates_for_jd(jd)

    if not candidates:
        # Try to get candidates from portal search results
        candidates = get_candidates_from_searches(jd)

    for candidate in candidates:
        calculate_and_save_ranking(jd, candidate)

    # Update JD status
    jd.db_set("portal_search_status", "Searched")
    jd.db_set("status", "In Progress")


def get_candidates_for_jd(jd):
    """Get candidate documents associated with a JD."""
    ranking_candidates = frappe.get_all(
        "Candidate Ranking",
        filters={"job_description": jd.name},
        pluck="candidate",
    )

    if ranking_candidates:
        return frappe.get_all(
            "Candidate",
            filters={"name": ["in", ranking_candidates]},
            fields=["name", "candidate_name", "candidate_skills"],
        )

    # If no existing rankings, get all candidates from searches
    return get_candidates_from_searches(jd)


def get_candidates_from_searches(jd):
    """Get candidates from portal searches for this JD."""
    searches = frappe.get_all(
        "Job Portal Search",
        filters={"job_description": jd.name},
        pluck="name",
    )

    all_candidates = []
    for search_name in searches:
        search = frappe.get_doc("Job Portal Search", search_name)
        if search.search_results:
            for result in search.search_results:
                if result.is_imported:
                    candidate_name = frappe.db.get_value(
                        "Candidate",
                        {"source_url": result.profile_url},
                        "name",
                    )
                    if candidate_name:
                        all_candidates.append({
                            "name": candidate_name,
                            "candidate_name": result.candidate_name,
                        })

    return all_candidates


def calculate_and_save_ranking(jd, candidate_data):
    """Calculate match score and create/update ranking record."""
    candidate = frappe.get_doc("Candidate", candidate_data["name"])
    jd_skills = jd.get_all_skills_with_importance()

    # Calculate skill match
    skill_match_details = []
    total_skill_score = 0

    if jd_skills:
        candidate_skills = candidate.get_skills_with_details()

        for skill_name, skill_info in jd_skills.items():
            match_detail = get_skill_match_detail(
                skill_name, skill_info, candidate_skills
            )
            skill_match_details.append(match_detail)

        total_skill_score = calculate_weighted_score(skill_match_details, jd_skills)

    # Calculate experience match
    experience_match = calculate_experience_match(jd, candidate)

    # Calculate education match
    education_match = calculate_education_match(jd, candidate)

    # Calculate total score
    total_score = (
        total_skill_score * 0.60
        + experience_match["score"] * 0.25
        + education_match["score"] * 0.15
    )

    # Find or create ranking
    existing_ranking = frappe.db.get_value(
        "Candidate Ranking",
        {
            "job_description": jd.name,
            "candidate": candidate.name,
        },
        "name",
    )

    if existing_ranking:
        ranking = frappe.get_doc("Candidate Ranking", existing_ranking)
    else:
        ranking = frappe.new_doc("Candidate Ranking")
        ranking.job_description = jd.name
        ranking.job_title = jd.job_title
        ranking.candidate = candidate.name
        ranking.candidate_name = candidate.candidate_name

    ranking.total_match_score = round(total_score, 1)
    ranking.experience_match_score = round(experience_match["score"], 1)
    ranking.education_match_score = round(education_match["score"], 1)
    ranking.experience_analysis = experience_match["analysis"]
    ranking.education_analysis = education_match["analysis"]
    ranking.evaluation_date = now_datetime()
    ranking.status = "Evaluated"

    # Set recommendation based on score
    if total_score >= 80:
        ranking.recommendation = "Strong Yes"
    elif total_score >= 65:
        ranking.recommendation = "Yes"
    elif total_score >= 50:
        ranking.recommendation = "Maybe"
    elif total_score >= 35:
        ranking.recommendation = "No"
    else:
        ranking.recommendation = "Strong No"

    # Add skill match details
    ranking.set("skills_match_details", [])
    for detail in skill_match_details:
        ranking.append("skills_match_details", detail)

    ranking.save(ignore_permissions=True)

    # Update candidate's total match score
    candidate.db_set("total_match_score", total_score)
    candidate.db_set("last_ranked_date", now_datetime())


def get_skill_match_detail(skill_name, jd_skill_info, candidate_skills):
    """Calculate match detail for an individual skill."""
    import frappe

    skill_found = candidate_skills.get(skill_name) if candidate_skills else None

    is_matched = bool(skill_found)
    match_score = 100 if is_matched else 0

    # Adjust score based on proficiency
    if skill_found:
        proficiency_scores = {
            "Beginner": 25,
            "Intermediate": 50,
            "Advanced": 75,
            "Expert": 100,
        }
        proficiency_score = proficiency_scores.get(
            skill_found.get("proficiency", "Intermediate"), 50
        )

        years_ok = True
        if jd_skill_info.get("min_years") and skill_found.get("years_of_experience"):
            years_ok = skill_found["years_of_experience"] >= jd_skill_info["min_years"]

        match_score = proficiency_score
        if not years_ok:
            match_score = min(proficiency_score, 50)

    return {
        "skill": skill_name,
        "skill_importance": jd_skill_info.get("importance", "Required"),
        "candidate_proficiency": skill_found.get("proficiency", "") if skill_found else "",
        "years_match": 1 if (
            skill_found
            and jd_skill_info.get("min_years")
            and skill_found.get("years_of_experience")
            and skill_found["years_of_experience"] >= jd_skill_info["min_years"]
        ) else 0,
        "match_score": match_score,
        "is_matched": 1 if is_matched else 0,
        "notes": _("Skill found") if is_matched else _("Skill not found in candidate profile"),
    }


def calculate_weighted_score(skill_match_details, jd_skills):
    """Calculate weighted skill match score based on importance."""
    if not skill_match_details:
        return 0

    weighted_sum = 0
    total_weight = 0

    weights = {
        "Required": 3,
        "Preferred": 2,
        "Good to Have": 1,
    }

    for detail in skill_match_details:
        importance = detail.get("skill_importance", "Required")
        weight = weights.get(importance, 1)

        if detail.get("skill_importance") == "Required" and not detail.get("is_matched"):
            # Penalty for unmatched required skills
            weighted_sum -= 10 * weight

        weighted_sum += (detail.get("match_score", 0) * weight)
        total_weight += weight * 100

    return (weighted_sum / total_weight * 100) if total_weight > 0 else 0


def calculate_experience_match(jd, candidate):
    """Calculate experience match score."""
    jd_min_exp = jd.min_experience_years or 0
    jd_max_exp = jd.max_experience_years or 20
    candidate_exp = candidate.total_experience_years or 0

    score = 0
    analysis = ""

    if candidate_exp == 0 and jd_min_exp > 0:
        score = 0
        analysis = _("No experience provided")
    elif jd_min_exp <= candidate_exp <= jd_max_exp:
        score = 100
        analysis = _("Experience matches the requirement ({0} years)").format(candidate_exp)
    elif candidate_exp < jd_min_exp:
        gap = jd_min_exp - candidate_exp
        score = max(0, 100 - (gap / jd_min_exp * 100))
        analysis = _("Candidate has {0} years less experience than required").format(gap)
    elif candidate_exp > jd_max_exp:
        score = 90
        analysis = _("Candidate has more experience than required")

    return {"score": score, "analysis": analysis}


def calculate_education_match(jd, candidate):
    """Calculate education match score."""
    score = 50  # Default moderate score
    analysis = _("Education requirement not specified")

    if candidate.highest_education:
        education_levels = {
            "High School": 1,
            "Diploma": 2,
            "Bachelor's": 3,
            "Master's": 4,
            "MBA": 4,
            "PhD": 5,
        }

        candidate_level = education_levels.get(candidate.highest_education, 0)

        if candidate_level >= 3:
            score = 100
            analysis = _("Candidate has {0} degree").format(candidate.highest_education)
        elif candidate_level >= 2:
            score = 70
            analysis = _("Candidate has {0}").format(candidate.highest_education)
        else:
            score = 40
            analysis = _("Candidate has {0}").format(candidate.highest_education)

    return {"score": score, "analysis": analysis}
