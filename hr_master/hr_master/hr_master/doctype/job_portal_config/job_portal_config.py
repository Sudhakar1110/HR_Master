"""Job Portal Config DocType (Single) Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class JobPortalConfig(Document):
    """Singleton configuration for job portal integrations."""

    def validate(self):
        self.validate_api_configs()

    def validate_api_configs(self):
        """Validate that required API fields are populated for enabled portals."""
        if self.linkedin_enabled:
            if not self.linkedin_api_key:
                frappe.throw("LinkedIn API Key is required when LinkedIn is enabled")
            if not self.linkedin_access_token:
                frappe.throw("LinkedIn Access Token is required when LinkedIn is enabled")

        if self.naukri_enabled:
            if not self.naukri_api_key:
                frappe.throw("Naukri API Key is required when Naukri is enabled")

        if self.indeed_enabled:
            if not self.indeed_publisher_id:
                frappe.throw("Indeed Publisher ID is required when Indeed is enabled")

        if self.monster_enabled:
            if not self.monster_api_key:
                frappe.throw("Monster API Key is required when Monster is enabled")

        if getattr(self, "serpapi_enabled", 0):
            if not getattr(self, "serpapi_api_key", None):
                frappe.throw("SerpAPI API Key is required when SerpAPI is enabled")

    def get_enabled_portals(self):
        """Get list of enabled portals."""
        portals = []
        if self.linkedin_enabled:
            portals.append("LinkedIn")
        if self.naukri_enabled:
            portals.append("Naukri")
        if self.indeed_enabled:
            portals.append("Indeed")
        if self.monster_enabled:
            portals.append("Monster")
        if getattr(self, "serpapi_enabled", 0):
            portals.append("SerpAPI")
        if getattr(self, "demo_enabled", 0):
            portals.append("Demo")
        return portals

    def get_search_limit(self, portal):
        """Get search limit for a specific portal."""
        limits = {
            "LinkedIn": self.linkedin_search_limit or 25,
            "Naukri": self.naukri_search_limit or 25,
            "Indeed": self.indeed_search_limit or 25,
            "Monster": self.monster_search_limit or 25,
            "SerpAPI": self.serpapi_search_limit or 10,
            "Demo": getattr(self, "demo_search_limit", 0) or 15,
        }
        return limits.get(portal, 10)

    def get_notification_recipients(self):
        """Get list of notification recipients."""
        recipients = []
        if self.notification_recipients:
            for row in self.notification_recipients:
                recipients.append({
                    "user": row.user,
                    "email": row.email,
                    "type": row.notification_type,
                })
        return recipients
