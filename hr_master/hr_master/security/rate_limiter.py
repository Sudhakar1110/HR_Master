"""API Rate Limiting Module for HR Master

Enforces API rate limits based on Recruitment Settings configuration.
Uses Frappe cache to track request counts by user/IP.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
import time


def check_rate_limit(user=None, ip_address=None):
    """Check if the request is within rate limits.
    
    Returns dict with:
        - allowed: bool
        - remaining: int
        - reset_time: int (Unix timestamp)
        - retry_after: int (seconds)
    """
    try:
        settings = frappe.get_single("Recruitment Settings")
        if not settings.enable_rate_limiting:
            return {"allowed": True, "remaining": -1}

        max_requests = settings.max_api_requests_per_minute or 60
        user = user or frappe.session.user
        ip_address = ip_address or frappe.request_ip

        # Use user as primary key, IP as fallback
        key = f"hr_rate_limit:{user or ip_address}"
        cache = frappe.cache()

        # Get current window
        window_key = f"{key}:window"
        current_window = cache.get(window_key)
        now = int(time.time())
        window_start = current_window or now
        window_end = window_start + 60

        if not current_window:
            cache.set(window_key, now, expires_in_sec=120)

        # Get request count for current window
        count_key = f"{key}:count"
        current_count = cache.get(count_key) or 0

        # Check if window expired
        if now >= window_end:
            cache.set(window_key, now, expires_in_sec=120)
            cache.set(count_key, 1, expires_in_sec=120)
            return {
                "allowed": True,
                "remaining": max_requests - 1,
                "reset_time": now + 60,
                "retry_after": 0
            }

        if current_count >= max_requests:
            retry_after = window_end - now
            return {
                "allowed": False,
                "remaining": 0,
                "reset_time": window_end,
                "retry_after": retry_after
            }

        # Increment count
        cache.set(count_key, current_count + 1, expires_in_sec=120)

        return {
            "allowed": True,
            "remaining": max_requests - current_count - 1,
            "reset_time": window_end,
            "retry_after": 0
        }

    except Exception:
        # If rate limiting fails, allow request
        return {"allowed": True, "remaining": -1}


@frappe.whitelist()
def get_rate_limit_status():
    """Get current rate limit status for the requesting user."""
    result = check_rate_limit()
    return {
        "status": "success",
        "rate_limit": {
            "allowed": result["allowed"],
            "remaining": result["remaining"],
            "reset_time": result.get("reset_time"),
            "retry_after": result.get("retry_after", 0)
        }
    }


@frappe.whitelist()
def clear_rate_limit(user=None):
    """Clear rate limit for a specific user (Admin only)."""
    if "HR Master Admin" not in frappe.get_roles():
        return {"status": "error", "message": _("Permission denied")}

    key = f"hr_rate_limit:{user or frappe.session.user}"
    cache = frappe.cache()
    cache.delete(f"{key}:count")
    cache.delete(f"{key}:window")

    return {"status": "success", "message": _("Rate limit cleared")}


def rate_limit_decorator(f):
    """Decorator to apply rate limiting to API methods."""
    def wrapper(*args, **kwargs):
        result = check_rate_limit()
        if not result["allowed"]:
            frappe.throw(
                _("Rate limit exceeded. Try again in {0} seconds.").format(
                    result.get("retry_after", 60)
                ),
                frappe.RateLimitExceededError
            )
        return f(*args, **kwargs)
    return wrapper
