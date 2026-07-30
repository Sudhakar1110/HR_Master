// Recruitment Settings Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Recruitment Settings", {
    refresh: function (frm) {
        // Indicate rate limiting status
        if (frm.doc.enable_rate_limiting) {
            frm.dashboard.add_indicator(
                __("Rate Limiting: {0} req/min", [frm.doc.max_api_requests_per_minute]),
                "blue"
            );
        }

        if (frm.doc.enable_audit_logging) {
            frm.dashboard.add_indicator(__("Audit Logging: Enabled"), "green");
        }

        frm.add_custom_button(__("Test Email Config"), function () {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Recruitment Settings",
                    filters: { name: "Recruitment Settings" },
                    fieldname: ["cc_emails"]
                },
                callback: function (r) {
                    if (r.message && r.message.cc_emails) {
                        frappe.msgprint({
                            title: __("Configuration Valid"),
                            indicator: "green",
                            message: __("Email configuration is set. CC recipients: {0}", [r.message.cc_emails])
                        });
                    } else {
                        frappe.msgprint({
                            title: __("Info"),
                            indicator: "orange",
                            message: __("No CC emails configured.")
                        });
                    }
                }
            });
        }, __("Test"));

        frm.add_custom_button(__("Run Duplicate Scan"), function () {
            frappe.call({
                method: "hr_master.tasks.duplicate_detection.scan_for_duplicates",
                freeze: true,
                freeze_message: __("Scanning for duplicates..."),
                callback: function () {
                    frappe.msgprint({
                        title: __("Scan Complete"),
                        indicator: "green",
                        message: __("Duplicate detection scan completed. Check Candidate Activity Log for results.")
                    });
                }
            });
        }, __("Actions"));

        frm.add_custom_button(__("Generate Weekly Report Now"), function () {
            frappe.call({
                method: "hr_master.tasks.weekly.generate_weekly_report",
                freeze: true,
                freeze_message: __("Generating report..."),
                callback: function () {
                    frappe.msgprint({
                        title: __("Report Generated"),
                        indicator: "green",
                        message: __("Weekly report generation completed.")
                    });
                }
            });
        }, __("Reports"));
    },

    enable_rate_limiting: function (frm) {
        if (frm.doc.enable_rate_limiting) {
            frappe.confirm(
                __("Enabling API rate limiting will restrict API requests. Are you sure?"),
                function () {},
                function () {
                    frm.set_value("enable_rate_limiting", 0);
                }
            );
        }
    },

    max_resume_size_kb: function (frm) {
        if (frm.doc.max_resume_size_kb > 51200) {
            frappe.msgprint({
                title: __("Warning"),
                indicator: "orange",
                message: __("Max resume size exceeds 50MB. This may cause performance issues.")
            });
        }
    }
});
