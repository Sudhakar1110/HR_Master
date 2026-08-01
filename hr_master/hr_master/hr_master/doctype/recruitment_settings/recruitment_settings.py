"""Recruitment Settings Singleton Controller for HR Master"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document

AI_PROVIDERS = ("gemini", "groq", "openai", "deepseek", "ollama")


class RecruitmentSettings(Document):
    """Central configuration for recruitment operations."""
    
    def validate(self):
        self.validate_file_types()
        self.validate_ai_config()

    def validate_ai_config(self):
        """Ensure AI settings are coherent when AI features are enabled."""
        if not self.ai_enabled:
            return

        provider = (self.ai_provider or "gemini").strip().lower()
        if provider not in AI_PROVIDERS:
            frappe.throw(_("Invalid AI provider: {0}").format(provider))

        # Ollama runs locally and needs no key
        if provider == "ollama":
            return

        if not (self.ai_api_key or "").strip():
            frappe.throw(
                _("AI API Key is required when AI Features are enabled (provider: {0}). "
                  "Use Ollama if you want to run AI locally without a key.").format(provider)
            )

    def validate_file_types(self):
        if self.allowed_file_types:
            types = [t.strip().lower() for t in self.allowed_file_types.split(",")]
            self.allowed_file_types = ", ".join(types)

    def get_allowed_extensions(self):
        if self.allowed_file_types:
            return [f".{t.strip()}" for t in self.allowed_file_types.split(",")]
        return [".pdf", ".docx", ".txt"]
