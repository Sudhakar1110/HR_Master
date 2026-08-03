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


@frappe.whitelist()
def auto_merge_exact_duplicates():
    """Weekly cron: automatically merge 100%-match duplicate candidates.

    Only pairs that score 100% AND share an exact email or phone are merged -
    identical names alone are never auto-merged, so two different people with
    the same name stay separate. The record with the most complete data is
    kept as the primary; the other is merged into it (skills, activities and
    rankings move across) and marked Blacklisted - exactly like a manual merge
    from the portal's Duplicates page.

    Gated by 'Enable Duplicate Detection' and 'Auto-Merge Exact Duplicates'
    in Recruitment Settings. Whitelisted so it can also be triggered manually.
    """
    from hr_master.utils.duplicate_resolution import (
        find_duplicate_candidates,
        merge_duplicates,
    )

    settings = frappe.get_single("Recruitment Settings")
    if not settings.get("enable_duplicate_detection"):
        return {"status": "skipped", "message": "Duplicate detection is disabled"}
    if not settings.get("auto_merge_duplicates"):
        return {"status": "skipped", "message": "Auto-merge is disabled in Recruitment Settings"}

    result = find_duplicate_candidates(threshold=100) or {}
    groups = result.get("duplicates") or []

    # Fetch notes up-front so already-merged / reviewed candidates are skipped.
    names = set()
    for g in groups:
        for side in ("candidate_1", "candidate_2"):
            name = (g.get(side) or {}).get("name")
            if name:
                names.add(name)

    notes_map = {}
    if names:
        rows = frappe.get_all(
            "Candidate",
            fields=["name", "notes"],
            filters={"name": ["in", list(names)]},
            limit_page_length=0,
        )
        notes_map = {row.get("name"): (row.get("notes") or "") for row in rows}

    merged = 0
    skipped = 0
    for g in groups:
        c1 = g.get("candidate_1") or {}
        c2 = g.get("candidate_2") or {}
        reason = g.get("matched_by") or ""

        # Safety: only auto-merge when an exact unique identifier matches
        # ("Same email" / "Same phone" never appear for name-only matches).
        if "Same email" not in reason and "Same phone" not in reason:
            skipped += 1
            continue

        if _is_unmergeable(c1, notes_map) or _is_unmergeable(c2, notes_map):
            skipped += 1
            continue

        primary, duplicate = _choose_primary(c1, c2)

        # Fresh re-check: the group snapshot can be stale if an earlier merge
        # in this run already blacklisted one of these candidates.
        if primary.status == "Blacklisted" or duplicate.status == "Blacklisted":
            skipped += 1
            continue

        outcome = merge_duplicates(primary.name, duplicate.name)
        if outcome.get("status") == "success":
            merged += 1
        else:
            skipped += 1

    frappe.db.commit()

    if merged or skipped:
        frappe.logger().info(
            "HR Master: Auto-merged {0} duplicate pair(s), skipped {1} (weekly scan)".format(merged, skipped)
        )
    return {"status": "success", "auto_merged": merged, "skipped": skipped}


def _is_unmergeable(candidate, notes_map):
    """Skip candidates that are blacklisted or already merged / reviewed."""
    if candidate.get("status") == "Blacklisted":
        return True
    notes = (notes_map.get(candidate.get("name")) or "").lower()
    return "merged into" in notes or "reviewed - not a duplicate" in notes


def _choose_primary(c1, c2):
    """Pick the record to keep: the more complete one; ties go to the older one.
    Returns the (primary, duplicate) Document objects, freshly read from the DB."""
    d1 = frappe.get_doc("Candidate", c1.get("name"))
    d2 = frappe.get_doc("Candidate", c2.get("name"))

    s1, s2 = _completeness(d1), _completeness(d2)
    if s1 > s2:
        return d1, d2
    if s2 > s1:
        return d2, d1

    if (c1.get("creation") or "") <= (c2.get("creation") or ""):
        return d1, d2
    return d2, d1


def _completeness(doc):
    """Data-completeness score used to choose the primary record to keep."""
    fields = [
        "email", "phone", "current_company", "current_title", "location",
        "resume_text", "parsed_skills_from_resume", "languages",
        "certifications", "highest_education", "college", "notes",
    ]
    score = sum(1 for f in fields if doc.get(f))
    if doc.get("resume_attachment"):
        score += 1
    score += len(doc.get("candidate_skills") or [])
    return score
