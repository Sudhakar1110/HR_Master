"""Candidate Activity Log DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import today, nowtime


class CandidateActivityLog(Document):
    """Logs all activities related to a candidate for audit trail."""

    def validate(self):
        self.set_defaults()

    def set_defaults(self):
        if not self.activity_date:
            self.activity_date = today()
        if not self.activity_time:
            self.activity_time = nowtime()
        if not self.user:
            self.user = frappe.session.user


@frappe.whitelist()
def log_activity(candidate, activity_type, description, reference_doctype=None, reference_name=None):
    """Utility to log candidate activity from anywhere."""
    cand_name = frappe.db.get_value("Candidate", candidate, "candidate_name")
    log = frappe.new_doc("Candidate Activity Log")
    log.candidate = candidate
    log.candidate_name = cand_name
    log.activity_type = activity_type
    log.description = description
    log.reference_doctype = reference_doctype
    log.reference_name = reference_name
    log.user = frappe.session.user
    log.save(ignore_permissions=True)
    return log.name
