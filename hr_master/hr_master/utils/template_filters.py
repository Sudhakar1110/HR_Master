"""Template filter utilities for HR Master Jinja rendering"""

from __future__ import unicode_literals


def get_match_color(score):
    """Return Bootstrap color class based on match score."""
    if score is None:
        return "secondary"
    if score >= 80:
        return "success"
    if score >= 60:
        return "info"
    if score >= 40:
        return "warning"
    return "danger"


def format_score(score):
    """Format a match score for display."""
    if score is None:
        return "N/A"
    return f"{score:.1f}%"
