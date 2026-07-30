"""Hiring Funnel Report Script for HR Master"""

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"fieldname":"stage","label":_("Stage"),"fieldtype":"Data","width":200},
        {"fieldname":"count","label":_("Count"),"fieldtype":"Int","width":100},
        {"fieldname":"percentage","label":_("% of Total"),"fieldtype":"Percent","width":100},
    ]
    stages = ["New","Contacted","Screened","Shortlisted","Interview Scheduled","Interviewed","Selected","Rejected","On Hold"]
    total = frappe.db.count("Candidate", filters={"docstatus":["<",2]})
    data = []
    for stage in stages:
        cnt = frappe.db.count("Candidate", filters={"status":stage,"docstatus":["<",2]})
        pct = round((cnt/total*100),1) if total > 0 else 0
        data.append({"stage":_(stage),"count":cnt,"percentage":pct})
    
    chart = {
        "data":{"labels":[d["stage"] for d in data],"datasets":[{"name":"Candidates","values":[d["count"] for d in data],"chartType":"bar"}]},
        "type":"bar","height":300,"colors":["#2490ef"]
    }
    summary = [
        {"value":total,"label":_("Total Candidates"),"indicator":"Blue"},
        {"value":frappe.db.count("Candidate",filters={"status":"Shortlisted","docstatus":["<",2]}),"label":_("Shortlisted"),"indicator":"Green"},
        {"value":frappe.db.count("Candidate",filters={"status":"Selected","docstatus":["<",2]}),"label":_("Selected"),"indicator":"Green"},
    ]
    return columns, data, None, chart, summary
