"""Job Description DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import today, nowdate


class JobDescription(Document):
    """Job Description document for managing job requisitions and candidate sourcing."""

    def validate(self):
        self.set_defaults()
        self.parse_jd_for_skills()
        self.validate_dates()

    def before_submit(self):
        self.status = "Open"

    def before_cancel(self):
        self.status = "Cancelled"

    def set_defaults(self):
        """Set default values if not provided."""
        if not self.posting_date:
            self.posting_date = today()
        if not self.status:
            self.status = "Draft"
        if not self.portal_search_status:
            self.portal_search_status = "Not Searched"

    def validate_dates(self):
        """Validate date fields."""
        if self.target_close_date and self.posting_date:
            if self.target_close_date < self.posting_date:
                frappe.throw(
                    "Target Close Date cannot be before Posting Date"
                )

    def parse_jd_for_skills(self):
        """Parse raw JD text to extract skills automatically."""
        if not self.job_description_raw:
            return

        raw_text = frappe.utils.strip_html_tags(self.job_description_raw)
        from hr_master.hr_master.doctype.skill.skill import extract_skills_from_text

        found_skills = extract_skills_from_text(raw_text)
        if found_skills:
            self.parsed_skills = ", ".join(found_skills)

    def get_required_skills_list(self):
        """Get list of required skills."""
        if not self.required_skills:
            return []
        return [row.skill for row in self.required_skills]

    def get_preferred_skills_list(self):
        """Get list of preferred skills."""
        if not self.preferred_skills:
            return []
        return [row.skill for row in self.preferred_skills]

    def get_all_skills_with_importance(self):
        """Get all skills with their importance levels."""
        all_skills = {}
        if self.required_skills:
            for row in self.required_skills:
                all_skills[row.skill] = {
                    "importance": row.importance,
                    "min_years": row.min_years,
                    "is_mandatory": row.is_mandatory,
                }
        if self.preferred_skills:
            for row in self.preferred_skills:
                all_skills[row.skill] = {
                    "importance": row.importance,
                    "min_years": row.min_years,
                    "is_mandatory": row.is_mandatory,
                }
        return all_skills


def on_update(doc, method):
    """Handle post-save actions for Job Description."""
    if doc.status == "Open" and not doc.amended_from:
        auto_trigger_search(doc)


def auto_trigger_search(doc):
    """Automatically trigger portal search when JD is opened."""
    from hr_master.tasks.celery import process_candidate_search

    if frappe.db.get_single_value("Job Portal Config", "auto_search_enabled"):
        frappe.enqueue(
            method=process_candidate_search,
            queue="long",
            timeout=300,
            job_description_name=doc.name,
        )
