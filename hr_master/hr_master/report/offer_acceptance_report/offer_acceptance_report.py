"""Offer Acceptance Report"""
from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"fieldname":"status","label":_("Status"),"fieldtype":"Data","width":200},
        {"fieldname":"count","label":_("Count"),"fieldtype":"Int","width":100},
        {"fieldname":"total_ctc","label":_("Total CTC"),"fieldtype":"Currency","width":120},
    ]
    data = frappe.db.sql("""
        SELECT status, COUNT(*) as count, SUM(total_ctc) as total_ctc
        FROM `tabOffer Management` WHERE docstatus < 2
        GROUP BY status ORDER BY count DESC
    """, as_dict=True)
    chart = {"data":{"labels":[d.status for d in data],"datasets":[{"name":"Offers","values":[d.count for d in data],"chartType":"pie"}]},"type":"pie","height":250}
    return columns, data or [], None, chart, None
