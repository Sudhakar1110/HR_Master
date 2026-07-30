"""Recruitment Dashboard Report Script for HR Master"""

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns, data = get_columns(), get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary

def get_columns():
    return [
        {"fieldname":"candidate_name","label":_("Candidate"),"fieldtype":"Data","width":180},
        {"fieldname":"status","label":_("Status"),"fieldtype":"Data","width":120},
        {"fieldname":"source","label":_("Source"),"fieldtype":"Data","width":100},
        {"fieldname":"current_title","label":_("Current Title"),"fieldtype":"Data","width":180},
        {"fieldname":"total_match_score","label":_("Match Score"),"fieldtype":"Percent","width":100},
        {"fieldname":"job_title","label":_("Job"),"fieldtype":"Data","width":150},
        {"fieldname":"created","label":_("Created"),"fieldtype":"Date","width":100},
    ]

def get_data(filters):
    conditions = ""
    if filters:
        if filters.get("from_date"):
            conditions += f" AND c.creation >= '{filters['from_date']}'"
        if filters.get("to_date"):
            conditions += f" AND c.creation <= '{filters['to_date']}'"
        if filters.get("status"):
            conditions += f" AND c.status = '{frappe.db.escape(filters['status'])}'"
        if filters.get("source"):
            conditions += f" AND c.source = '{frappe.db.escape(filters['source'])}'"
    return frappe.db.sql(f"""
        SELECT c.name, c.candidate_name, c.status, c.source, c.current_title,
               c.total_match_score, c.creation as created
        FROM `tabCandidate` c WHERE c.docstatus < 2 {conditions}
        ORDER BY c.creation DESC LIMIT 100
    """, as_dict=True)

def get_chart(data):
    if not data: return None
    status_counts = {}
    for d in data:
        s = d.status or "Unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
    return {"data":{"labels":list(status_counts.keys()),"datasets":[{"name":"Candidates","values":list(status_counts.values()),"chartType":"bar"}]},"type":"bar","height":250,"colors":["#2490ef"]}

def get_summary(data):
    if not data: return []
    return [
        {"value":len(data),"label":_("Total Candidates"),"indicator":"Blue"},
        {"value":sum(1 for d in data if d.status=="Shortlisted"),"label":_("Shortlisted"),"indicator":"Green"},
        {"value":sum(1 for d in data if d.status=="Selected"),"label":_("Selected"),"indicator":"Green"},
    ]
