"""Recruitment Analytics Report for HR Master"""

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"fieldname":"metric","label":_("Metric"),"fieldtype":"Data","width":250},
        {"fieldname":"current_value","label":_("Current Value"),"fieldtype":"Float","width":120},
        {"fieldname":"previous_value","label":_("Previous Period"),"fieldtype":"Float","width":120},
        {"fieldname":"change_percentage","label":_("Change %"),"fieldtype":"Percent","width":100},
    ]
    total_candidates = frappe.db.count("Candidate", filters={"docstatus":["<",2]})
    total_jds = frappe.db.count("Job Description", filters={"docstatus":["<",2]})
    shortlisted = frappe.db.count("Candidate", filters={"status":"Shortlisted","docstatus":["<",2]})
    selected = frappe.db.count("Candidate", filters={"status":"Selected","docstatus":["<",2]})
    interviewed = frappe.db.count("Interview Schedule", filters={"status":"Completed"})
    offers = frappe.db.count("Offer Management", filters={"docstatus":["<",2]})
    offers_accepted = frappe.db.count("Offer Management", filters={"status":"Accepted"})
    
    data = [
        {"metric":_("Total Candidates"),"current_value":total_candidates,"previous_value":0,"change_percentage":100},
        {"metric":_("Active Job Descriptions"),"current_value":total_jds,"previous_value":0,"change_percentage":100},
        {"metric":_("Candidates Shortlisted"),"current_value":shortlisted,"previous_value":0,"change_percentage":round((shortlisted/max(total_candidates,1))*100,1)},
        {"metric":_("Candidates Selected"),"current_value":selected,"previous_value":0,"change_percentage":round((selected/max(total_candidates,1))*100,1)},
        {"metric":_("Interviews Completed"),"current_value":interviewed,"previous_value":0,"change_percentage":100},
        {"metric":_("Offers Made"),"current_value":offers,"previous_value":0,"change_percentage":100},
        {"metric":_("Offers Accepted"),"current_value":offers_accepted,"previous_value":0,"change_percentage":round((offers_accepted/max(offers,1))*100,1)},
        {"metric":_("Offer Acceptance Rate"),"current_value":round((offers_accepted/max(offers,1))*100,1),"previous_value":0,"change_percentage":round((offers_accepted/max(offers,1))*100,1)},
        {"metric":_("Selection Rate"),"current_value":round((selected/max(total_candidates,1))*100,1),"previous_value":0,"change_percentage":round((selected/max(total_candidates,1))*100,1)},
    ]
    
    chart = {"data":{"labels":[d["metric"] for d in data],"datasets":[{"name":"Value","values":[d["current_value"] for d in data],"chartType":"bar"}]},"type":"bar","height":300,"colors":["#9b59b6"]}
    return columns, data, None, chart, None
