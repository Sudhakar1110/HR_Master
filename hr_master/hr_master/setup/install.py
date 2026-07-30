"""Installation setup for HR Master - creates seed data and initial configuration"""

from __future__ import unicode_literals

import os
import json

import frappe
from frappe import _
from frappe.modules.import_file import import_file_by_path


def after_install():
    """Run after app installation."""
    create_seed_data()
    create_default_workspace()
    set_default_config()
    sync_all_resources()


def after_migrate():
    """Run after database migration."""
    create_seed_data()
    sync_all_resources()


def create_seed_data():
    """Create initial seed data for the app."""
    create_roles()
    create_departments()
    create_skills()


def create_roles():
    """Create HR Master roles if they don't exist."""
    roles = [
        {
            "role_name": "HR Master Admin",
            "desk_access": 1,
            "role_type": "System",
        },
        {
            "role_name": "HR Master Recruiter",
            "desk_access": 1,
            "role_type": "System",
        },
        {
            "role_name": "HR Master Hiring Manager",
            "desk_access": 1,
            "role_type": "System",
        },
        {
            "role_name": "HR Master Viewer",
            "desk_access": 1,
            "role_type": "System",
        },
    ]

    for role_data in roles:
        if not frappe.db.exists("Role", role_data["role_name"]):
            role = frappe.new_doc("Role")
            role.update(role_data)
            role.save(ignore_permissions=True)

    frappe.db.commit()


def create_departments():
    """Create common departments if they don't exist."""
    # Get default company from ERPNext
    # During after_migrate, there's no user session, so check all sources
    default_company = (
        frappe.defaults.get_user_default("Company")
        or frappe.db.get_single_value("Global Defaults", "default_company")
        or frappe.db.get_value("Company", {}, "name")
    )

    if not default_company:
        frappe.logger().info(
            "HR Master: No company found. Skipping department creation."
        )
        return

    departments = [
        "Engineering",
        "Product",
        "Design",
        "Marketing",
        "Sales",
        "Human Resources",
        "Finance",
        "Operations",
        "Legal",
        "Customer Support",
    ]

    for dept_name in departments:
        # Check by department_name field — ERPNext uses autonaming (e.g. "Marketing - HM")
        # so the document name won't match the plain department_name
        if not frappe.db.get_value("Department", {"department_name": dept_name}, "name"):
            dept = frappe.new_doc("Department")
            dept.department_name = dept_name
            dept.company = default_company
            dept.is_active = 1
            dept.save(ignore_permissions=True)

    frappe.db.commit()


def create_skills():
    """Create common skills if they don't exist."""
    skills = [
        # Programming Languages
        ("Python", "Programming Language"),
        ("JavaScript", "Programming Language"),
        ("TypeScript", "Programming Language"),
        ("Java", "Programming Language"),
        ("C++", "Programming Language"),
        ("Go", "Programming Language"),
        ("Rust", "Programming Language"),
        ("Ruby", "Programming Language"),
        ("PHP", "Programming Language"),
        ("SQL", "Programming Language"),
        # Frameworks
        ("React", "Framework"),
        ("Angular", "Framework"),
        ("Vue.js", "Framework"),
        ("Django", "Framework"),
        ("Flask", "Framework"),
        ("Node.js", "Framework"),
        ("Express.js", "Framework"),
        ("Spring Boot", "Framework"),
        (".NET", "Framework"),
        ("Frappe Framework", "Framework"),
        # Databases
        ("PostgreSQL", "Database"),
        ("MySQL", "Database"),
        ("MongoDB", "Database"),
        ("Redis", "Database"),
        ("Elasticsearch", "Database"),
        # Cloud & DevOps
        ("AWS", "Cloud"),
        ("Azure", "Cloud"),
        ("GCP", "Cloud"),
        ("Docker", "DevOps"),
        ("Kubernetes", "DevOps"),
        ("CI/CD", "DevOps"),
        ("Terraform", "DevOps"),
        # Soft Skills
        ("Leadership", "Soft Skill"),
        ("Communication", "Soft Skill"),
        ("Project Management", "Soft Skill"),
        ("Team Management", "Soft Skill"),
        # Tools
        ("Git", "Tool"),
        ("Jira", "Tool"),
        ("Confluence", "Tool"),
        ("Figma", "Tool"),
        # Domain Knowledge
        ("Machine Learning", "Domain Knowledge"),
        ("Data Science", "Domain Knowledge"),
        ("Cybersecurity", "Domain Knowledge"),
        ("Blockchain", "Domain Knowledge"),
    ]

    for skill_name, category in skills:
        if not frappe.db.exists("Skill", skill_name):
            skill = frappe.new_doc("Skill")
            skill.skill_name = skill_name
            skill.category = category
            skill.is_active = 1
            skill.save(ignore_permissions=True)

    frappe.db.commit()


def create_default_workspace():
    """Ensure default workspace is created."""
    if not frappe.db.exists("Workspace", "HR Master"):
        workspace = frappe.new_doc("Workspace")
        workspace.label = "HR Master"
        workspace.module = "HR Master"
        workspace.icon = "hr"
        workspace.indicator_color = "blue"
        workspace.public = 1
        workspace.save(ignore_permissions=True)

    frappe.db.commit()


