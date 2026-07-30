"""Candidate DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class Candidate(Document):
    """Candidate document for managing sourced candidates."""

    def validate(self):
        self.set_candidate_name()
        self.validate_email()
        self.parse_resume_for_skills()

    def set_candidate_name(self):
        """Format candidate name properly."""
        if self.candidate_name:
            self.candidate_name = self.candidate_name.strip().title()

    def validate_email(self):
        """Basic email validation."""
        if self.email and "@" not in self.email:
            frappe.throw("Please enter a valid email address")

    def parse_resume_for_skills(self):
        """Parse resume text to extract skills automatically."""
        if not self.resume_text and not self.candidate_skills:
            return

        if self.resume_text and not self.parsed_skills_from_resume:
            from hr_master.doctype.skill.skill import extract_skills_from_text

            found_skills = extract_skills_from_text(self.resume_text)
            if found_skills:
                self.parsed_skills_from_resume = ", ".join(found_skills)

    def get_skills_list(self):
        """Get list of candidate's skills."""
        if not self.candidate_skills:
            return []
        return [row.skill for row in self.candidate_skills]

    def get_skills_with_details(self):
        """Get candidate skills with proficiency and years."""
        skills = {}
        if self.candidate_skills:
            for row in self.candidate_skills:
                skills[row.skill] = {
                    "years_of_experience": row.years_of_experience,
                    "proficiency": row.proficiency,
                    "is_primary": row.is_primary,
                }
        return skills


def after_insert(doc, method):
    """Log activity when a new candidate is created."""
    from hr_master.doctype.candidate_activity_log.candidate_activity_log import log_activity
    log_activity(
        candidate=doc.name,
        activity_type="Created",
        description=f"Candidate {doc.candidate_name} created via {doc.source or 'Manual Entry'}",
        reference_doctype="Candidate",
        reference_name=doc.name
    )


def get_permission_query_conditions(user=None):
    """Return permission query conditions for Candidate."""
    if not user:
        user = frappe.session.user

    user_roles = frappe.get_roles(user)

    if "HR Master Admin" in user_roles:
        return ""

    if "HR Master Recruiter" in user_roles:
        return ""

    if "HR Master Hiring Manager" in user_roles:
        return ""

    if "HR Master Viewer" in user_roles:
        return ""

    return """(`tabCandidate`.owner = '{user}' or `tabCandidate`.blacklisted = 0)""".format(
        user=user
    )
