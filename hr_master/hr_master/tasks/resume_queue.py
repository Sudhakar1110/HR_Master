"""Resume queue processing tasks for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.utils import now_datetime


def process_resume_parsing(resume_name):
    """Background job: Parse a resume document and extract structured data."""
    try:
        resume = frappe.get_doc("Resume", resume_name)
        resume.db_set("parsing_status", "Processing")

        from hr_master.api.candidate_api import extract_text_from_file

        file_path = frappe.get_site_path(resume.resume_file.lstrip("/"))
        text = extract_text_from_file(file_path)

        if text:
            resume.db_set("raw_text", text)
            resume.db_set("parsed_text", text)
            resume.db_set("parsing_status", "Completed")
            resume.db_set("parsed_on", now_datetime())

            # Extract skills from parsed text
            from hr_master.hr_master.doctype.skill.skill import extract_skills_from_text
            skills = extract_skills_from_text(text)
            resume = frappe.get_doc("Resume", resume_name)
            for skill_name in skills:
                resume.append("resume_skills", {"skill": skill_name, "extracted_from": "Resume Parsing"})
            resume.save(ignore_permissions=True)
        else:
            resume.db_set("parsing_status", "Failed")
            resume.db_set("parsing_error", "Unable to extract text from file")

        frappe.db.commit()

    except Exception as e:
        frappe.db.set_value("Resume", resume_name, "parsing_status", "Failed")
        frappe.db.set_value("Resume", resume_name, "parsing_error", str(e))
        frappe.log_error(message=f"Resume parsing error: {str(e)}", title="Resume Parse Error")


def process_pending_resumes():
    """Daily long: Process all pending resume parsing jobs."""
    pending = frappe.get_all("Resume", filters={"parsing_status": "Pending"}, pluck="name", limit=20)
    for resume_name in pending:
        frappe.enqueue(
            method="hr_master.tasks.resume_queue.process_resume_parsing",
            queue="long",
            timeout=300,
            resume_name=resume_name,
        )
