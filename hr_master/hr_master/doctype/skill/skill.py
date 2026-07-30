"""Skill DocType Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class Skill(Document):
    """Master data for skills used in JD parsing and candidate matching."""

    def validate(self):
        self.set_skill_name()
        self.validate_aliases()

    def set_skill_name(self):
        """Ensure skill name is properly formatted."""
        if self.skill_name:
            self.skill_name = self.skill_name.strip().title()

    def validate_aliases(self):
        """Validate and clean up aliases."""
        if self.aliases:
            aliases = [a.strip().lower() for a in self.aliases.split(",")]
            aliases = [a for a in aliases if a]
            self.aliases = ", ".join(aliases)

    def get_aliases_list(self):
        """Return aliases as a list."""
        if self.aliases:
            return [a.strip().lower() for a in self.aliases.split(",")]
        return []


def get_all_active_skills():
    """Get all active skills with their aliases."""
    skills = frappe.get_all("Skill", filters={"is_active": 1}, fields=["name", "aliases"])
    skill_map = {}
    for skill in skills:
        skill_map[skill.name.lower()] = skill.name
        if skill.aliases:
            for alias in skill.aliases.split(","):
                alias = alias.strip().lower()
                if alias:
                    skill_map[alias] = skill.name
    return skill_map


def extract_skills_from_text(text):
    """Extract known skills from a given text."""
    if not text:
        return []

    text_lower = text.lower()
    skill_map = get_all_active_skills()
    found_skills = []

    for keyword, skill_name in skill_map.items():
        if keyword in text_lower:
            found_skills.append(skill_name)

    return list(set(found_skills))
