"""Search History DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe, json
from frappe.model.document import Document
from frappe.utils import now_datetime


class SearchHistory(Document):
    """Records all searches performed in the system for audit and analytics."""

    def validate(self):
        self.set_defaults()

    def set_defaults(self):
        if not self.user:
            self.user = frappe.session.user
        if not self.search_date:
            self.search_date = now_datetime()


@frappe.whitelist()
def log_search(query, search_type, result_count=0, filters=None, ref_doctype=None, ref_name=None):
    """Log a search into Search History."""
    sh = frappe.new_doc("Search History")
    sh.search_query = query
    sh.search_type = search_type
    sh.result_count = result_count
    if filters:
        sh.filters_used = json.dumps(filters, default=str)
    sh.ref_doctype = ref_doctype
    sh.ref_name = ref_name
    sh.save(ignore_permissions=True)
    return sh.name
