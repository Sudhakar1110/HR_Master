// Job Description Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Job Description", {
    refresh: function (frm) {
        // Add custom buttons
        if (!frm.is_new() && frm.doc.status === "Open") {
            frm.add_custom_button(__("Search Portals"), function () {
                search_candidates(frm);
            }, __("Actions"));

            frm.add_custom_button(__("Rank Candidates"), function () {
                rank_candidates(frm);
            }, __("Actions"));
        }

        if (!frm.is_new()) {
            frm.add_custom_button(__("View Rankings"), function () {
                frappe.set_route("List", "Candidate Ranking", {
                    job_description: frm.doc.name,
                });
            }, __("View"));
        }

        // Show portal search status indicator
        if (frm.doc.portal_search_status === "Searching") {
            frm.dashboard.set_headline(
                __(
                    '<span class="text-warning">⏳ Portal search in progress...</span>'
                )
            );
        } else if (frm.doc.portal_search_status === "Searched") {
            frm.dashboard.set_headline(
                __(
                    '<span class="text-success">✅ Portal search completed</span>'
                )
            );
        } else if (frm.doc.portal_search_status === "Error") {
            frm.dashboard.set_headline(
                __(
                    '<span class="text-danger">❌ Portal search failed</span>'
                )
            );
        }
    },

    job_description_raw: function (frm) {
        // Auto-parse skills when JD text is entered
        if (frm.doc.job_description_raw && !frm.is_new()) {
            frappe.call({
                method: "hr_master.api.jd_api.parse_skills_from_jd",
                args: {
                    jd_text: frm.doc.job_description_raw,
                },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value("parsed_skills", r.message.join(", "));
                    }
                },
            });
        }
    },

    onload: function (frm) {
        // Set default posting date
        if (frm.is_new()) {
            frm.set_value("posting_date", frappe.datetime.get_today());
        }
    },
});

// Helper functions
function search_candidates(frm) {
    frappe.call({
        method: "hr_master.api.search_api.search_candidates_for_jd",
        args: {
            job_description_name: frm.doc.name,
        },
        freeze: true,
        freeze_message: __("Searching job portals..."),
        callback: function (r) {
            if (r.message && r.message.status === "success") {
                frappe.msgprint({
                    title: __("Search Initiated"),
                    indicator: "green",
                    message: __(
                        "Portal search has been initiated in the background. Results will be available shortly."
                    ),
                });
                frm.reload_doc();
            } else {
                frappe.msgprint({
                    title: __("Search Error"),
                    indicator: "red",
                    message: r.message
                        ? r.message.message
                        : __("Failed to initiate search"),
                });
            }
        },
        error: function (err) {
            frappe.msgprint({
                title: __("Error"),
                indicator: "red",
                message: __("An error occurred while searching portals."),
            });
        },
    });
}

function rank_candidates(frm) {
    frappe.call({
        method: "hr_master.api.ranking_api.rank_all_candidates_for_jd",
        args: {
            job_description_name: frm.doc.name,
        },
        freeze: true,
        freeze_message: __("Ranking candidates..."),
        callback: function (r) {
            if (r.message && r.message.status === "success") {
                frappe.msgprint({
                    title: __("Ranking Complete"),
                    indicator: "green",
                    message: __(
                        "Candidates have been ranked against the job description."
                    ),
                });
                frappe.set_route("List", "Candidate Ranking", {
                    job_description: frm.doc.name,
                });
            } else {
                frappe.msgprint({
                    title: __("Ranking Error"),
                    indicator: "red",
                    message: r.message
                        ? r.message.message
                        : __("Failed to rank candidates"),
                });
            }
        },
        error: function (err) {
            frappe.msgprint({
                title: __("Error"),
                indicator: "red",
                message: __(
                    "An error occurred while ranking candidates."
                ),
            });
        },
    });
}
