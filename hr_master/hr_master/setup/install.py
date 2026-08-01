"""Installation setup for HR Master - creates seed data and initial configuration"""

from __future__ import unicode_literals

import os
import json

import frappe
from frappe.modules.import_file import import_file_by_path


def after_install():
    """Run after app installation."""
    # Register the module, create the workflow master records the workflow
    # fixture links to, then import all standard resources so every later
    # step can rely on doctypes, reports, workspaces, number cards etc.
    # existing in the DB.
    _run_phase("ensure_module_def", ensure_module_def)
    _run_phase("create_workflow_masters", create_workflow_masters)
    _run_phase("sync_all_resources", sync_all_resources)
    _run_phase("create_seed_data", create_seed_data)
    _run_phase("set_default_config", set_default_config)


def after_migrate():
    """Run after database migration."""
    _run_phase("ensure_module_def", ensure_module_def)
    _run_phase("create_workflow_masters", create_workflow_masters)
    _run_phase("sync_all_resources", sync_all_resources)
    _run_phase("create_seed_data", create_seed_data)
    _run_phase("set_default_config", set_default_config)


def ensure_module_def():
    """Ensure the 'HR Master' Module Def record exists and that the runtime
    module maps can resolve it.

    Frappe resolves modules (controller imports, native migrate sync) via
    ``frappe.local.module_app``, which is built once at process start from
    the app's ``modules.txt`` file. Apps missing that file fail with
    'Module HR Master not found'. This recreates the record if needed and
    refreshes the runtime maps so the current process can resolve it too.
    """
    if not frappe.db.exists("Module Def", "HR Master"):
        md = frappe.new_doc("Module Def")
        md.module_name = "HR Master"
        md.app_name = "hr_master"
        md.insert(ignore_permissions=True)
        frappe.db.commit()
        print("HR Master: created 'HR Master' Module Def")
    else:
        # Sites installed with older code may have the record with an
        # empty or wrong app_name - keep it consistent.
        md = frappe.get_doc("Module Def", "HR Master")
        if md.app_name != "hr_master":
            md.app_name = "hr_master"
            md.save(ignore_permissions=True)
            frappe.db.commit()

    # Frappe builds the module maps at connect time; refresh them now so
    # this process (e.g. a migrate run) can resolve the module too.
    _refresh_module_maps()


def _refresh_module_maps():
    """Merge Module Def records from the DB into ``frappe.local.app_modules``
    and ``frappe.local.module_app`` (normally built from ``modules.txt``).
    """
    frappe.local.app_modules = frappe.local.app_modules or {}
    frappe.local.module_app = frappe.local.module_app or {}

    for m in frappe.db.get_all(
        "Module Def",
        fields=["name", "app_name"],
        ignore_permissions=True,
        limit_page_length=0,
        order_by=None,
    ):
        app = m.get("app_name")
        module = frappe.scrub(m.get("name"))
        if not app or not module:
            continue
        frappe.local.app_modules.setdefault(app, [])
        if module not in frappe.local.app_modules[app]:
            frappe.local.app_modules[app].append(module)
        frappe.local.module_app[module] = app


def _run_phase(phase_name, fn):
    """Run a setup phase.

    Failures are logged to the Error Log and printed to the console (with
    the exception message) but never re-raised, so a single broken record
    can never abort a migrate run or block the remaining setup phases.
    """
    try:
        fn()
    except Exception as e:
        frappe.log_error(
            title=f"HR Master: {phase_name} failed",
            message=frappe.get_traceback(),
        )
        print(f"HR Master: {phase_name} failed: {e}")


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


def create_workflow_masters():
    """Create Workflow State and Workflow Action Master records.

    Since Frappe v13 the 'Workflow State' and 'Workflow Action Master'
    doctypes are standalone records, and a Workflow document's child rows
    link to them by name. Importing the Workflow fixture does NOT create
    them, so without this seed step the Desk raises
    "Workflow State <name> not found" (404) whenever the workflow loads.
    These are the exact states/actions referenced by the
    'Candidate Evaluation' workflow fixture.
    """
    workflow_states = [
        ("Pending", "Info"),
        ("Evaluated", "Primary"),
        ("Shortlisted", "Success"),
        ("Interview Scheduled", "Info"),
        ("Rejected", "Danger"),
        ("On Hold", "Warning"),
    ]

    for state_name, style in workflow_states:
        if not frappe.db.exists("Workflow State", state_name):
            state = frappe.new_doc("Workflow State")
            state.workflow_state_name = state_name
            state.style = style
            state.save(ignore_permissions=True)
            print("HR Master: created Workflow State {0}".format(state_name))
            frappe.logger().info("HR Master: created Workflow State {0}".format(state_name))

    workflow_actions = [
        "Evaluate",
        "Shortlist",
        "Reject",
        "Schedule Interview",
        "Put on Hold",
        "Re-evaluate",
    ]

    for action_name in workflow_actions:
        if not frappe.db.exists("Workflow Action Master", action_name):
            action = frappe.new_doc("Workflow Action Master")
            action.workflow_action_name = action_name
            action.save(ignore_permissions=True)
            print("HR Master: created Workflow Action Master {0}".format(action_name))
            frappe.logger().info("HR Master: created Workflow Action Master {0}".format(action_name))

    frappe.db.commit()
    print("HR Master: workflow masters ready")
    frappe.logger().info("HR Master: workflow masters ready")


