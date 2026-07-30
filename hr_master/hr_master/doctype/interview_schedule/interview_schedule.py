"""Interview Schedule DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import today


class InterviewSchedule(Document):
    """Interview schedule management for candidates."""

    def validate(self):
        self.set_defaults()
        self.validate_schedule()
        self.update_candidate_status()

    def set_defaults(self):
        """Set default values."""
        if not self.status:
            self.status = "Scheduled"
        if not self.mode_of_interview:
            self.mode_of_interview = "Video Call"
        if not self.duration_minutes:
            self.duration_minutes = 60

    def validate_schedule(self):
        """Validate interview schedule fields."""
        if self.scheduled_date and self.scheduled_date < today():
            frappe.throw("Scheduled Date cannot be in the past")

        if self.scheduled_date and self.scheduled_time:
            # Check for conflicts with existing interviews for the same candidate
            conflicts = frappe.db.exists(
                "Interview Schedule",
                {
                    "candidate": self.candidate,
                    "scheduled_date": self.scheduled_date,
                    "scheduled_time": self.scheduled_time,
                    "status": ["in", ["Scheduled", "Rescheduled"]],
                    "name": ["!=", self.name],
                },
            )
            if conflicts:
                frappe.throw(
                    "This candidate already has an interview scheduled at this time"
                )

    def update_candidate_status(self):
        """Update candidate status when interview is scheduled."""
        if self.status == "Scheduled" and self.candidate:
            candidate = frappe.get_doc("Candidate", self.candidate)
            if candidate.status not in ["Interview Scheduled", "Selected", "Rejected"]:
                candidate.status = "Interview Scheduled"
                candidate.save(ignore_permissions=True)

    def before_submit(self):
        """Actions before submission."""
        if self.status == "Scheduled":
            if self.send_calendar_invite:
                self.send_interview_invite()

    def send_interview_invite(self):
        """Send email notification about the interview."""
        recipients = [self.candidate_name]
        if self.interviewers:
            for interviewer in self.interviewers:
                if interviewer.email:
                    recipients.append(interviewer.email)

        subject = f"Interview Scheduled: {self.interview_type} - {self.candidate_name}"
        message = f"""
        <h3>Interview Schedule</h3>
        <p><strong>Candidate:</strong> {self.candidate_name}</p>
        <p><strong>Job:</strong> {self.job_title}</p>
        <p><strong>Date:</strong> {self.scheduled_date}</p>
        <p><strong>Time:</strong> {self.scheduled_time}</p>
        <p><strong>Duration:</strong> {self.duration_minutes} minutes</p>
        <p><strong>Mode:</strong> {self.mode_of_interview}</p>
        <p><strong>Location/Link:</strong> {self.location_or_link}</p>
        <p><strong>Round:</strong> {self.interview_round}</p>
        """

        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            reference_doctype="Interview Schedule",
            reference_name=self.name,
        )


def on_update(doc, method):
    """Handle post-save actions for Interview Schedule."""
    if doc.status == "Completed" and doc.result:
        update_candidate_status_from_interview(doc)


def update_candidate_status_from_interview(interview):
    """Update candidate status based on interview result."""
    if interview.candidate:
        candidate = frappe.get_doc("Candidate", interview.candidate)
        if interview.result == "Selected":
            candidate.status = "Selected"
        elif interview.result == "Rejected":
            candidate.status = "Rejected"
        elif interview.result == "Advanced to Next Round":
            candidate.status = "Interview Scheduled"
        candidate.save(ignore_permissions=True)
