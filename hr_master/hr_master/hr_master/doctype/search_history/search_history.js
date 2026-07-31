// Search History Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Search History", {
    refresh: function (frm) {
        if (frm.doc.search_type) {
            frm.dashboard.add_indicator(
                __("Search Type: {0}", [frm.doc.search_type]),
                "blue"
            );
        }

        if (frm.doc.result_count !== undefined) {
            frm.dashboard.add_indicator(
                __("Results: {0}", [frm.doc.result_count]),
                frm.doc.result_count > 0 ? "green" : "orange"
            );
        }

        if (frm.doc.ref_name && frm.doc.ref_doctype) {
            frm.add_custom_button(__("View Reference"), function () {
                frappe.set_route("Form", frm.doc.ref_doctype, frm.doc.ref_name);
            }, __("View"));
        }

        // Re-run this search
        if (frm.doc.search_query && frm.doc.search_type === "Candidate") {
            frm.add_custom_button(__("Re-run Search"), function () {
                frappe.call({
                    method: "hr_master.api.search_api.advanced_candidate_search",
                    args: {
                        search_text: frm.doc.search_query,
                        filters: frm.doc.filters_used ? JSON.parse(frm.doc.filters_used) : {}
                    },
                    freeze: true,
                    freeze_message: __("Searching..."),
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint({
                                title: __("Search Complete"),
                                indicator: "green",
                                message: __("Found {0} results", [r.message.length])
                            });
                        }
                    }
                });
            }, __("Actions"));
        }
    }
});
