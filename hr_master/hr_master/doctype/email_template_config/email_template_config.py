"""Email Template Config DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class EmailTemplateConfig(Document):
    """Pre-configured email templates for HR communications."""

    def validate(self):
        self.set_placeholders()

    def set_placeholders(self):
        self.available_placeholders = "{{ candidate_name }}, {{ job_title }}, {{ company_name }}, {{ interviewer_name }}, {{ scheduled_date }}, {{ scheduled_time }}, {{ interview_link }}, {{ recruiter_name }}, {{ offer_link }}"


@frappe.whitelist()
def render_template(template_name, context):
    """Render an email template with the given context."""
    import json
    if isinstance(context, str):
        context = json.loads(context)

    template = frappe.get_doc("Email Template Config", template_name)
    message = template.message_html if template.use_html else template.message_text

    for key, value in context.items():
        placeholder = "{{ " + key + " }}"
        message = message.replace(placeholder, str(value))

    return {
        "subject": template.subject,
        "message": message,
        "use_html": template.use_html,
    }
