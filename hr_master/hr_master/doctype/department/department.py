"""Department DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class Department(Document):
    """Department master data for organizing JDs and candidates."""

    def validate(self):
        self.set_department_name()

    def set_department_name(self):
        """Ensure department name is properly formatted."""
        if self.department_name:
            self.department_name = self.department_name.strip().title()
