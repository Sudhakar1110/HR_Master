// Offer Management Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Offer Management", {
    refresh: function (frm) {
        if (frm.doc.status) {
            let colors = {
                "Draft": "gray",
                "Approval Pending": "orange",
                "Approved": "blue",
                "Offer Sent": "purple",
                "Negotiation": "orange",
                "Accepted": "green",
                "Declined": "red",
                "Withdrawn": "darkgrey"
            };
            frm.dashboard.add_indicator(
                __("Status: {0}", [frm.doc.status]),
                colors[frm.doc.status] || "gray"
            );
        }

        if (!frm.is_new()) {
            if (frm.doc.status === "Approved") {
                frm.add_custom_button(__("Send Offer"), function () {
                    frm.set_value("status", "Offer Sent");
                    frm.save();
                }, __("Actions"));
            }

            if (frm.doc.status === "Offer Sent") {
                frm.add_custom_button(__("Candidate Accepted"), function () {
                    frm.set_value("status", "Accepted");
                    frm.save();
                }, __("Actions"));

                frm.add_custom_button(__("Candidate Declined"), function () {
                    frm.set_value("status", "Declined");
                    frm.save();
                }, __("Actions"));

                frm.add_custom_button(__("Enter Negotiation"), function () {
                    frm.set_value("status", "Negotiation");
                    frm.save();
                }, __("Actions"));
            }

            if (frm.doc.status === "Draft") {
                frm.add_custom_button(__("Request Approval"), function () {
                    frm.set_value("status", "Approval Pending");
                    frm.save();
                }, __("Actions"));
            }

            if (frm.doc.candidate) {
                frm.add_custom_button(__("View Candidate"), function () {
                    frappe.set_route("Form", "Candidate", frm.doc.candidate);
                }, __("View"));

                frm.add_custom_button(__("Generate Offer Letter"), function () {
                    frappe.call({
                        method: "hr_master.api.candidate_api.get_candidate_details",
                        args: { candidate_name: frm.doc.candidate },
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint({
                                    title: __("Generate Offer Letter"),
                                    indicator: "green",
                                    message: __("Offer letter generation initiated for {0}", [frm.doc.candidate_name])
                                });
                            }
                        }
                    });
                }, __("Documents"));
            }
        }

        // Quick edit compensation
        if (!frm.is_new() && (frm.doc.status === "Draft" || frm.doc.status === "Negotiation")) {
            frm.add_custom_button(__("Recalculate CTC"), function () {
                let base = frm.doc.base_salary || 0;
                let variable = frm.doc.variable_pay || 0;
                frm.set_value("total_ctc", base + variable);
                frappe.show_alert({
                    message: __("CTC recalculated: {0}", [format_currency(base + variable)]),
                    indicator: "green"
                });
            }, __("Actions"));
        }
    },

    base_salary: function (frm) {
        calculate_ctc(frm);
    },

    variable_pay: function (frm) {
        calculate_ctc(frm);
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

function calculate_ctc(frm) {
    let base = frm.doc.base_salary || 0;
    let variable = frm.doc.variable_pay || 0;
    if (base > 0 || variable > 0) {
        frm.set_value("total_ctc", base + variable);
    }
}
