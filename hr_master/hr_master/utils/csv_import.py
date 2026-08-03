"""CSV Candidate Import Utility for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _
import csv
import json
import io


def _valid_select(doctype, fieldname, value, default=""):
    """Return a value that passes Select validation for a doctype field.

    Dropdown fields reject anything that is not one of their options (e.g.
    "CSV Import" on source, or a typo like "Bachelors" on highest_education),
    which would otherwise fail the whole row. Unknown values fall back to
    ``default``; empty values stay empty.
    """
    value = (value or "").strip()
    if not value:
        return ""
    try:
        meta = frappe.get_meta(doctype)
        field = meta.get_field(fieldname)
        options = [o.strip() for o in (field.options or "").split("\n") if o.strip()]
    except Exception:
        options = []
    if options and value in options:
        return value
    return default


def _valid_source(value):
    """Return a Candidate.source value that passes Select validation."""
    return _valid_select("Candidate", "source", value, default="Other")


def _to_float(value):
    """Coerce a CSV cell to a float (0 for empty/invalid)."""
    try:
        return float(value) if value not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


def _to_int(value):
    """Coerce a CSV cell to an int (0 for empty/invalid)."""
    try:
        return int(float(value)) if value not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


@frappe.whitelist()
def import_candidates_from_csv(file_url, job_description=None, source="CSV Import"):
    """Import candidates from a CSV file.

    Columns (only candidate_name is required): candidate_name, email, phone,
    current_title, current_company, total_experience_years, location,
    current_salary, expected_salary, notice_period_days, source, source_url,
    linkedin_url, naukri_url, other_portal_url, highest_education,
    field_of_study, college, graduation_year, skills, languages,
    certifications, resume_text, status, blacklisted, notes
    """
    try:
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        content = file_doc.get_content()
        decoded = content.decode("utf-8-sig") if isinstance(content, bytes) else content
        reader = csv.DictReader(io.StringIO(decoded))

        results = {"imported": 0, "duplicates": 0, "errors": [], "candidates": []}
        required_fields = ["candidate_name"]
        source = _valid_source(source)

        for row in reader:
            try:
                missing = [f for f in required_fields if not row.get(f)]
                if missing:
                    results["errors"].append(f"Row {reader.line_num}: Missing fields: {', '.join(missing)}")
                    continue

                email = row.get("email", "").strip().lower()
                if email and frappe.db.exists("Candidate", {"email": email}):
                    results["duplicates"] += 1
                    continue

                candidate = frappe.new_doc("Candidate")
                candidate.candidate_name = row.get("candidate_name", "").strip()
                candidate.email = email
                candidate.phone = row.get("phone", "").strip()
                candidate.current_title = row.get("current_title", "").strip()
                candidate.current_company = row.get("current_company", "").strip()
                candidate.total_experience_years = _to_float(row.get("total_experience_years"))
                candidate.location = row.get("location", "").strip()
                candidate.current_salary = _to_float(row.get("current_salary"))
                candidate.expected_salary = _to_float(row.get("expected_salary"))
                candidate.notice_period_days = _to_int(row.get("notice_period_days"))

                # Source: a per-row "source" column overrides the page source.
                candidate.source = _valid_source((row.get("source") or "").strip() or source)
                candidate.source_url = row.get("source_url", "").strip()
                candidate.linkedin_url = row.get("linkedin_url", "").strip()
                candidate.naukri_url = row.get("naukri_url", "").strip()
                candidate.other_portal_url = row.get("other_portal_url", "").strip()

                # Education
                candidate.highest_education = _valid_select(
                    "Candidate", "highest_education", row.get("highest_education")
                )
                candidate.field_of_study = row.get("field_of_study", "").strip()
                candidate.college = row.get("college", "").strip()
                candidate.graduation_year = _to_int(row.get("graduation_year"))

                # Skills / languages / certifications
                candidate.languages = row.get("languages", "")
                candidate.certifications = row.get("certifications", "")

                # Resume / notes / status
                candidate.resume_text = row.get("resume_text", "")
                candidate.notes = row.get("notes", "")
                status_val = (row.get("status") or "").strip()
                candidate.status = _valid_select(
                    "Candidate", "status", status_val, default="New"
                ) or "New"
                blacklisted = (row.get("blacklisted") or "").strip().lower()
                candidate.blacklisted = 1 if blacklisted in ("1", "true", "yes", "y") else 0

                # Parse skills from column
                skills_str = row.get("skills", "")
                if skills_str:
                    for skill_name in [s.strip() for s in skills_str.split(",") if s.strip()]:
                        if frappe.db.exists("Skill", skill_name):
                            candidate.append("candidate_skills", {
                                "skill": skill_name,
                                "proficiency": "Intermediate"
                            })

                candidate.save(ignore_permissions=True)
                results["imported"] += 1
                results["candidates"].append(candidate.name)

                # Link to JD if provided
                if job_description:
                    link_candidate_to_jd(job_description, candidate.name)

            except Exception as e:
                results["errors"].append(f"Row {reader.line_num}: {str(e)}")

        frappe.db.commit()
        log_import_activity(results)

        return {
            "status": "success",
            "imported": results["imported"],
            "duplicates": results["duplicates"],
            "errors": results["errors"],
            "candidates": results["candidates"]
        }

    except Exception as e:
        frappe.log_error(message=f"CSV import error: {str(e)}", title="CSV Import Error")
        return {"status": "error", "message": str(e)}


def link_candidate_to_jd(jd_name, candidate_name):
    """Create a candidate ranking placeholder for the linked JD."""
    jd = frappe.get_doc("Job Description", jd_name)
    ranking = frappe.new_doc("Candidate Ranking")
    ranking.job_description = jd_name
    ranking.job_title = jd.job_title
    ranking.candidate = candidate_name
    ranking.candidate_name = frappe.db.get_value("Candidate", candidate_name, "candidate_name")
    ranking.status = "Pending"
    ranking.save(ignore_permissions=True)


def log_import_activity(results):
    """Log import activity."""
    from hr_master.hr_master.doctype.candidate_activity_log.candidate_activity_log import log_activity
    for c_name in results.get("candidates", []):
        log_activity(
            candidate=c_name,
            activity_type="Created",
            description=f"Imported via CSV (Source: CSV Import)",
            reference_doctype="Candidate",
            reference_name=c_name
        )
