"""HR Master Recruiting Portal - Interview calendar page."""

from __future__ import unicode_literals

import calendar as _cal
from datetime import date, timedelta

import frappe

from hr_master.api.portal_actions import (
    require_hr_access,
    set_portal_context,
    can_write,
    visible_jd_names,
    _time_to_string,
)

_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_INTERVIEW_FIELDS = [
    "name",
    "candidate",
    "candidate_name",
    "job_description",
    "job_title",
    "scheduled_date",
    "scheduled_time",
    "status",
    "interview_type",
    "location_or_link",
]


def get_context(context):
    """Render the interview month grid plus an upcoming-7-days list."""
    require_hr_access()
    set_portal_context(context)
    context.no_cache = 1
    context.active = "calendar"
    context.can_write = can_write()
    context.page_title = "Interview Calendar"
    context.page_description = "Upcoming interviews across all job descriptions — month grid plus the next 7 days."

    today = date.today()
    try:
        year = int(frappe.form_dict.get("year") or today.year)
        month = int(frappe.form_dict.get("month") or today.month)
    except (TypeError, ValueError):
        year, month = today.year, today.month
    if month < 1:
        month, year = 12, year - 1
    if month > 12:
        month, year = 1, year + 1

    visible = visible_jd_names()
    last_day = _cal.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)

    filters = [["scheduled_date", "between", [month_start, month_end]]]
    if visible is not None:
        if not visible:
            filters.append(["job_description", "in", ["__no_visible_jd__"]])
        else:
            filters.append(["job_description", "in", visible])

    interviews = frappe.get_all(
        "Interview Schedule",
        fields=_INTERVIEW_FIELDS,
        filters=filters,
        order_by="scheduled_date asc, scheduled_time asc",
        limit_page_length=500,
    )
    for iv in interviews:
        iv["time_display"] = _time_to_string(iv.get("scheduled_time"))

    by_day = {}
    for iv in interviews:
        day = iv.get("scheduled_date")
        if not day:
            continue
        by_day.setdefault(int(day.day), []).append(iv)

    # Build the grid cells (Mon-first), padded to whole weeks.
    cells = []
    for _ in range(_cal.weekday(year, month, 1)):
        cells.append({"day": 0, "interviews": [], "is_today": False})
    for day in range(1, last_day + 1):
        cells.append(
            {
                "day": day,
                "interviews": by_day.get(day, []),
                "is_today": (year, month, day) == (today.year, today.month, today.day),
            }
        )
    while len(cells) % 7:
        cells.append({"day": 0, "interviews": [], "is_today": False})

    context.month_name = _cal.month_name[month]
    context.year = year
    context.month = month
    context.weekdays = _WEEKDAYS
    context.cells = cells

    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)
    context.prev_link = "/hr_portal/calendar?year={0}&month={1}".format(prev_y, prev_m)
    context.next_link = "/hr_portal/calendar?year={0}&month={1}".format(next_y, next_m)

    # Upcoming 7 days
    week_end = today + timedelta(days=6)
    up_filters = [["scheduled_date", "between", [today, week_end]]]
    if visible is not None:
        if not visible:
            up_filters.append(["job_description", "in", ["__no_visible_jd__"]])
        else:
            up_filters.append(["job_description", "in", visible])
    upcoming = frappe.get_all(
        "Interview Schedule",
        fields=_INTERVIEW_FIELDS,
        filters=up_filters,
        order_by="scheduled_date asc, scheduled_time asc",
        limit_page_length=12,
    )
    for iv in upcoming:
        iv["time_display"] = _time_to_string(iv.get("scheduled_time"))
    context.upcoming = upcoming

    return context
