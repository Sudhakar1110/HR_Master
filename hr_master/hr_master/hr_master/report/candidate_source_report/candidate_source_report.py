"""Candidate Source Report Script for HR Master"""

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"fieldname":"source","label":_("Source"),"fieldtype":"Data","width":200},
        {"fieldname":"count","label":_("Candidates"),"fieldtype":"Int","width":120},
        {"fieldname":"shortlisted","label":_("Shortlisted"),"fieldtype":"Int","width":100},
        {"fieldname":"selected","label":_("Selected"),"fieldtype":"Int","width":100},
        {"fieldname":"conversion_rate","label":_("Conversion Rate"),"fieldtype":"Percent","width":100},
    ]
    data = frappe.db.sql("""
        SELECT source, COUNT(*) as count,
               SUM(CASE WHEN status IN ('Shortlisted','Interview Scheduled','Selected') THEN 1 ELSE 0 END) as shortlisted,
               SUM(CASE WHEN status = 'Selected' THEN 1 ELSE 0 END) as selected
        FROM `tabCandidate` WHERE docstatus < 2 AND source IS NOT NULL AND source != ''
        GROUP BY source ORDER BY count DESC
    """, as_dict=True)
    for d in data:
        d.conversion_rate = round((d.selected / d.count * 100), 1) if d.count > 0 else 0
    
    chart = {"data":{"labels":[d.source for d in data],"datasets":[
        {"name":"Total","values":[d.count for d in data],"chartType":"bar"},
        {"name":"Selected","values":[d.selected for d in data],"chartType":"bar"}
    ]},"type":"bar","height":300,"colors":["#2490ef","#5cb85c"]}
    
    return columns, data, None, chart, None
