"""HR Master Module Definition for Frappe Framework v15+"""

from frappe import _

def get_module_icons():
    """Return module icon mapping."""
    return {
        "HR Master": {"icon": "hr", "color": "blue"}
    }


def get_module_profile():
    """Return module profile definition."""
    return {
        "Module Name": "HR Master",
        "Module Category": "Human Resources",
        "App Name": "hr_master",
        "Module Icon": "octicon octicon-person",
        "Module Color": "blue",
        "Is Standard": 1,
        "Custom": 0,
        "Package": "",
        "Label": _("HR Master"),
        "Workspace": "HR Master",
    }
