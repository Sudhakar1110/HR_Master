"""HR Master Recruiting Portal - Job Description list & creation page."""

from __future__ import unicode_literals

import json

import frappe

from hr_master.api.portal_actions import (
    require_hr_access,
    can_write,
    create_jd,
    set_portal_context,
    jd_visibility,
    get_hr_roles,
)
from hr_master.utils.jd_templates import get_templates


def get_context(context):
    """Render the JD list and handle JD creation via POST."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "jds"
    context.page_title = "Job Descriptions"
    context.page_description = "Create and manage job descriptions, then search candidate portals and rank applicants by match percentage."
    context.can_write = can_write()
    context.is_hiring_manager = get_hr_roles() == ["HR Master Hiring Manager"]

    # Users for the Hiring Manager picker (all enabled, non-Guest)
    context.users = frappe.get_all(
        "User",
        fields=["name", "full_name"],
        filters={"enabled": 1, "name": ["!=", "Guest"]},
        order_by="full_name asc",
        limit_page_length=300,
    ) or []

    # Handle POST (create JD)
    if frappe.request.method == "POST":
        data = {k: v for k, v in frappe.form_dict.items() if k != "csrf_token"}
        try:
            result = create_jd(json.dumps(data))
            frappe.local.flags.redirect_location = (
                "/hr_portal/jd?name={0}&msg=created".format(result["name"])
            )
            raise frappe.Redirect
        except frappe.Redirect:
            raise
        except Exception as e:
            context.form_error = str(e)
            context.form_values = data

    jd_filters, jd_or_filters = jd_visibility()
    context.jds = frappe.get_all(
        "Job Description",
        fields=[
            "name",
            "job_title",
            "status",
            "portal_search_status",
            "location",
            "vacancies",
            "hiring_manager",
            "posting_date",
            "creation",
        ],
        filters=jd_filters,
        or_filters=jd_or_filters,
        order_by="posting_date desc, creation desc",
        limit_page_length=100,
    )

    context.departments = frappe.get_all(
        "Department", pluck="name", limit_page_length=0
    ) or []

    # Built-in JD templates — pre-fill the creation form in one click.
    templates = get_templates()
    context.templates = templates
    # JSON embedded inside an inline <script>: escape '<' so a template can
    # never break out of the script tag (e.g. via a "</script>" in text).
    context.templates_json = json.dumps(
        [
            {
                k: t.get(k)
                for k in (
                    "key",
                    "title",
                    "job_title",
                    "employment_type",
                    "location",
                    "remote_option",
                    "min_experience_years",
                    "max_experience_years",
                    "salary_range_min",
                    "salary_range_max",
                    "vacancies",
                    "required_skills",
                    "preferred_skills",
                    "qualifications",
                    "job_description_raw",
                )
            }
            for t in templates
        ]
    ).replace("<", "\\u003c")

    return context
