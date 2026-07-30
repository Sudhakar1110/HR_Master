"""Duplicate Candidate Detection & Resolution Utility for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _
import json
from difflib import SequenceMatcher


@frappe.whitelist()
def find_duplicate_candidates(threshold=None):
    """Find potential duplicate candidates using name and email similarity."""
    try:
        settings = frappe.get_single("Recruitment Settings")
        threshold = threshold or settings.duplicate_threshold or 85
        threshold = int(threshold)

        candidates = frappe.get_all(
            "Candidate",
            fields=["name", "candidate_name", "email", "phone", "status", "creation"],
            order_by="creation desc"
        )

        duplicates = []
        checked = set()

        for i, c1 in enumerate(candidates):
            for j, c2 in enumerate(candidates):
                if i >= j or c1.name in checked or c2.name in checked:
                    continue

                match_score = calculate_similarity(c1, c2)

                if match_score >= threshold:
                    duplicates.append({
                        "candidate_1": c1,
                        "candidate_2": c2,
                        "match_score": match_score,
                        "matched_by": get_match_reason(c1, c2)
                    })
                    checked.add(c2.name)

        return {
            "status": "success",
            "total_candidates": len(candidates),
            "duplicate_groups": len(duplicates),
            "duplicates": duplicates
        }

    except Exception as e:
        frappe.log_error(message=f"Duplicate detection error: {str(e)}", title="Duplicate Detection Error")
        return {"status": "error", "message": str(e)}


def calculate_similarity(c1, c2):
    """Calculate similarity score between two candidates (0-100)."""
    scores = []

    # Email match (exact = 100)
    if c1.email and c2.email:
        if c1.email.lower() == c2.email.lower():
            scores.append(100)
        else:
            scores.append(SequenceMatcher(None, c1.email.lower(), c2.email.lower()).ratio() * 100)

    # Phone match (exact = 100)
    if c1.phone and c2.phone:
        c1_phone = ''.join(filter(str.isdigit, c1.phone))
        c2_phone = ''.join(filter(str.isdigit, c2.phone))
        if c1_phone and c2_phone:
            if c1_phone == c2_phone:
                scores.append(100)
            else:
                scores.append(SequenceMatcher(None, c1_phone, c2_phone).ratio() * 100)

    # Name similarity
    if c1.candidate_name and c2.candidate_name:
        name_sim = SequenceMatcher(
            None, c1.candidate_name.lower(), c2.candidate_name.lower()
        ).ratio() * 100
        scores.append(name_sim)

    return sum(scores) / len(scores) if scores else 0


def get_match_reason(c1, c2):
    """Get human-readable reason for the match."""
    reasons = []
    if c1.email and c2.email and c1.email.lower() == c2.email.lower():
        reasons.append("Same email")
    if c1.phone and c2.phone:
        c1p = ''.join(filter(str.isdigit, c1.phone))
        c2p = ''.join(filter(str.isdigit, c2.phone))
        if c1p and c2p and c1p == c2p:
            reasons.append("Same phone")
    if c1.candidate_name and c2.candidate_name:
        sim = SequenceMatcher(None, c1.candidate_name.lower(), c2.candidate_name.lower()).ratio()
        if sim > 0.9:
            reasons.append("Similar name")
    return ", ".join(reasons) if reasons else "Multiple matching criteria"


@frappe.whitelist()
def merge_duplicates(primary_candidate, duplicate_candidate, merge_activities=True):
    """Merge a duplicate candidate into the primary candidate record."""
    try:
        if not frappe.db.exists("Candidate", primary_candidate):
            return {"status": "error", "message": _("Primary candidate not found")}
        if not frappe.db.exists("Candidate", duplicate_candidate):
            return {"status": "error", "message": _("Duplicate candidate not found")}

        primary = frappe.get_doc("Candidate", primary_candidate)
        duplicate = frappe.get_doc("Candidate", duplicate_candidate)

        # Merge fields (prefer primary, fill empty from duplicate)
        merge_fields = [
            "candidate_name", "email", "phone", "current_title", "current_company",
            "total_experience_years", "highest_education", "resume_text",
            "location", "current_salary", "expected_salary", "notice_period_days",
            "source", "source_url", "parsed_skills_from_resume", "notes"
        ]

        for field in merge_fields:
            if not primary.get(field) and duplicate.get(field):
                primary.set(field, duplicate.get(field))

        # Merge skills
        existing_skills = {s.skill for s in primary.candidate_skills}
        for skill in duplicate.candidate_skills:
            if skill.skill not in existing_skills:
                primary.append("candidate_skills", {
                    "skill": skill.skill,
                    "proficiency": skill.proficiency,
                    "years_of_experience": skill.years_of_experience,
                    "is_primary": skill.is_primary
                })

        primary.save(ignore_permissions=True)

        # Merge activities
        if merge_activities:
            activities = frappe.get_all(
                "Candidate Activity Log",
                filters={"candidate": duplicate_candidate},
                pluck="name"
            )
            for activity_name in activities:
                frappe.db.set_value("Candidate Activity Log", activity_name, "candidate", primary_candidate)

        # Merge rankings
        rankings = frappe.get_all(
            "Candidate Ranking",
            filters={"candidate": duplicate_candidate},
            pluck="name"
        )
        for ranking_name in rankings:
            frappe.db.set_value("Candidate Ranking", ranking_name, "candidate", primary_candidate)

        frappe.db.commit()

        # Mark duplicate as blacklisted
        frappe.db.set_value("Candidate", duplicate_candidate, "status", "Blacklisted")
        frappe.db.set_value("Candidate", duplicate_candidate, "notes", 
                            f"Merged into {primary_candidate} on {frappe.utils.now_datetime()}")

        # Log activity
        from hr_master.doctype.candidate_activity_log.candidate_activity_log import log_activity
        log_activity(
            candidate=primary_candidate,
            activity_type="Status Changed",
            description=_("Merged duplicate {0} into this record").format(duplicate_candidate),
        )

        return {
            "status": "success",
            "primary": primary_candidate,
            "merged": duplicate_candidate,
            "message": _("Successfully merged {0} into {1}").format(duplicate_candidate, primary_candidate)
        }

    except Exception as e:
        frappe.log_error(message=f"Merge error: {str(e)}", title="Merge Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def ignore_duplicate(candidate_name, reason=""):
    """Mark a candidate as reviewed (not a duplicate)."""
    try:
        frappe.db.set_value("Candidate", candidate_name, "notes", 
                            _("Reviewed - Not a duplicate: {0}").format(reason))
        return {"status": "success", "message": _("Duplicate flag ignored")}
    except Exception as e:
        return {"status": "error", "message": str(e)}
