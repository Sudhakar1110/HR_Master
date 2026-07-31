// Email Template Config Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Email Template Config", {
    refresh: function (frm) {
        if (frm.doc.is_active) {
            frm.dashboard.add_indicator(__("Active"), "green");
        } else {
            frm.dashboard.add_indicator(__("Inactive"), "red");
        }

        if (!frm.is_new()) {
            frm.add_custom_button(__("Preview Template"), function () {
                let d = new frappe.ui.Dialog({
                    title: __("Email Preview"),
                    fields: [
                        {
                            fieldtype: "Data",
                            fieldname: "candidate_name",
                            label: __("Candidate Name"),
                            default: "John Doe"
                        },
                        {
                            fieldtype: "Data",
                            fieldname: "job_title",
                            label: __("Job Title"),
                            default: "Software Engineer"
                        },
                        {
                            fieldtype: "Data",
                            fieldname: "company_name",
                            label: __("Company Name"),
                            default: "Acme Corp"
                        }
                    ],
                    primary_action_label: __("Preview"),
                    primary_action: function (vals) {
                        frappe.call({
                            method: "hr_master.hr_master.doctype.email_template_config.email_template_config.render_template",
                            args: {
                                template_name: frm.doc.name,
                                context: vals
                            },
                            callback: function (r) {
                                if (r.message) {
                                    let preview = new frappe.ui.Dialog({
                                        title: __("Email Preview: {0}", [r.message.subject]),
                                        fields: [
                                            {
                                                fieldtype: "HTML",
                                                fieldname: "preview",
                                                options: r.message.use_html
                                                    ? r.message.message
                                                    : `<pre>${r.message.message}</pre>`
                                            }
                                        ],
                                        primary_action_label: __("Close"),
                                        primary_action: function () {
                                            preview.hide();
                                        }
                                    });
                                    preview.show();
                                }
                            }
                        });
                    }
                });
                d.show();
            }, __("Actions"));

            frm.add_custom_button(__("Use as Default"), function () {
                frappe.call({
                    method: "frappe.client.set_value",
                    args: {
                        doctype: "Email Template Config",
                        name: frm.doc.name,
                        fieldname: "is_active",
                        value: 1
                    },
                    callback: function () {
                        frappe.msgprint(__("Template set as active"));
                        frm.reload_doc();
                    }
                });
            }, __("Actions"));
        }
    }
});
