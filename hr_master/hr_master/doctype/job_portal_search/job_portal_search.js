// Job Portal Search Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Job Portal Search", {
    refresh: function (frm) {
        // Import candidates button
        if (
            frm.doc.status === "Completed" &&
            frm.doc.search_results &&
            frm.doc.search_results.length > 0
        ) {
            frm.add_custom_button(__("Import Candidates"), function () {
                frappe.call({
                    method:
                        "hr_master.api.search_api.import_search_results",
                    args: {
                        search_name: frm.doc.name,
                    },
                    freeze: true,
                    freeze_message: __("Importing candidates..."),
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint(
                                __("{0} candidates imported successfully", [
                                    r.message,
                                ])
                            );
                            frm.reload_doc();
                        }
                    },
                });
            }, __("Actions"));

            // Rank candidates button
            frm.add_custom_button(__("Rank Against JD"), function () {
                frappe.call({
                    method:
                        "hr_master.api.ranking_api.rank_candidates_from_search",
                    args: {
                        search_name: frm.doc.name,
                    },
                    freeze: true,
                    freeze_message: __("Ranking candidates..."),
                    callback: function (r) {
                        if (r.message && r.message.status === "success") {
                            frappe.msgprint(
                                __("Candidates ranked successfully")
                            );
                            frappe.set_route("List", "Candidate Ranking", {
                                job_description: frm.doc.job_description,
                            });
                        }
                    },
                });
            }, __("Actions"));
        }
    },
});
