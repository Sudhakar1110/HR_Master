"""Advanced Candidate Search Utility for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _
import json


@frappe.whitelist()
def advanced_candidate_search(search_text=None, filters=None, sort_by="total_match_score",
                               sort_order="desc", page=1, page_size=25):
    """Advanced full-text search for candidates with multiple filter combinations."""
    try:
        if isinstance(filters, str):
            filters = frappe.parse_json(filters) if filters else {}

        conditions = []
        params = {}

        if search_text:
            conditions.append("""
                (c.candidate_name LIKE %(search)s
                OR c.email LIKE %(search)s
                OR c.phone LIKE %(search)s
                OR c.current_title LIKE %(search)s
                OR c.current_company LIKE %(search)s
                OR c.resume_text LIKE %(search)s
                OR c.parsed_skills_from_resume LIKE %(search)s)
            """)
            params["search"] = f"%{search_text}%"

        # Apply additional filters
        if filters:
            filter_map = {
                "status": ("c.status", "="),
                "source": ("c.source", "="),
                "source_url": ("c.source_url", "="),
                "location": ("c.location", "="),
                "current_title": ("c.current_title", "like"),
                "current_company": ("c.current_company", "like"),
                "highest_education": ("c.highest_education", "="),
                "min_experience": ("c.total_experience_years", ">="),
                "max_experience": ("c.total_experience_years", "<="),
                "min_score": ("c.total_match_score", ">="),
                "max_score": ("c.total_match_score", "<="),
                "min_current_salary": ("c.current_salary", ">="),
                "max_current_salary": ("c.current_salary", "<="),
                "min_expected_salary": ("c.expected_salary", ">="),
                "max_expected_salary": ("c.expected_salary", "<="),
                "max_notice_period": ("c.notice_period_days", "<="),
                "created_after": ("c.creation", ">="),
                "created_before": ("c.creation", "<="),
                "owner": ("c.owner", "=")
            }

            for filter_key, (field, operator) in filter_map.items():
                value = filters.get(filter_key)
                if value is not None and value != "":
                    param_key = f"f_{filter_key}"
                    if operator == "like":
                        conditions.append(f"{field} LIKE %({param_key})s")
                        params[param_key] = f"%{value}%"
                    else:
                        conditions.append(f"{field} {operator} %({param_key})s")
                        params[param_key] = value

        # Skill filter (requires join)
        skill_filters = filters.get("skills", [])
        if isinstance(skill_filters, str):
            skill_filters = [s.strip() for s in skill_filters.split(",") if s.strip()]

        if skill_filters:
            skill_conditions = " OR ".join([f"cs.skill = %(skill_{i})s" for i in range(len(skill_filters))])
            conditions.append(f"""
                c.name IN (
                    SELECT cs.parent FROM `tabCandidate Skill Detail` cs
                    WHERE ({skill_conditions})
                )
            """)
            for i, skill in enumerate(skill_filters):
                params[f"skill_{i}"] = skill

        # JD filter
        jd_name = filters.get("job_description")
        if jd_name:
            conditions.append("""
                c.name IN (
                    SELECT cr.candidate FROM `tabCandidate Ranking` cr
                    WHERE cr.job_description = %(jd_name)s
                )
            """)
            params["jd_name"] = jd_name

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Validate sort
        allowed_sort_fields = [
            "candidate_name", "total_match_score", "creation", "modified",
            "status", "total_experience_years", "current_title", "current_company"
        ]
        if sort_by not in allowed_sort_fields:
            sort_by = "total_match_score"
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"

        # Count total
        count_query = f"SELECT COUNT(*) FROM `tabCandidate` c WHERE {where_clause}"
        total = frappe.db.sql(count_query, params)[0][0]

        # Fetch results with pagination
        offset = (page - 1) * page_size
        query = f"""
            SELECT c.name, c.candidate_name, c.email, c.phone, c.status,
                   c.current_title, c.current_company, c.total_experience_years,
                   c.highest_education, c.total_match_score, c.source,
                   c.location, c.creation, c.owner
            FROM `tabCandidate` c
            WHERE {where_clause}
            ORDER BY c.{sort_by} {sort_order}
            LIMIT %(limit)s OFFSET %(offset)s
        """
        params["limit"] = page_size
        params["offset"] = offset

        results = frappe.db.sql(query, params, as_dict=True)

        return {
            "status": "success",
            "candidates": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size)
        }

    except Exception as e:
        frappe.log_error(message=f"Advanced search error: {str(e)}", title="Search Error")
        return {"status": "error", "message": str(e)}
