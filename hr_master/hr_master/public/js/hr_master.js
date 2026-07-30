// HR Master - Public JavaScript
// Client-side utilities for the HR Master module

frappe.provide("hr_master");

hr_master = {
    // Initialize HR Master module
    init: function () {
        this.bind_events();
    },

    // Bind global events
    bind_events: function () {
        // Add custom navigation items
        frappe.after("page_ready", function () {
            hr_master.add_workspace_shortcut();
        });
    },

    // Add workspace shortcut
    add_workspace_shortcut: function () {
        if (
            frappe.boot.hr_master &&
            frappe.boot.hr_master.has_access
        ) {
            // Workspace is automatically loaded by Frappe
        }
    },

    // Format match score with color
    format_match_score: function (score) {
        if (score === null || score === undefined) return "N/A";
        let color = "red";
        if (score >= 80) color = "green";
        else if (score >= 60) color = "blue";
        else if (score >= 40) color = "orange";
        return `<span style="color: ${color}; font-weight: bold;">${score}%</span>`;
    },
};

// Initialize on document ready
$(document).ready(function () {
    hr_master.init();
});
