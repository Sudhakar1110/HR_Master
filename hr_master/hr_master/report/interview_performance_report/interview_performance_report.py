"""Interview Performance Report"""
from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"fieldname":"interviewer","label":_("Interviewer"),"fieldtype":"Data","width":180},
        {"fieldname":"interviews_conducted","label":_("Interviews"),"fieldtype":"Int","width":100},
        {"fieldname":"avg_rating","label":_("Avg Rating"),"fieldtype":"Rating","width":100},
        {"fieldname":"selected","label":_("Selected"),"fieldtype":"Int","width":80},
        {"fieldname":"rejected","label":_("Rejected"),"fieldtype":"Int","width":80},
    ]
    data = frappe.db.sql("""
        SELECT interviewer, COUNT(*) as interviews_conducted,
               AVG(overall_rating) as avg_rating,
               SUM(CASE WHEN result='Selected' THEN 1 ELSE 0 END) as selected,
               SUM(CASE WHEN result='Rejected' THEN 1 ELSE 0 END) as rejected
        FROM `tabInterview Feedback` WHERE docstatus < 2
        GROUP BY interviewer
    """, as_dict=True)
    return columns, data or [], None, None, None
