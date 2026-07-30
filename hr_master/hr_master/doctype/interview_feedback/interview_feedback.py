"""Interview Feedback DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class InterviewFeedback(Document):
    """Stores interviewer feedback for candidate interviews."""

    def validate(self):
        self.set_defaults()

    def before_insert(self):
        self.submitted_date = now_datetime()

    def set_defaults(self):
        if not self.interviewer:
            self.interviewer = frappe.session.user

    def after_insert(self):
        self.update_interview_schedule()
        self.log_activity()

    def update_interview_schedule(self):
        """Mark interviewer feedback as submitted on the interview schedule."""
        if self.interview_schedule:
            schedule = frappe.get_doc("Interview Schedule", self.interview_schedule)
            for row in schedule.interviewers:
                if row.interviewer == self.interviewer:
                    row.feedback_submitted = 1
                    break
            schedule.save(ignore_permissions=True)

    def log_activity(self):
        from hr_master.doctype.candidate_activity_log.candidate_activity_log import log_activity
        log_activity(
            candidate=self.candidate,
            activity_type="Feedback Submitted",
            description=f"Feedback submitted by {self.interviewer} for {self.interview_round} - Recommendation: {self.recommendation}",
            reference_doctype="Interview Feedback",
            reference_name=self.name,
        )
