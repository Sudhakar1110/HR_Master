"""HR Master App Hooks for Frappe Framework v15+"""

from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "hr_master"
app_title = "HR Master"
app_publisher = "HR Master Team"
app_description = "AI-powered candidate sourcing and ranking system for ERPNext v15+"
app_icon = "octicon octicon-person"
app_color = "blue"
app_email = "info@hrmaster.com"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]
after_install = "hr_master.setup.install.after_install"
after_migrate = "hr_master.setup.install.after_migrate"
override_doctype_class = {}

doc_events = {
    "Job Description": {
        "on_update": "hr_master.doctype.job_description.job_description.on_update"
    },
    "Candidate Ranking": {
        "after_insert": "hr_master.doctype.candidate_ranking.candidate_ranking.after_insert"
    },
    "Resume": {
        "on_submit": "hr_master.doctype.resume.resume.on_submit",
        "validate": "hr_master.doctype.resume.resume.validate"
    },
    "Offer Management": {
        "on_update_after_submit": "hr_master.doctype.offer_management.offer_management.on_update_after_submit"
    },
    "Interview Feedback": {
        "after_insert": "hr_master.doctype.interview_feedback.interview_feedback.after_insert"
    },
    "Candidate": {
        "after_insert": "hr_master.doctype.candidate.candidate.after_insert"
    }
}

scheduler_events = {
    "daily": [
        "hr_master.tasks.daily.auto_search_portals",
        "hr_master.tasks.daily.update_jd_statuses"
    ],
    "hourly": [
        "hr_master.tasks.hourly.auto_rank_pending_candidates",
        "hr_master.tasks.hourly.process_pending_search_results"
    ],
    "daily_long": [
        "hr_master.tasks.daily_cleanup.archive_old_searches",
        "hr_master.tasks.resume_queue.process_pending_resumes"
    ],
    "cron": {
        "0 2 * * 1": [
            "hr_master.tasks.report_generation.generate_weekly_report"
        ],
        "0 3 * * 0": [
            "hr_master.tasks.duplicate_detection.scan_for_duplicates"
        ],
        "0 4 * * *": [
            "hr_master.tasks.ai_ranking.ai_rank_candidates"
        ],
        "0 6 * * 0": [
            "hr_master.tasks.search_index.rebuild_search_index"
        ],
        "30 6 * * 0": [
            "hr_master.tasks.search_index.optimize_search_queries"
        ],
        "0 7 * * *": [
            "hr_master.tasks.report_generation.generate_daily_report"
        ],
        "0 8 * * 1": [
            "hr_master.tasks.report_generation.generate_weekly_report"
        ],
        "0 */6 * * *": [
            "hr_master.tasks.email_queue.process_email_queue"
        ]
    }
}

scheduled_tasks = {
    "process_candidate_search": {
        "type": "method",
        "method": "hr_master.tasks.celery.process_candidate_search",
        "queue": "long"
    },
    "rank_candidates_batch": {
        "type": "method",
        "method": "hr_master.tasks.celery.rank_candidates_batch",
        "queue": "long"
    },
    "process_resume_parsing": {
        "type": "method",
        "method": "hr_master.tasks.resume_queue.process_resume_parsing",
        "queue": "long"
    },
    "ai_rank_single_candidate": {
        "type": "method",
        "method": "hr_master.tasks.ai_ranking.ai_rank_single_candidate",
        "queue": "long"
    },
    "send_hr_notification": {
        "type": "method",
        "method": "hr_master.tasks.email_queue.send_hr_notification",
        "queue": "short"
    },
    "enqueue_notification_email": {
        "type": "method",
        "method": "hr_master.tasks.email_queue.enqueue_notification_email",
        "queue": "short"
    }
}

fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "HR Master Admin", "HR Master Recruiter",
        "HR Master Hiring Manager", "HR Master Viewer"
    ]]},
    {"dt": "Workflow", "filters": [["name", "=", "Candidate Evaluation"]]},
    {"dt": "Workflow State"},
    {"dt": "Workflow Action"},
    {"dt": "Email Template Config"},
    {"dt": "Recruitment Settings"},
    {"dt": "Notification", "filters": [["name", "in", [
        "Candidate Shortlisted",
        "Interview Scheduled",
        "Resume Uploaded",
        "Candidate Ranked",
        "Interview Feedback Submitted",
        "Offer Generated",
        "Offer Accepted",
        "Candidate Hired"
    ]]},
    {"dt": "Print Format", "filters": [["name", "in", [
        "Interview Feedback Form",
        "Candidate Profile",
        "Offer Letter"
    ]]},
    {"dt": "Letter Head", "filters": [["name", "in", [
        "Standard",
        "Official"
    ]]},
]

website_route_rules = [
    {"from_route": "/hr-master/candidates/<path:app>", "to_route": "candidate_portal"}
]

boot_session = "hr_master.boot.set_boot_config"

permission_query_conditions = {
    "Candidate": "hr_master.doctype.candidate.candidate.get_permission_query_conditions"
}

jinja = {
    "methods": [
        "hr_master.utils.template_filters.get_match_color",
        "hr_master.utils.template_filters.format_score"
    ]
}

translations = "hr_master/hr_master/translations"
custom_fields_path = "hr_master/fixtures/custom_fields.json"
