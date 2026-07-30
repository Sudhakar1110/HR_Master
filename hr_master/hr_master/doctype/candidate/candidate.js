// Candidate Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Candidate", {
    refresh: function (frm) {
        if (!frm.is_new()) {
            // View candidate rankings
            frm.add_custom_button(__("View Rankings"), function () {
                frappe.set_route("List", "Candidate Ranking", {
                    candidate: frm.doc.name,
                });
            }, __("View"));

            // Schedule interview
            frm.add_custom_button(__("Schedule Interview"), function () {
                frappe.new_doc("Interview Schedule", {
                    candidate: frm.doc.name,
                    candidate_name: frm.doc.candidate_name,
                    email: frm.doc.email,
                });
            }, __("Actions"));

            // Shortlist candidate
            if (frm.doc.status === "New" || frm.doc.status === "Contacted" || frm.doc.status === "Screened") {
                frm.add_custom_button(__("Shortlist"), function () {
                    frm.set_value("status", "Shortlisted");
                    frm.save();
                }, __("Actions"));
            }
        }
    },

    resume_attachment: function (frm) {
        if (frm.doc.resume_attachment) {
            frappe.call({
                method: "hr_master.api.candidate_api.parse_resume",
                args: {
                    candidate_name: frm.doc.name,
                    file_url: frm.doc.resume_attachment,
                },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value("resume_text", r.message.resume_text);
                        if (r.message.skills) {
                            frm.set_value("parsed_skills_from_resume", r.message.skills.join(", "));
                        }
                    }
                },
            });
        }
    },
});