def sync_all_resources():
    """
    Explicitly import all DocType, Report, Workspace, Number Card,
    Notification, Print Format, and Workflow JSON files from disk.

    This bypasses Frappe's auto-discovery mechanism which may fail
    to find the JSON files due to path resolution issues.
    """
    # Get the module root directory (parent of setup/)
    module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    resource_dirs = {
        "doctype": "DocType",
        "report": "Report",
        "workspace": "Workspace",
        "number_card": "Number Card",
        "notification": "Notification",
        "print_format": "Print Format",
        "letter_head": "Letter Head",
        "workflow": "Workflow",
        "email_template": "Email Template",
    }

    for subdir, label in resource_dirs.items():
        resource_path = os.path.join(module_root, subdir)
        if not os.path.exists(resource_path):
            continue

        if subdir == "workspace":
            # Workspaces are nested: workspace/{name}/{name}.json
            for ws_dir in os.listdir(resource_path):
                ws_path = os.path.join(resource_path, ws_dir)
                if os.path.isdir(ws_path):
                    for f in os.listdir(ws_path):
                        if f.endswith(".json"):
                            json_path = os.path.join(ws_path, f)
                            _import_json(json_path, label)
        else:
            # Standard: subdir/{name}/{name}.json
            for item_dir in os.listdir(resource_path):
                item_path = os.path.join(resource_path, item_dir)
                if os.path.isdir(item_path):
                    json_file = f"{item_dir}.json"
                    json_path = os.path.join(item_path, json_file)
                    if os.path.exists(json_path):
                        _import_json(json_path, label)


def _import_json(json_path, label):
    """Safely import a single JSON file as a Frappe document."""
    try:
        # Skip if the doctype already exists (avoid duplicates)
        with open(json_path, "r") as f:
            doc_data = json.load(f)

        doctype_name = doc_data.get("doctype", "")
        doc_name = doc_data.get("name", "")

        if doctype_name and doc_name:
            if frappe.db.exists(doctype_name, doc_name):
                return  # Already exists, skip

        import_file_by_path(json_path, force=True)
        frappe.db.commit()
    except Exception as e:
        frappe.logger().debug(
            f"HR Master: Skipped importing {json_path} - {str(e)}"
        )


def set_default_config():
    """Set default configuration values."""
    config = frappe.get_single("Job Portal Config")
    if not config.get("__onload"):
        config.auto_search_enabled = 0
        config.auto_shortlist_threshold = 80
        config.max_candidates_per_search = 50
        config.search_delay_seconds = 2
        config.default_country = "India"
        config.notify_on_high_match = 1
        config.notify_on_search_complete = 0
        config.email_notifications = 1
        config.desktop_notifications = 1
        config.save(ignore_permissions=True)

    frappe.db.commit()

    # Set default Recruitment Settings
    rs = frappe.get_single("Recruitment Settings")
    if not rs.get("__onload"):
        rs.auto_parse_resumes = 1
        rs.max_resume_size_kb = 10240
        rs.allowed_file_types = "pdf,docx,txt"
        rs.enable_duplicate_detection = 1
        rs.duplicate_threshold = 85
        rs.notify_on_new_candidate = 1
        rs.notify_on_offer_acceptance = 1
        rs.daily_digest_enabled = 1
        rs.weekly_report_enabled = 1
        rs.enable_audit_logging = 1
        rs.enable_rate_limiting = 0
        rs.max_api_requests_per_minute = 60
        rs.session_timeout_minutes = 60
        rs.require_approval_for_offers = 1
        rs.save(ignore_permissions=True)

    frappe.db.commit()

    # Create default Email Templates
    create_default_email_templates()


def create_default_email_templates():
    """Create default email templates if they don't exist."""
    templates = [
        {
            "template_name": "Interview Invitation",
            "template_type": "Interview Invitation",
            "subject": "Interview Invitation - {{ job_title }} at {{ company_name }}",
            "message_html": "<h3>Dear {{ candidate_name }},</h3><p>We are pleased to invite you for an interview for the position of <strong>{{ job_title }}</strong>.</p><p><strong>Date:</strong> {{ scheduled_date }}<br><strong>Time:</strong> {{ scheduled_time }}<br><strong>Mode:</strong> {{ interview_link }}</p><p>Best regards,<br>{{ recruiter_name }}</p>",
        },
        {
            "template_name": "Offer Letter",
            "template_type": "Offer Letter",
            "subject": "Offer of Employment - {{ job_title }} at {{ company_name }}",
            "message_html": "<h3>Dear {{ candidate_name }},</h3><p>Congratulations! We are pleased to offer you the position of <strong>{{ job_title }}</strong>.</p><p>Please find the offer letter attached. Kindly review and respond at your earliest convenience.</p><p>Best regards,<br>{{ recruiter_name }}</p>",
        },
        {
            "template_name": "Candidate Rejection",
            "template_type": "Custom",
            "subject": "Update on your application for {{ job_title }}",
            "message_html": "<h3>Dear {{ candidate_name }},</h3><p>Thank you for your interest in the <strong>{{ job_title }}</strong> position.</p><p>After careful consideration, we have decided to move forward with other candidates. We wish you the best in your job search.</p><p>Best regards,<br>{{ recruiter_name }}</p>",
        },
    ]

    for tpl in templates:
        if not frappe.db.exists("Email Template Config", tpl["template_name"]):
            doc = frappe.new_doc("Email Template Config")
            doc.update(tpl)
            doc.is_active = 1
            doc.use_html = 1
            doc.save(ignore_permissions=True)

    frappe.db.commit()
