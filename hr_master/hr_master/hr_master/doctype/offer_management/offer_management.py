"""Offer Management DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import today


def _as_float(value):
    """Coerce a value (string/number/None) to a float; 0.0 when empty/invalid.

    Values can arrive as strings (e.g. via the portal or the REST API), so
    arithmetic must coerce first to avoid TypeError: can only concatenate
    str (not "int") to str.
    """
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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
        base = _as_float(self.base_salary)
        variable = _as_float(self.variable_pay)
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
