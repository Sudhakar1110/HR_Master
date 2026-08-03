"""CSV Candidate Import Utility for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _
import csv
import json
import io


def _valid_source(value):
    """Return a Candidate.source value that passes Select validation.

    The Candidate doctype's ``source`` field is a Select; assigning a value
    that is not one of its options (e.g. a custom "CSV Import" label on a
    site where the option has not been synced yet) fails validation and
    rejects the whole row. Unknown values fall back to "Other" so imports
    never break.
    """
    value = (value or "").strip()
    if not value:
        return ""
    try:
        meta = frappe.get_meta("Candidate")
        field = meta.get_field("source")
        options = [o.strip() for o in (field.options or "").split("\n") if o.strip()]
    except Exception:
        options = []
    if options and value in options:
        return value
    return "Other"


@frappe.whitelist()
def import_candidates_from_csv(file_url, job_description=None, source="CSV Import"):
    """Import candidates from a CSV file.

    Expected columns: candidate_name, email, phone, current_title, current_company,
                      total_experience_years, highest_education, skills, resume_text,
                      location, current_salary, expected_salary, notice_period_days
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
                candidate.source = source
                candidate.source_url = row.get("source_url", "")
                candidate.highest_education = row.get("highest_education", "").strip()

                exp = row.get("total_experience_years", "0")
                try:
                    candidate.total_experience_years = float(exp) if exp else 0
                except ValueError:
                    candidate.total_experience_years = 0

                candidate.location = row.get("location", "").strip()

                current_salary = row.get("current_salary", "")
                try:
                    candidate.current_salary = float(current_salary) if current_salary else 0
                except ValueError:
                    candidate.current_salary = 0

                expected_salary = row.get("expected_salary", "")
                try:
                    candidate.expected_salary = float(expected_salary) if expected_salary else 0
                except ValueError:
                    candidate.expected_salary = 0

                notice_period = row.get("notice_period_days", "")
                try:
                    candidate.notice_period_days = int(float(notice_period)) if notice_period else 0
                except ValueError:
                    candidate.notice_period_days = 0

                candidate.resume_text = row.get("resume_text", "")
                candidate.status = "New"

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
