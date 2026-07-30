"""HR Master Module Definition for Frappe Framework v15+"""

from frappe import _


def get_data():
    """
    Return module definition for Frappe v15+.

    This is the standard Frappe v15 hook to register app modules.
    Frappe discovers this function automatically during migration
    and uses it to create/update the Module Def records.
    """
    return [
        {
            "module_name": "HR Master",
            "category": "Modules",
            "label": _("HR Master"),
            "color": "blue",
            "icon": "octicon octicon-person",
            "type": "module",
            "app": "hr_master",
        }
    ]
