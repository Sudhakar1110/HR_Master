"""Candidate API for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _


@frappe.whitelist()
def parse_resume(candidate_name, file_url):
    """Parse resume file and extract text, skills and structured profile.

    Uses the configured LLM (if AI is enabled) for rich extraction — skills
    with proficiency + years, education, certifications, current role — and
    falls back to the rule-based skill extractor when AI is off or fails.
    """
    try:
        candidate = frappe.get_doc("Candidate", candidate_name)
        if not candidate:
            return {"status": "error", "message": _("Candidate not found")}

        resume_text = ""
        # Download and parse the file
        if file_url:
            file_path = frappe.get_site_path(file_url.lstrip("/"))
            resume_text = extract_text_from_file(file_path)

        # Rule-based fallback skill extraction
        rule_skills = []
        if resume_text:
            from hr_master.hr_master.doctype.skill.skill import extract_skills_from_text

            rule_skills = extract_skills_from_text(resume_text)

        # LLM structured extraction (when AI is configured)
        from hr_master.utils.llm import is_llm_configured

        structured = {}
        llm_skills = []
        if resume_text:
            structured = _llm_extract_resume_profile(resume_text)
            llm_skills = structured.get("skills") or []

        # Prefer LLM skills; fall back to rule-based list
        skills = [s.get("skill") for s in llm_skills if s.get("skill")] or rule_skills

        return {
            "status": "success",
            "resume_text": resume_text,
            "skills": skills,
            "ai_enabled": is_llm_configured(),
            "structured": structured,
        }

    except Exception as e:
        frappe.log_error(
            message=f"Resume parsing error: {str(e)}",
            title="Resume Parse Error",
        )
        return {"status": "error", "message": str(e)}


def _llm_extract_resume_profile(resume_text):
    """Ask the configured LLM to extract a structured profile from resume text."""
    from hr_master.utils.llm import call_llm_json, is_llm_configured

    if not is_llm_configured():
        return {}

    system = (
        "You are an expert resume parser for a recruiting system. "
        "Extract only facts present in the resume. Reply with JSON only, no prose."
    )
    prompt = (
        "Extract a structured profile from this resume. Return a JSON object with keys:\n"
        '- "skills": array of {\"skill\": string, \"proficiency\": "Beginner|Intermediate|Advanced|Expert", \"years\": number}\n'
        '- "highest_education": string (e.g. Bachelor's, Master's, PhD)\n'
        '- "certifications": array of strings\n'
        '- "current_title": string, "current_company": string\n'
        '- "total_experience_years": number\n'
        '- "location": string\n'
        '- "notice_period_days": number or null\n\n'
        "Resume text:\n{0}".format((resume_text or "")[:9000])
    )
    return call_llm_json(prompt, system=system, max_tokens=1200, temperature=0.1)


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
