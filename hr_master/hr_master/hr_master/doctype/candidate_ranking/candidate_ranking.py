"""Candidate Ranking DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class CandidateRanking(Document):
    """Stores the candidate-to-JD matching score and ranking details."""

    def validate(self):
        self.set_defaults()
        self.update_rank_order()

    def before_insert(self):
        self.evaluation_date = now_datetime()

    def set_defaults(self):
        """Set default values."""
        if not self.status:
            self.status = "Pending"
        if not self.evaluation_date:
            self.evaluation_date = now_datetime()

    def update_rank_order(self):
        """Calculate and set the ranking order based on total match score."""
        if self.total_match_score:
            existing = frappe.get_all(
                "Candidate Ranking",
                filters={
                    "job_description": self.job_description,
                    "name": ["!=", self.name],
                },
                fields=["name", "total_match_score", "ranking_order"],
                order_by="total_match_score desc",
            )

            # Re-calculate rankings
            all_rankings = existing + [
                {"name": self.name, "total_match_score": self.total_match_score}
            ]
            all_rankings.sort(key=lambda x: x.get("total_match_score", 0) or 0, reverse=True)

            for i, r in enumerate(all_rankings, 1):
                if r["name"] == self.name:
                    self.ranking_order = i

    def calculate_total_score(self):
        """Calculate weighted total match score."""
        skill_score = 0
        experience_score = 0
        education_score = 0

        if self.skills_match_details:
            matched = sum(1 for s in self.skills_match_details if s.is_matched)
            total = len(self.skills_match_details)
            if total > 0:
                # Weight required skills higher
                required_skills = [s for s in self.skills_match_details if s.skill_importance == "Required"]
                preferred_skills = [s for s in self.skills_match_details if s.skill_importance == "Preferred"]

                required_matched = sum(1 for s in required_skills if s.is_matched)
                preferred_matched = sum(1 for s in preferred_skills if s.is_matched)

                required_weight = 0.6
                preferred_weight = 0.3
                good_to_have_weight = 0.1

                required_score = (required_matched / len(required_skills)) * 100 if required_skills else 0
                preferred_score = (preferred_matched / len(preferred_skills)) * 100 if preferred_skills else 0

                good_to_have = [s for s in self.skills_match_details if s.skill_importance == "Good to Have"]
                good_to_have_matched = sum(1 for s in good_to_have if s.is_matched)
                good_to_have_score = (good_to_have_matched / len(good_to_have)) * 100 if good_to_have else 100

                skill_score = (
                    required_score * required_weight
                    + preferred_score * preferred_weight
                    + good_to_have_score * good_to_have_weight
                )

        self.total_match_score = round(skill_score, 1)


def after_insert(doc, method):
    """Post-insert processing for Candidate Ranking."""
    # Trigger notification if score is above threshold
    threshold = frappe.db.get_single_value("Job Portal Config", "auto_shortlist_threshold") or 80
    if doc.total_match_score and doc.total_match_score >= threshold:
        create_shortlist_notification(doc)


def create_shortlist_notification(ranking_doc):
    """Create notification for highly-matched candidates."""
    notification = frappe.new_doc("Notification Log")
    notification.subject = f"High Match Candidate: {ranking_doc.candidate_name} ({ranking_doc.total_match_score}%)"
    notification.email_content = (
        f"Candidate {ranking_doc.candidate_name} has scored {ranking_doc.total_match_score}% "
        f"match for {ranking_doc.job_title} ({ranking_doc.job_description})."
    )
    notification.document_type = "Candidate Ranking"
    notification.document_name = ranking_doc.name
    notification.for_user = frappe.db.get_value(
        "Job Description", ranking_doc.job_description, "owner"
    )
    notification.type = "Alert"
    notification.save(ignore_permissions=True)
