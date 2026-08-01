"""HR Master Recruiting Portal - Ranked candidate results page."""

from __future__ import unicode_literals

import frappe
from frappe import _

from hr_master.api.portal_actions import (
    require_hr_access,
    can_write,
    require_write_access,
    set_ranking_status,
    redirect_with_flash,
    render_flash,
    set_portal_context,
)
from hr_master.api.ranking_api import rank_all_candidates_for_jd


def get_context(context):
    """Render candidates ranked by match % for a JD; handle workflow actions."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "jds"
    context.can_write = can_write()

    jd_name = frappe.form_dict.get("jd")
    if not jd_name or not frappe.db.exists("Job Description", jd_name):
        frappe.local.flags.redirect_location = "/hr_portal/jds"
        raise frappe.Redirect

    # Handle POST (workflow actions / re-rank) - PRG pattern
    if frappe.request.method == "POST":
        action = frappe.form_dict.get("action")
        ranking_name = frappe.form_dict.get("ranking")
        try:
            require_write_access()

            if action == "rank_all":
                result = rank_all_candidates_for_jd(jd_name)
                message = result.get("message") or str(result)
                flash_type = "success" if result.get("status") == "success" else "error"
                redirect_with_flash("/hr_portal/results?jd={0}".format(jd_name), message, flash_type)
            elif ranking_name and frappe.db.exists("Candidate Ranking", ranking_name):
                set_ranking_status(ranking_name, action)
                redirect_with_flash(
                    "/hr_portal/results?jd={0}".format(jd_name),
                    "Status updated: {0}".format(action),
                )
            else:
                frappe.throw(_("Ranking not found"))
        except frappe.Redirect:
            raise
        except Exception as e:
            context.flash = {"type": "error", "message": str(e)}

    render_flash(context)

    jd = frappe.get_doc("Job Description", jd_name)
    context.jd = jd
    context.page_title = "Ranked Candidates — {0}".format(jd.job_title)
    context.page_description = "Ranked candidates for {0}, sorted by match percentage with shortlist, reject and hold actions.".format(jd.job_title)

    context.rankings = frappe.get_all(
        "Candidate Ranking",
        fields=[
            "name",
            "candidate",
            "candidate_name",
            "total_match_score",
            "ranking_order",
            "status",
            "recommendation",
            "experience_match_score",
            "education_match_score",
            "evaluation_date",
        ],
        filters={"job_description": jd_name},
        order_by="total_match_score desc",
        limit_page_length=200,
    )

    # frappe.get_all returns dicts — use dict access
    scores = [r.get("total_match_score") or 0 for r in context.rankings]
    context.ranked_count = len(scores)
    context.avg_match = round(sum(scores) / context.ranked_count, 1) if scores else 0
    context.best_match = max(scores) if scores else 0
    context.shortlisted_count = frappe.db.count(
        "Candidate Ranking",
        filters={
            "job_description": jd_name,
            "status": ["in", ["Shortlisted", "Interview Scheduled"]],
        },
    )

    return context
