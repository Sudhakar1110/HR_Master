"""Duplicate candidate detection tasks for HR Master"""

from __future__ import unicode_literals

import frappe


def scan_for_duplicates():
    """Weekly cron: Scan for duplicate candidates based on email and name."""
    from frappe.utils import now_datetime

    candidates = frappe.get_all("Candidate", fields=["name", "candidate_name", "email", "phone"])
    dupes = []
    email_map = {}
    name_map = {}

    for c in candidates:
        if c.email:
            email_lower = c.email.lower().strip()
            if email_lower in email_map:
                dupes.append((email_map[email_lower], c.name, "email", c.email))
            else:
                email_map[email_lower] = c.name

        if c.candidate_name:
            name_normalized = c.candidate_name.lower().strip()
            if name_normalized in name_map:
                dupes.append((name_map[name_normalized], c.name, "name", c.candidate_name))
            else:
                name_map[name_normalized] = c.name

    for primary, duplicate, match_type, match_value in dupes:
        log = frappe.new_doc("Candidate Activity Log")
        log.candidate = duplicate
        log.candidate_name = frappe.db.get_value("Candidate", duplicate, "candidate_name")
        log.activity_type = "Status Changed"
        log.description = f"Flagged as possible duplicate of {primary} (matched by {match_type}: {match_value})"
        log.activity_date = frappe.utils.today()
        log.save(ignore_permissions=True)

    frappe.db.commit()

    if dupes:
        frappe.logger().info(f"HR Master: Found {len(dupes)} potential duplicate candidates")
