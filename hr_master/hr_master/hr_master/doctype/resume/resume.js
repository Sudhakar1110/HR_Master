// Resume Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Resume", {
    refresh: function (frm) {
        if (frm.doc.parsing_status) {
            let color = {
                "Pending": "orange",
                "Processing": "blue",
                "Completed": "green",
                "Failed": "red"
            }[frm.doc.parsing_status] || "gray";

            frm.dashboard.add_indicator(
                __("Parsing: {0}", [frm.doc.parsing_status]),
                color
            );
        }

        if (!frm.is_new() && frm.doc.parsing_status === "Pending") {
            frm.add_custom_button(__("Parse Now"), function () {
                frappe.call({
                    method: "frappe.client.get_value",
                    args: {
                        doctype: "Resume",
                        filters: { name: frm.doc.name },
                        fieldname: ["name"]
                    },
                    callback: function () {
                        frappe.call({
                            method: "hr_master.hr_master.doctype.resume.resume.create_resume_from_attachment",
                            args: {
                                candidate_name: frm.doc.candidate,
                                file_url: frm.doc.resume_file
                            },
                            freeze: true,
                            freeze_message: __("Parsing resume..."),
                            callback: function () {
                                frm.reload_doc();
                            }
                        });
                    }
                });
            }, __("Actions"));
        }

        if (frm.doc.candidate) {
            frm.add_custom_button(__("View Candidate"), function () {
                frappe.set_route("Form", "Candidate", frm.doc.candidate);
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
    },

    resume_file: function (frm) {
        if (frm.doc.resume_file) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "File",
                    filters: { file_url: frm.doc.resume_file },
                    fieldname: ["file_size"]
                },
                callback: function (r) {
                    if (r.message && r.message.file_size) {
                        frm.set_value("file_size_kb", Math.round(r.message.file_size / 1024));
                    }
                }
            });
        }
    }
});
