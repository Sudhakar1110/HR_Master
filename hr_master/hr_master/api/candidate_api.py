"""Candidate API for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _


@frappe.whitelist()
def parse_resume(candidate_name, file_url):
    """Parse resume file and extract text and skills."""
    try:
        candidate = frappe.get_doc("Candidate", candidate_name)
        if not candidate:
            return {"status": "error", "message": _("Candidate not found")}

        resume_text = ""
        # Download and parse the file
        if file_url:
            file_path = frappe.get_site_path(file_url.lstrip("/"))
            resume_text = extract_text_from_file(file_path)

        # Extract skills from resume text
        skills = []
        if resume_text:
            from hr_master.doctype.skill.skill import extract_skills_from_text

            skills = extract_skills_from_text(resume_text)

        return {
            "status": "success",
            "resume_text": resume_text,
            "skills": skills,
        }

    except Exception as e:
        frappe.log_error(
            message=f"Resume parsing error: {str(e)}",
            title="Resume Parse Error",
        )
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_candidate_details(candidate_name):
    """Get detailed candidate information."""
    candidate = frappe.get_doc("Candidate", candidate_name)
    if not candidate:
        return {"status": "error", "message": _("Candidate not found")}

    # Get rankings
    rankings = frappe.get_all(
        "Candidate Ranking",
        filters={"candidate": candidate_name},
        fields=[
            "job_description",
            "job_title",
            "total_match_score",
            "ranking_order",
            "status",
            "evaluation_date",
        ],
        order_by="evaluation_date desc",
    )

    # Get interviews
    interviews = frappe.get_all(
        "Interview Schedule",
        filters={"candidate": candidate_name},
        fields=[
            "name",
            "scheduled_date",
            "scheduled_time",
            "interview_type",
            "interview_round",
            "status",
            "result",
        ],
        order_by="scheduled_date desc",
    )

    return {
        "candidate": candidate,
        "rankings": rankings,
        "interviews": interviews,
    }


@frappe.whitelist()
def bulk_update_candidate_status(candidates, status):
    """Bulk update candidate statuses."""
    import json

    if isinstance(candidates, str):
        candidates = json.loads(candidates)

    updated = 0
    for candidate_name in candidates:
        try:
            frappe.db.set_value("Candidate", candidate_name, "status", status)
            updated += 1
        except Exception:
            continue

    frappe.db.commit()
    return {
        "status": "success",
        "updated_count": updated,
        "message": _("{0} candidates updated to {1}").format(updated, status),
    }


def extract_text_from_file(file_path):
    """Extract text content from uploaded file (PDF, DOCX, TXT)."""
    import os

    if not os.path.exists(file_path):
        return ""

    text = ""
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

        elif ext == ".pdf":
            try:
                from PyPDF2 import PdfReader

                reader = PdfReader(file_path)
                for page in reader.pages:
                    text += page.extract_text() or ""
            except ImportError:
                # Fallback to pdftotext command line
                import subprocess

                result = subprocess.run(
                    ["pdftotext", file_path, "-"],
                    capture_output=True,
                    text=True,
                )
                text = result.stdout

        elif ext == ".docx":
            try:
                from docx import Document

                doc = Document(file_path)
                text = "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                pass

    except Exception as e:
        frappe.log_error(
            message=f"File extraction error: {str(e)}",
            title="File Extraction Error",
        )

    return text
