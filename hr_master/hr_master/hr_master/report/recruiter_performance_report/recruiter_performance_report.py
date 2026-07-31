"""Recruiter Performance Report"""
from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"fieldname":"recruiter","label":_("Recruiter"),"fieldtype":"Data","width":200},
        {"fieldname":"candidates_sourced","label":_("Sourced"),"fieldtype":"Int","width":100},
        {"fieldname":"candidates_shortlisted","label":_("Shortlisted"),"fieldtype":"Int","width":100},
        {"fieldname":"interviews_scheduled","label":_("Interviews"),"fieldtype":"Int","width":100},
        {"fieldname":"offers_made","label":_("Offers"),"fieldtype":"Int","width":100},
        {"fieldname":"hired","label":_("Hired"),"fieldtype":"Int","width":100},
    ]
    data = frappe.db.sql("""
        SELECT owner as recruiter, COUNT(*) as candidates_sourced,
            SUM(CASE WHEN status IN ('Shortlisted','Interview Scheduled','Selected') THEN 1 ELSE 0 END) as candidates_shortlisted
        FROM `tabCandidate` WHERE docstatus < 2 GROUP BY owner
    """, as_dict=True)
    return columns, data or [], None, None, None
