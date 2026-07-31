// Candidate Activity Log Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Candidate Activity Log", {
    refresh: function (frm) {
        if (frm.doc.activity_type) {
            let colors = {
                "Created": "blue",
                "Contacted": "orange",
                "Screened": "purple",
                "Shortlisted": "green",
                "Interview Scheduled": "cyan",
                "Hired": "green",
                "Rejected": "red",
                "Offer Made": "yellow"
            };
            let color = colors[frm.doc.activity_type] || "gray";
            frm.dashboard.add_indicator(__("{0}", [frm.doc.activity_type]), color);
        }

        if (frm.doc.candidate) {
            frm.add_custom_button(__("View Candidate"), function () {
                frappe.set_route("Form", "Candidate", frm.doc.candidate);
            }, __("View"));
        }

        if (frm.doc.reference_name && frm.doc.reference_doctype) {
            frm.add_custom_button(__("View Reference"), function () {
                frappe.set_route("Form", frm.doc.reference_doctype, frm.doc.reference_name);
            }, __("View"));
        }
    },

    candidate: function (frm) {
        if (frm.doc.candidate) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Candidate",
                    filters: { name: frm.doc.candidate },
                    fieldname: ["candidate_name"]
                },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value("candidate_name", r.message.candidate_name);
                    }
                }
            });
        }
    }
});