def sync_all_resources():
    """
    Explicitly import all DocType, Report, Workspace, Number Card,
    Notification, Print Format, Workflow, Email Template and Letter Head
    JSON files from disk.

    Frappe's native migrate sync handles doctype, report, workspace,
    print format and notification automatically once the app's Module Def
    exists in the site, but number cards, workflows, email templates and
    letter heads are only ever imported here. Running all of them keeps
    every standard record in sync with this repository.
    """
    # Module content lives in the 'hr_master' module folder inside the
    # app package root (parent of setup/).
    module_root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "hr_master",
    )

    resource_dirs = [
        "doctype",
        "report",
        "workspace",
        "number_card",
        "notification",
        "print_format",
        "letter_head",
        "workflow",
        "email_template",
    ]

    imported = 0
    skipped = 0

    for subdir in resource_dirs:
        resource_path = os.path.join(module_root, subdir)
        if not os.path.exists(resource_path):
            continue

        if subdir == "workspace":
            # Workspaces are nested: workspace/{name}/{name}.json
            for ws_dir in sorted(os.listdir(resource_path)):
                ws_path = os.path.join(resource_path, ws_dir)
                if os.path.isdir(ws_path):
                    for f in sorted(os.listdir(ws_path)):
                        if f.endswith(".json"):
                            json_path = os.path.join(ws_path, f)
                            imported, skipped = _import_json(json_path, imported, skipped)
        else:
            # Standard: subdir/{name}/*.json (import ALL json files including child tables)
            for item_dir in sorted(os.listdir(resource_path)):
                item_path = os.path.join(resource_path, item_dir)
                if os.path.isdir(item_path):
                    for f in sorted(os.listdir(item_path)):
                        if f.endswith(".json"):
                            json_path = os.path.join(item_path, f)
                            imported, skipped = _import_json(json_path, imported, skipped)

    print(f"HR Master: synced resources - {imported} imported, {skipped} skipped")
    frappe.logger().info(
        f"HR Master: sync_all_resources finished - {imported} imported, {skipped} skipped"
    )


def _import_json(json_path, imported=0, skipped=0):
    """Import a single JSON file as a Frappe document.

    Existing DocTypes are skipped to avoid clobbering site-level changes
    (Frappe's native migrate keeps standard doctypes in sync). All other
    records (reports, workspaces, number cards, workflows, ...) are
    force-imported on every run so they always match this repository.
    """
    doc_data = {}
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            doc_data = json.load(f)

        doctype_name = doc_data.get("doctype", "")
        doc_name = doc_data.get("name", "")

        if not doctype_name or not doc_name:
            frappe.logger().warning(
                f"HR Master: Skipping {json_path} - missing doctype/name"
            )
            return imported, skipped + 1

        if doctype_name == "DocType" and frappe.db.exists("DocType", doc_name):
            return imported, skipped + 1

        import_file_by_path(json_path, force=True, ignore_version=True)
        frappe.db.commit()
        return imported + 1, skipped
    except Exception as e:
        frappe.log_error(
            title=f"HR Master: Failed to import {doc_data.get('name', os.path.basename(json_path))}",
            message=frappe.get_traceback(),
        )
        frappe.logger().error(f"HR Master: Failed importing {json_path} - {e}")
        return imported, skipped + 1


def set_default_config():
    """Set default configuration values only when not already configured.

    Previously defaults were applied on every migrate, silently overwriting
    admin changes. Now they are applied only for Singles with no saved values.
    Each step is isolated so one failure cannot hide the others.
    """
    _run_phase(
        "set_defaults:Job Portal Config",
        lambda: _set_single_defaults(
            "Job Portal Config",
            {
                "auto_search_enabled": 0,
                "auto_shortlist_threshold": 80,
                "max_candidates_per_search": 50,
                "search_delay_seconds": 2,
                "default_country": "India",
                "demo_enabled": 1,
                "demo_search_limit": 15,
                "remotive_enabled": 1,
                "remotive_search_limit": 15,
                "arbeitnow_enabled": 1,
                "arbeitnow_search_limit": 15,
                "notify_on_high_match": 1,
                "notify_on_search_complete": 0,
                "email_notifications": 1,
                "desktop_notifications": 1,
            },
        ),
    )

    _run_phase(
        "set_defaults:Recruitment Settings",
        lambda: _set_single_defaults(
            "Recruitment Settings",
            {
                "auto_parse_resumes": 1,
                "max_resume_size_kb": 10240,
                "allowed_file_types": "pdf,docx,txt",
                "enable_duplicate_detection": 1,
                "duplicate_threshold": 85,
                "notify_on_new_candidate": 1,
                "notify_on_offer_acceptance": 1,
                "daily_digest_enabled": 1,
                "weekly_report_enabled": 1,
                "enable_audit_logging": 1,
                "enable_rate_limiting": 0,
                "max_api_requests_per_minute": 60,
                "session_timeout_minutes": 60,
                "require_approval_for_offers": 1,
            },
        ),
    )

    # Create default Email Templates
    _run_phase("create_default_email_templates", create_default_email_templates)


def _set_single_defaults(single_doctype, defaults):
    """Populate a Single doctype's defaults only if it has no saved values yet."""
    if frappe.db.get_singles_dict(single_doctype):
        return

    doc = frappe.get_single(single_doctype)
    doc.update(defaults)
    doc.save(ignore_permissions=True)
    frappe.db.commit()


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
