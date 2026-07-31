"""Time-to-Hire Report for HR Master"""

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff

def execute(filters=None):
    columns = [
        {"fieldname":"candidate_name","label":_("Candidate"),"fieldtype":"Data","width":180},
        {"fieldname":"job_title","label":_("Job Title"),"fieldtype":"Data","width":150},
        {"fieldname":"source_date","label":_("Sourced Date"),"fieldtype":"Date","width":100},
        {"fieldname":"hired_date","label":_("Hired Date"),"fieldtype":"Date","width":100},
        {"fieldname":"days_to_hire","label":_("Days to Hire"),"fieldtype":"Int","width":100},
        {"fieldname":"recruiter","label":_("Recruiter"),"fieldtype":"Data","width":120},
    ]
    conditions = ""
    if filters:
        if filters.get("from_date"):
            conditions += f" AND c.creation >= '{filters['from_date']}'"
        if filters.get("to_date"):
            conditions += f" AND c.creation <= '{filters['to_date']}'"
        if filters.get("recruiter"):
            conditions += f" AND c.owner = '{frappe.db.escape(filters['recruiter'])}'"

    data = frappe.db.sql(f"""
        SELECT c.name, c.candidate_name, c.creation as source_date,
               c.modified as hired_date, c.owner as recruiter,
               (SELECT cr.job_title FROM `tabCandidate Ranking` cr WHERE cr.candidate = c.name LIMIT 1) as job_title
        FROM `tabCandidate` c
        WHERE c.status = 'Selected' AND c.docstatus < 2 {conditions}
        ORDER BY c.modified DESC LIMIT 200
    """, as_dict=True)

    for d in data:
        d.days_to_hire = date_diff(d.hired_date, d.source_date) if d.source_date and d.hired_date else 0

    avg_days = sum(d.days_to_hire for d in data) / len(data) if data else 0
    
    chart = {"data":{"labels":[d.candidate_name[:15] for d in data[:20]],"datasets":[{"name":"Days","values":[d.days_to_hire for d in data[:20]],"chartType":"bar"}]},"type":"bar","height":300,"colors":["#3498db"]}
    
    summary = [
        {"value":len(data),"label":_("Hired Candidates"),"indicator":"Green"},
        {"value":round(avg_days,1),"label":_("Avg Days to Hire"),"indicator":"Blue"},
    ]
    return columns, data, None, chart, summary
