"""Skill Gap Analysis Report for HR Master"""

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"fieldname":"skill","label":_("Skill"),"fieldtype":"Link","options":"Skill","width":180},
        {"fieldname":"jd_required_count","label":_("Required In JDs"),"fieldtype":"Int","width":120},
        {"fieldname":"candidate_match_count","label":_("Candidates With Skill"),"fieldtype":"Int","width":150},
        {"fieldname":"gap_percentage","label":_("Gap %"),"fieldtype":"Percent","width":100},
        {"fieldname":"avg_match_score","label":_("Avg Match Score"),"fieldtype":"Percent","width":120},
    ]
    conditions = ""
    skill_filter = filters.get("skill") if filters else None
    if skill_filter:
        conditions += f" AND s.skill = '{frappe.db.escape(skill_filter)}'"

    data = frappe.db.sql(f"""
        SELECT s.skill,
               COUNT(DISTINCT s.parent) as jd_required_count,
               COUNT(DISTINCT cr.candidate) as candidate_match_count,
               ROUND(AVG(sm.match_score),1) as avg_match_score
        FROM `tabJD Skill Detail` s
        LEFT JOIN `tabSkill Match Detail` sm ON sm.skill = s.skill
        LEFT JOIN `tabCandidate Ranking` cr ON cr.name = sm.parent
        {conditions}
        GROUP BY s.skill
    """, as_dict=True)

    for d in data:
        d.gap_percentage = round((1 - (d.candidate_match_count / max(d.jd_required_count, 1))) * 100, 1)

    # Apply min_gap filter in Python (not SQL, since gap_percentage is computed here)
    min_gap = float(filters.get("min_gap")) if filters and filters.get("min_gap") else 0
    if min_gap > 0:
        data = [d for d in data if d.gap_percentage >= min_gap]

    chart = {"data":{"labels":[d.skill[:20] for d in data[:15]],"datasets":[
        {"name":"Required","values":[d.jd_required_count for d in data[:15]],"chartType":"bar"},
        {"name":"Available","values":[d.candidate_match_count for d in data[:15]],"chartType":"bar"}
    ]},"type":"bar","height":300,"colors":["#e74c3c","#2ecc71"]}

    summary = [
        {"value":len(data),"label":_("Skills Analyzed"),"indicator":"Blue"},
        {"value":sum(d.jd_required_count for d in data),"label":_("Total Requirements"),"indicator":"Blue"},
    ]
    return columns, data, None, chart, summary
