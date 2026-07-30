"""Recruitment Settings Singleton Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class RecruitmentSettings(Document):
    """Central configuration for recruitment operations."""
    
    def validate(self):
        self.validate_file_types()

    def validate_file_types(self):
        if self.allowed_file_types:
            types = [t.strip().lower() for t in self.allowed_file_types.split(",")]
            self.allowed_file_types = ", ".join(types)

    def get_allowed_extensions(self):
        if self.allowed_file_types:
            return [f".{t.strip()}" for t in self.allowed_file_types.split(",")]
        return [".pdf", ".docx", ".txt"]
