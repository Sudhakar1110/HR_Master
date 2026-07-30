"""Background email queue processing for HR Master

Processes queued email notifications using Frappe's email queue system.
Handles batching, retries, and failure tracking for all HR communications.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date


def process_email_queue():
    """Daily: Process pending emails in the queue."""
    try:
        pending = frappe.db.sql("""
            SELECT name, recipient, subject, message, reference_doctype, reference_name
            FROM `tabEmail Queue`
            WHERE status = "Not Sent"
                AND creation >= %s
                AND (send_after IS NULL OR send_after <= %s)
            ORDER BY creation ASC
            LIMIT 100
        """, (add_to_date(now_datetime(), days=-7), now_datetime()), as_dict=True)

        if not pending:
            return

        sent_count = 0
        failed_count = 0

        for email in pending:
            try:
                frappe.sendmail(
                    recipients=[email.recipient],
                    subject=email.subject,
                    message=email.message,
                    reference_doctype=email.reference_doctype,
                    reference_name=email.reference_name,
                    now=True
                )
                frappe.db.set_value("Email Queue", email.name, "status", "Sent")
                sent_count += 1
            except Exception as e:
                frappe.db.set_value("Email Queue", email.name, "status", "Error")
                frappe.db.set_value("Email Queue", email.name, "error", str(e))
                failed_count += 1

        frappe.db.commit()

        frappe.logger().info(
            f"HR Master Email Queue: {sent_count} sent, {failed_count} failed"
        )

    except Exception as e:
        frappe.log_error(
            message=f"Email queue processing error: {str(e)}",
            title="Email Queue Error"
        )


def enqueue_notification_email(recipient, subject, message, reference_doctype=None, reference_name=None):
    """Utility to enqueue an email notification for background processing."""
    try:
        queue = frappe.new_doc("Email Queue")
        queue.recipient = recipient
        queue.subject = subject
        queue.message = message
        queue.reference_doctype = reference_doctype
        queue.reference_name = reference_name
        queue.status = "Not Sent"
        queue.priority = 1
        queue.save(ignore_permissions=True)
        frappe.db.commit()
        return queue.name
    except Exception as e:
        frappe.log_error(
            message=f"Failed to enqueue email: {str(e)}",
            title="Email Enqueue Error"
        )
        return None


def send_hr_notification(recipient, subject, template, context, reference_doctype=None, reference_name=None):
    """Send an HR notification using email templates."""
    try:
        # Try to find a matching email template
        template_doc = None
        if frappe.db.exists("Email Template Config", template):
            template_doc = frappe.get_doc("Email Template Config", template)

        if template_doc:
            message = template_doc.message_html if template_doc.use_html else template_doc.message_text
            email_subject = template_doc.subject

            for key, value in context.items():
                placeholder = "{{ " + key + " }}"
                message = message.replace(placeholder, str(value))
                email_subject = email_subject.replace(placeholder, str(value))
        else:
            message = subject
            email_subject = subject

        enqueue_notification_email(
            recipient=recipient,
            subject=email_subject,
            message=message,
            reference_doctype=reference_doctype,
            reference_name=reference_name
        )

    except Exception as e:
        frappe.log_error(
            message=f"Failed to send HR notification: {str(e)}",
            title="HR Notification Error"
        )
