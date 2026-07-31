"""Offer Management DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import today


class OfferManagement(Document):
    """Manages job offers for selected candidates."""

    def validate(self):
        self.calculate_total_ctc()
        self.set_defaults()

    def set_defaults(self):
        if not self.status:
            self.status = "Draft"
        if not self.offer_date:
            self.offer_date = today()

    def calculate_total_ctc(self):
        base = self.base_salary or 0
        variable = self.variable_pay or 0
        self.total_ctc = base + variable

    def before_submit(self):
        if self.status == "Draft":
            self.status = "Approval Pending"

    def on_submit(self):
        self.log_activity("Offer Generated")

    def on_update_after_submit(self):
        if self.status == "Accepted" and self.candidate:
            frappe.db.set_value("Candidate", self.candidate, "status", "Selected")
            self.log_activity("Offer Accepted")
        elif self.status == "Declined":
            self.log_activity("Offer Declined")

    def log_activity(self, activity_type):
        from hr_master.hr_master.doctype.candidate_activity_log.candidate_activity_log import log_activity
        log_activity(
            candidate=self.candidate,
            activity_type=activity_type,
            description=f"Offer {self.status}: {self.name}",
            reference_doctype="Offer Management",
            reference_name=self.name,
        )
