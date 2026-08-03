"""HR Master Recruiting Portal - Job Description detail & portal search page."""

from __future__ import unicode_literals

import frappe
from frappe import _

from hr_master.api.portal_actions import (
    require_hr_access,
    can_write,
    require_write_access,
    redirect_with_flash,
    render_flash,
    set_portal_context,
)
from hr_master.api.search_api import search_candidates_for_jd, import_search_results
from hr_master.api.ranking_api import rank_all_candidates_for_jd


def get_context(context):
    """Render JD details, trigger portal search/import/rank via POST."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "jds"
    context.can_write = can_write()

    jd_name = frappe.form_dict.get("name")
    if not jd_name or not frappe.db.exists("Job Description", jd_name):
        frappe.local.flags.redirect_location = "/hr_portal/jds"
        raise frappe.Redirect

    # Handle POST actions (search / import / rank) - PRG pattern
    if frappe.request.method == "POST":
        action = frappe.form_dict.get("action")
        try:
            require_write_access()

            if action == "search":
                result = search_candidates_for_jd(jd_name)
                message = result.get("message") or "Search queued"
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash("/hr_portal/jd?name={0}".format(jd_name), message, flash_type)
            elif action == "import":
                search_name = frappe.form_dict.get("search_name")
                result = import_search_results(search_name) if search_name else {"status": "error", "message": "No search selected"}
                message = result.get("message") or str(result)
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash("/hr_portal/jd?name={0}".format(jd_name), message, flash_type)
            elif action == "rank":
                result = rank_all_candidates_for_jd(jd_name)
                message = result.get("message") or str(result)
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash("/hr_portal/jd?name={0}".format(jd_name), message, flash_type)
            else:
                frappe.throw(_("Unknown action"))
        except frappe.Redirect:
            raise
        except Exception as e:
            context.flash = {"type": "error", "message": str(e)}

    if frappe.form_dict.get("msg") == "created":
        context.flash = {"type": "success", "message": "Job Description created successfully."}
    else:
        render_flash(context)

    jd = frappe.get_doc("Job Description", jd_name)
    context.jd = jd
    context.page_title = jd.job_title
    context.page_description = "{0} — search candidate portals, import results and rank applicants by match percentage.".format(jd.job_title)

    context.searches = frappe.get_all(
        "Job Portal Search",
        fields=[
            "name",
            "status",
            "search_date",
            "total_candidates_found",
            "linkedin_results",
            "naukri_results",
            "indeed_results",
            "monster_results",
            "serpapi_results",
            "adzuna_results",
            "remotive_results",
            "arbeitnow_results",
            "demo_results",
            "error_log",
        ],
        filters={"job_description": jd_name},
        order_by="search_date desc",
        limit_page_length=20,
    )

    context.ranking_count = frappe.db.count(
        "Candidate Ranking", filters={"job_description": jd_name}
    )

    # Whether a background portal search is still running (drives auto-refresh polling)
    # context.searches comes from frappe.get_all (list of dicts) — use dict access.
    context.search_in_progress = (
        jd.portal_search_status == "Searching"
        or any(s.get("status") in ("Queued", "In Progress") for s in context.searches)
    )

    # Explain a search that finished with 0 results, partially failed or
    # failed entirely (config-aware hint with the real error where available).
    context.search_zero_hint = None
    latest = context.searches[0] if context.searches else None
    if latest and latest.get("status") in ("Completed", "Partial", "Failed"):
        if latest.get("status") == "Failed":
            details = (latest.get("error_log") or "").strip()
            if not details:
                details = _latest_search_errors()
            context.search_zero_hint = {
                "title": "Search failed",
                "body": (
                    "The search job hit an error — details are shown below "
                    "(full traceback in Desk → Error Log). Common causes: an "
                    "invalid/expired SerpAPI key, no network access to the API, "
                    "or a portal that is enabled but not actually available."
                ),
                "details": details,
            }
        elif latest.get("status") == "Partial":
            context.search_zero_hint = {
                "title": "Search partially completed",
                "body": (
                    "Some portals returned results, but others failed. "
                    "Error details from the search job are shown below."
                ),
                "details": (latest.get("error_log") or "").strip(),
            }
        elif not (latest.get("total_candidates_found") or 0):
            config = frappe.get_single("Job Portal Config")
            serpapi_ready = bool(getattr(config, "serpapi_enabled", 0)) and bool(
                getattr(config, "serpapi_api_key", None)
            )
            adzuna_ready = bool(getattr(config, "adzuna_enabled", 0)) and bool(
                getattr(config, "adzuna_app_id", None)
            ) and bool(getattr(config, "adzuna_api_key", None))
            remotive_ready = bool(getattr(config, "remotive_enabled", 0))
            arbeitnow_ready = bool(getattr(config, "arbeitnow_enabled", 0))
            live_ready = serpapi_ready or adzuna_ready or remotive_ready or arbeitnow_ready
            if not live_ready:
                # No live portal configured: point the user to the free no-key
                # sources (Remotive / Arbeitnow) and Demo Search.
                context.search_zero_hint = {
                    "title": "Search finished, but 0 results",
                    "body": (
                        "No portal returned results. Enable Remotive or Arbeitnow in "
                        "Desk → HR Master → Job Portal Config — both are 100% free with no "
                        "API key (real live job data). For a quick zero-key test, enable "
                        "Demo Search instead (returns realistic sample candidates). "
                        "LinkedIn, Naukri and Monster are placeholders and Indeed's free "
                        "API was retired."
                    ),
                }
            else:
                configured = []
                if remotive_ready:
                    configured.append("Remotive")
                if arbeitnow_ready:
                    configured.append("Arbeitnow")
                if serpapi_ready:
                    configured.append("SerpAPI")
                if adzuna_ready:
                    configured.append("Adzuna")
                context.search_zero_hint = {
                    "title": "Search finished, but 0 results",
                    "body": (
                        "{0} {1} enabled but returned no matching listings for these keywords. ".format(
                            " and ".join(configured), "are" if len(configured) > 1 else "is"
                        )
                        + "Try broader keywords, or a different Adzuna country / search limit in Job "
                        + "Portal Config. You can also enable Demo Search to see the full pipeline "
                        + "with sample data."
                    ),
                }

    return context


def _latest_search_errors(limit=3):
    """Return the most recent search-related Error Log messages.

    Used when a search record has no error_log of its own (e.g. it failed
    before the background job could persist one), so the portal can show the
    real reason instead of generic boilerplate.
    """
    try:
        logs = frappe.get_all(
            "Error Log",
            filters={"title": ["like", "%Search Error%"]},
            fields=["message", "creation"],
            order_by="creation desc",
            limit_page_length=limit,
        )
        lines = []
        for log in logs:
            msg = (log.get("message") or "").strip()
            if not msg:
                continue
            if len(msg) > 600:
                msg = msg[:600] + "…"
            lines.append("- [{0}] {1}".format((log.get("creation") or "")[:19], msg))
        return "\n".join(lines)
    except Exception:
        return ""
