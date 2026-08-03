"""HR Master Recruiting Portal - Duplicate candidate review & merge page."""

from __future__ import unicode_literals

import frappe
from frappe import _

from hr_master.api.portal_actions import (
    can_write,
    redirect_with_flash,
    render_flash,
    require_hr_access,
    require_write_access,
    set_portal_context,
)
from hr_master.utils.duplicate_resolution import (
    find_duplicate_candidates,
    ignore_duplicate,
    merge_duplicates,
)


def get_context(context):
    """Review duplicate candidate groups and merge / ignore them."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "duplicates"
    context.can_write = can_write()

    if frappe.request.method == "POST":
        action = frappe.form_dict.get("action")
        try:
            require_write_access()
            if action == "merge":
                primary = frappe.form_dict.get("primary")
                duplicate = frappe.form_dict.get("duplicate")
                result = merge_duplicates(primary, duplicate)
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash(
                    "/hr_portal/duplicates",
                    result.get("message") or "Candidates merged",
                    flash_type,
                )
            elif action == "ignore":
                name = frappe.form_dict.get("candidate")
                result = ignore_duplicate(name, "Reviewed in portal")
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash(
                    "/hr_portal/duplicates",
                    result.get("message") or "Marked as not a duplicate",
                    flash_type,
                )
            else:
                frappe.throw(_("Unknown action"))
        except frappe.Redirect:
            raise
        except Exception as e:
            context.flash = {"type": "error", "message": str(e)}

    render_flash(context)

    context.page_title = "Duplicate Candidates"
    context.page_description = "Candidates matched by name, email or phone — merge duplicates into a single record."

    result = find_duplicate_candidates() or {}
    groups = result.get("duplicates") or []
    context.total_candidates = result.get("total_candidates", 0)

    # Hide candidates already merged or reviewed
    names = set()
    for g in groups:
        names.add(g.get("candidate_1", {}).get("name"))
        names.add(g.get("candidate_2", {}).get("name"))
    names.discard(None)

    extra = {}
    if names:
        rows = frappe.get_all(
            "Candidate",
            fields=["name", "source", "status", "notes"],
            filters={"name": ["in", list(names)]},
            limit_page_length=0,
        )
        extra = {row["name"]: row for row in rows}

    def _skip(name):
        if not name:
            return True
        notes = (extra.get(name) or {}).get("notes") or ""
        return "Merged into" in notes or "Reviewed - Not a duplicate" in notes

    filtered = []
    for g in groups:
        c1 = g.get("candidate_1") or {}
        c2 = g.get("candidate_2") or {}
        if _skip(c1.get("name")) or _skip(c2.get("name")):
            continue
        for c in (c1, c2):
            info = extra.get(c.get("name")) or {}
            c["source"] = info.get("source") or ""
            c["status"] = info.get("status") or ""
        filtered.append(g)

    context.groups = filtered
    context.duplicate_count = len(filtered)
    return context
