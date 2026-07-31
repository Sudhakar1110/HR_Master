"""Job Portal Search DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class JobPortalSearch(Document):
    """Tracks automated searches across job portals for a given JD."""

    def validate(self):
        self.set_defaults()
        self.update_totals()

    def before_insert(self):
        self.search_date = now_datetime()

    def set_defaults(self):
        """Set default values."""
        if not self.status:
            self.status = "Queued"
        if not self.search_date:
            self.search_date = now_datetime()

    def update_totals(self):
        """Update total counts from search results."""
        if self.search_results:
            self.total_candidates_found = len(self.search_results)
            self.linkedin_results = len([r for r in self.search_results if r.source == "LinkedIn"])
            self.naukri_results = len([r for r in self.search_results if r.source == "Naukri"])
            self.indeed_results = len([r for r in self.search_results if r.source == "Indeed"])
            self.monster_results = len([r for r in self.search_results if r.source == "Monster"])

    def import_results_to_candidates(self):
        """Import unimported search results as Candidate documents."""
        imported_count = 0
        for result in self.search_results:
            if not result.is_imported and result.import_status == "Pending":
                try:
                    candidate = frappe.new_doc("Candidate")
                    candidate.candidate_name = result.candidate_name
                    candidate.source = result.source
                    candidate.source_url = result.profile_url
                    candidate.current_title = result.current_title
                    candidate.current_company = result.current_company
                    candidate.location = result.location
                    candidate.total_experience_years = result.experience_years or 0
                    candidate.parsed_skills_from_resume = result.skills_summary
                    candidate.status = "New"
                    candidate.save(ignore_permissions=True)

                    result.is_imported = 1
                    result.import_status = "Imported"
                    imported_count += 1
                except Exception as e:
                    result.import_status = "Failed"
                    frappe.log_error(
                        message=f"Failed to import candidate {result.candidate_name}: {str(e)}",
                        title="Candidate Import Error",
                    )

        if imported_count > 0:
            self.save(ignore_permissions=True)

        return imported_count
