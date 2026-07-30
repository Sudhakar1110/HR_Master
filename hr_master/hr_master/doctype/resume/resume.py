"""Resume DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class Resume(Document):
    """Resume document for storing parsed resume data."""

    def validate(self):
        self.set_defaults()
        self.set_file_metadata()

    def before_insert(self):
        self.uploaded_on = now_datetime()
        self.uploaded_by = frappe.session.user

    def set_defaults(self):
        if not self.parsing_status:
            self.parsing_status = "Pending"
        if not self.version:
            self.version = 1
        if not self.is_latest:
            self.is_latest = 1

    def set_file_metadata(self):
        if self.resume_file:
            ext = self.resume_file.rsplit(".", 1)[-1].lower() if "." in self.resume_file else ""
            type_map = {"pdf": "PDF", "docx": "DOCX", "txt": "TXT", "png": "Image", "jpg": "Image", "jpeg": "Image"}
            self.file_type = type_map.get(ext, "TXT")

    def on_submit(self):
        """On submit, link resume to candidate and queue parsing."""
        if self.candidate and self.parsing_status == "Pending":
            self.queue_parsing()

    def queue_parsing(self):
        """Queue resume for background parsing."""
        frappe.enqueue(
            method="hr_master.tasks.resume_queue.process_resume_parsing",
            queue="long",
            timeout=300,
            resume_name=self.name,
        )


@frappe.whitelist()
def create_resume_from_attachment(candidate_name, file_url):
    """Create a Resume document from an attached file."""
    candidate = frappe.get_doc("Candidate", candidate_name)
    resume = frappe.new_doc("Resume")
    resume.candidate = candidate_name
    resume.candidate_name = candidate.candidate_name
    resume.resume_file = file_url
    resume.uploaded_by = frappe.session.user
    resume.uploaded_on = now_datetime()
    resume.save(ignore_permissions=True)
    resume.submit()
    return resume.name
