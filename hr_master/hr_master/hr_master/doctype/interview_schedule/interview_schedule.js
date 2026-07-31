// Interview Schedule Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Interview Schedule", {
    refresh: function (frm) {
        if (frm.doc.status === "Completed" && !frm.doc.result) {
            frm.add_custom_button(__("Mark as Selected"), function () {
                frm.set_value("result", "Selected");
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Mark as Rejected"), function () {
                frm.set_value("result", "Rejected");
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Advance to Next Round"), function () {
                frm.set_value("result", "Advanced to Next Round");
                frm.save();
            }, __("Actions"));
        }

        if (frm.doc.status === "Scheduled") {
            frm.add_custom_button(__("Mark In Progress"), function () {
                frm.set_value("status", "In Progress");
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Reschedule"), function () {
                frm.set_value("status", "Rescheduled");
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Cancel Interview"), function () {
                frm.set_value("status", "Cancelled");
                frm.save();
            }, __("Actions"));
        }
    },

    candidate: function (frm) {
        if (frm.doc.candidate) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Candidate",
                    filters: { name: frm.doc.candidate },
                    fieldname: [
                        "candidate_name",
                        "email",
                        "current_title",
                        "current_company",
                    ],
                },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value("candidate_name", r.message.candidate_name);
                    }
                },
            });
        }
    },
});
