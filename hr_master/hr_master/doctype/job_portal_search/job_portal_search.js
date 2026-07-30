// Job Portal Search Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Job Portal Search", {
    refresh: function (frm) {
        // Status indicator
        if (frm.doc.status) {
            let colors = {
                "Draft": "gray",
                "In Progress": "orange",
                "Completed": "green",
                "Failed": "red",
                "Stopped": "darkgrey"
            };
            frm.dashboard.add_indicator(
                __("Search Status: {0}", [frm.doc.status]),
                colors[frm.doc.status] || "gray"
            );
        }

        if (!frm.is_new()) {
            frm.add_custom_button(__("Rank Candidates"), function () {
                frappe.call({
                    method: "hr_master.api.ranking_api.rank_candidates_from_search",
                    args: { search_name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Ranking candidates..."),
                    callback: function (r) {
                        if (r.message && r.message.status === "success") {
                            frappe.msgprint({
                                title: __("Ranking Complete"),
                                indicator: "green",
                                message: r.message.message
                            });
                        }
                    }
                });
            }, __("Actions"));

            frm.add_custom_button(__("View Results"), function () {
                frappe.set_route("List", "Candidate", {
                    source: frm.doc.name
                });
            }, __("View"));
        }
    }
});
