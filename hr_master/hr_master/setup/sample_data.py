"""Sample data creation and verification for HR Master.

Creates a sample Candidate (with skills in the Candidate Skill Detail child
table) and a sample Resume (with parsed Skills / Experience / Education /
Certifications child rows) so you can confirm that the child tables save and
reload correctly after the orphan-doctype fix.

Run on the server (as Administrator):

    cd ~/frappe-bench-v15/apps/hr_master && git pull && cd ../..
    bench --site hr.bizaxl.local migrate
    bench --site hr.bizaxl.local execute hr_master.setup.sample_data.create_sample_data

Or create only one piece / verify:

    bench --site hr.bizaxl.local execute hr_master.setup.sample_data.create_sample_candidate
    bench --site hr.bizaxl.local execute hr_master.setup.sample_data.create_sample_resume
    bench --site hr.bizaxl.local execute hr_master.setup.sample_data.verify_sample_data

The script is idempotent - running it again updates the same records instead
of creating duplicates. verify_sample_data() loads the documents back from the
database and prints every child row, asserting the row counts.
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import now_datetime

SAMPLE_EMAIL = "asha.kumar@example.com"
SAMPLE_CANDIDATE_NAME = "Asha Kumar"

# (skill display name, category). The stored name is returned by _ensure_skill
# because Skill.validate() title-cases skill_name (e.g. "MySQL" -> "Mysql").
SAMPLE_SKILLS = [
    ("Python", "Programming Language"),
    ("ERPNext", "Framework"),
    ("MySQL", "Database"),
    ("REST API", "Tool"),
    ("Communication", "Soft Skill"),
]

SAMPLE_RESUME_TEXT = (
    "Asha Kumar\n"
    "Senior Python Developer with 5+ years of experience building HR and ERP solutions.\n"
    "Core skills: Python, ERPNext, MySQL, REST API development, agile communication.\n"
    "Led a team of 4 developers delivering a recruitment management platform."
)

SAMPLE_CANDIDATE_SKILLS = [
    {"skill": "Python", "years_of_experience": 5.5, "proficiency": "Expert", "is_primary": 1},
    {"skill": "ERPNext", "years_of_experience": 4.0, "proficiency": "Advanced", "is_primary": 0},
    {"skill": "MySQL", "years_of_experience": 5.0, "proficiency": "Advanced", "is_primary": 0},
    {"skill": "REST API", "years_of_experience": 4.0, "proficiency": "Intermediate", "is_primary": 0},
]

SAMPLE_RESUME_SKILLS = [
    {"skill": "Python", "proficiency": "Expert", "years_of_experience": 5.5, "extracted_from": "Resume Parsing"},
    {"skill": "ERPNext", "proficiency": "Advanced", "years_of_experience": 4.0, "extracted_from": "Resume Parsing"},
    {"skill": "MySQL", "proficiency": "Advanced", "years_of_experience": 5.0, "extracted_from": "Resume Parsing"},
    {"skill": "REST API", "proficiency": "Intermediate", "years_of_experience": 4.0, "extracted_from": "Resume Parsing"},
]

SAMPLE_EXPERIENCES = [
    {
        "company": "TechNova Solutions",
        "title": "Senior Python Developer",
        "from_date": "2022-04-01",
        "is_current": 1,
        "location": "Chennai, India",
        "description": "Led development of a recruitment management platform (Python, ERPNext, MySQL).",
    },
    {
        "company": "CloudCore Systems",
        "title": "Python Developer",
        "from_date": "2019-06-01",
        "to_date": "2022-03-31",
        "location": "Bengaluru, India",
        "description": "Built REST APIs and database tooling for enterprise clients.",
    },
]

SAMPLE_EDUCATIONS = [
    {
        "institution": "Anna University",
        "degree": "Master's",
        "field_of_study": "Computer Science",
        "from_year": 2017,
        "to_year": 2019,
        "grade": "8.4 CGPA",
    }
]

SAMPLE_CERTIFICATIONS = [
    {
        "certification_name": "AWS Certified Developer - Associate",
        "issuing_organization": "Amazon Web Services",
        "issue_date": "2021-08-15",
        "credential_id": "AWS-DEV-2021-004217",
    }
]


def _ensure_skill(skill_name, category):
    """Create a Skill if missing and return the actual stored skill name."""
    existing = frappe.db.get_all("Skill", pluck="name")
    canonical = next((name for name in existing if name.lower() == skill_name.lower()), None)
    if canonical:
        return canonical

    doc = frappe.new_doc("Skill")
    doc.skill_name = skill_name
    doc.category = category
    doc.is_active = 1
    doc.insert(ignore_permissions=True)
    return doc.name


def _canonical_skills():
    """Return {display_name: stored_skill_name} for the sample skills."""
    return {display: _ensure_skill(display, category) for display, category in SAMPLE_SKILLS}


def _ensure_sample_file():
    """Create (idempotently) a small private text file and return its URL."""
    file_name = "Sample_Asha_Kumar_Resume.txt"
    existing = frappe.db.get_value("File", {"file_name": file_name}, "file_url")
    if existing:
        return existing

    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name,
            "is_private": 1,
            "content": SAMPLE_RESUME_TEXT,
        }
    )
    file_doc.insert(ignore_permissions=True)
    return file_doc.file_url


def create_sample_candidate(quiet=False):
    """Create (or update) the sample Candidate with skills in the child table."""
    canonical = _canonical_skills()

    existing = frappe.db.get_value("Candidate", {"email": SAMPLE_EMAIL}, "name")
    if existing:
        cand = frappe.get_doc("Candidate", existing)
        action = "updated"
    else:
        cand = frappe.new_doc("Candidate")
        cand.email = SAMPLE_EMAIL
        action = "created"

    cand.candidate_name = SAMPLE_CANDIDATE_NAME
    cand.phone = "+91 98765 43210"
    cand.current_company = "TechNova Solutions"
    cand.current_title = "Senior Python Developer"
    cand.total_experience_years = 5.5
    cand.highest_education = "Master's"
    cand.field_of_study = "Computer Science"
    cand.college = "Anna University"
    cand.graduation_year = 2019
    cand.source = "LinkedIn"
    cand.languages = "English, Tamil"
    cand.certifications = "AWS Certified Developer - Associate"
    cand.resume_text = SAMPLE_RESUME_TEXT
    cand.notes = "Sample candidate created via hr_master.setup.sample_data"

    # rebuild child rows
    cand.set("candidate_skills", [])
    for row in SAMPLE_CANDIDATE_SKILLS:
        cand.append(
            "candidate_skills",
            {
                "skill": canonical[row["skill"]],
                "years_of_experience": row["years_of_experience"],
                "proficiency": row["proficiency"],
                "is_primary": row["is_primary"],
            },
        )

    cand.save(ignore_permissions=True)

    reloaded = frappe.get_doc("Candidate", cand.name)
    rows = reloaded.candidate_skills
    if not quiet:
        print("Candidate {0} ({1}) with {2} skill row(s) in child table".format(cand.name, action, len(rows)))
        for r in rows:
            print("  - {0} | {1} | {2} yrs | primary={3}".format(r.skill, r.proficiency, r.years_of_experience, r.is_primary))
    assert len(rows) == len(SAMPLE_CANDIDATE_SKILLS), (
        "Expected {0} candidate skill rows after reload, got {1}".format(len(SAMPLE_CANDIDATE_SKILLS), len(rows))
    )
    if not quiet:
        print("RELOAD_OK: Candidate child table persisted and reloaded.")
    return cand.name


def _print_resume(reloaded):
    """Print all child rows of a Resume and assert the counts."""
    print("Resume {0} (docstatus={1}, parsing_status={2}) child tables:".format(
        reloaded.name, reloaded.docstatus, reloaded.parsing_status
    ))
    print("  Skills ({0}):".format(len(reloaded.resume_skills)))
    for r in reloaded.resume_skills:
        print("    - {0} | {1} | {2} yrs | via {3}".format(r.skill, r.proficiency, r.years_of_experience, r.extracted_from))
    print("  Experience ({0}):".format(len(reloaded.resume_experiences)))
    for r in reloaded.resume_experiences:
        print("    - {0} @ {1} ({2} - {3}) current={4}".format(
            r.title, r.company, r.from_date, r.to_date or "-", r.is_current
        ))
    print("  Education ({0}):".format(len(reloaded.resume_educations)))
    for r in reloaded.resume_educations:
        print("    - {0} in {1} @ {2} ({3}-{4})".format(r.degree, r.field_of_study, r.institution, r.from_year, r.to_year))
    print("  Certifications ({0}):".format(len(reloaded.resume_certifications)))
    for r in reloaded.resume_certifications:
        print("    - {0} | {1} | {2}".format(r.certification_name, r.issuing_organization, r.issue_date))

    assert len(reloaded.resume_skills) == len(SAMPLE_RESUME_SKILLS), "Resume Skills count mismatch"
    assert len(reloaded.resume_experiences) == len(SAMPLE_EXPERIENCES), "Resume Experience count mismatch"
    assert len(reloaded.resume_educations) == len(SAMPLE_EDUCATIONS), "Resume Education count mismatch"
    assert len(reloaded.resume_certifications) == len(SAMPLE_CERTIFICATIONS), "Resume Certification count mismatch"
    print("RELOAD_OK: Resume child tables persisted and reloaded.")
    return reloaded.name


def create_sample_resume():
    """Create (or rebuild) the submitted sample Resume with parsed child sections."""
    canonical = _canonical_skills()
    cand_name = frappe.db.get_value("Candidate", {"email": SAMPLE_EMAIL}, "name")
    if not cand_name:
        cand_name = create_sample_candidate(quiet=True)
    file_url = _ensure_sample_file()

    # Rebuild the sample resume from scratch so re-runs stay clean.
    old = frappe.db.get_value("Resume", {"candidate": cand_name, "is_latest": 1}, "name")
    if old:
        old_doc = frappe.get_doc("Resume", old)
        if old_doc.docstatus == 1:
            old_doc.cancel()
        frappe.delete_doc("Resume", old, force=1)
        print("Removed previous sample resume {0}".format(old))

    resume = frappe.new_doc("Resume")
    resume.candidate = cand_name
    resume.candidate_name = frappe.db.get_value("Candidate", cand_name, "candidate_name")
    resume.resume_file = file_url
    resume.raw_text = SAMPLE_RESUME_TEXT
    resume.parsed_text = SAMPLE_RESUME_TEXT
    resume.parsing_status = "Completed"
    resume.parsed_on = now_datetime()
    resume.version = 1
    resume.is_latest = 1

    for row in SAMPLE_RESUME_SKILLS:
        resume.append(
            "resume_skills",
            {
                "skill": canonical[row["skill"]],
                "proficiency": row["proficiency"],
                "years_of_experience": row["years_of_experience"],
                "extracted_from": row["extracted_from"],
            },
        )
    for exp in SAMPLE_EXPERIENCES:
        resume.append("resume_experiences", dict(exp))
    for edu in SAMPLE_EDUCATIONS:
        resume.append("resume_educations", dict(edu))
    for cert in SAMPLE_CERTIFICATIONS:
        resume.append("resume_certifications", dict(cert))

    resume.save(ignore_permissions=True)
    resume.submit()

    # Cross-link the resume file onto the candidate as well.
    cand = frappe.get_doc("Candidate", cand_name)
    cand.resume_attachment = file_url
    cand.save(ignore_permissions=True)

    return _print_resume(resume.name)


def create_sample_data():
    """Create the sample Candidate and Resume, then verify both."""
    cand_name = create_sample_candidate()
    resume_name = create_sample_resume()
    print("DONE. Candidate: {0} | Resume: {1}".format(cand_name, resume_name))
    return {"candidate": cand_name, "resume": resume_name}


def verify_sample_data():
    """Load the sample Candidate + Resume from the DB and print every child row."""
    cand_name = frappe.db.get_value("Candidate", {"email": SAMPLE_EMAIL}, "name")
    if not cand_name:
        print("No sample Candidate found. Run create_sample_data first.")
        return

    cand = frappe.get_doc("Candidate", cand_name)
    print("Candidate {0}: {1} skill row(s)".format(cand.name, len(cand.candidate_skills)))
    for r in cand.candidate_skills:
        print("  - {0} | {1} | {2} yrs | primary={3}".format(r.skill, r.proficiency, r.years_of_experience, r.is_primary))

    resume_name = frappe.db.get_value("Resume", {"candidate": cand_name, "is_latest": 1}, "name")
    if not resume_name:
        print("No sample Resume found for {0}. Run create_sample_resume first.".format(cand_name))
        return
    _print_resume(frappe.get_doc("Resume", resume_name))
