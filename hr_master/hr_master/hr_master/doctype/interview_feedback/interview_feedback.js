// Interview Feedback Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Interview Feedback", {
    refresh: function (frm) {
        if (frm.doc.recommendation) {
            let colors = {
                "Strong Hire": "green",
                "Hire": "green",
                "Lean Hire": "blue",
                "No Decision": "orange",
                "Lean No": "orange",
                "No": "red",
                "Strong No": "red"
            };
            frm.dashboard.add_indicator(
                __("Recommendation: {0}", [frm.doc.recommendation]),
                colors[frm.doc.recommendation] || "gray"
            );
        }

        if (frm.doc.result) {
            let result_colors = {
                "Selected": "green",
                "Rejected": "red",
                "On Hold": "orange",
                "Advanced to Next Round": "blue"
            };
            frm.dashboard.add_indicator(
                __("Result: {0}", [frm.doc.result]),
                result_colors[frm.doc.result] || "gray"
            );
        }

        if (frm.doc.candidate) {
            frm.add_custom_button(__("View Candidate"), function () {
                frappe.set_route("Form", "Candidate", frm.doc.candidate);
            }, __("View"));
        }

        if (frm.doc.interview_schedule) {
            frm.add_custom_button(__("View Interview"), function () {
                frappe.set_route("Form", "Interview Schedule", frm.doc.interview_schedule);
            }, __("View"));
        }

        if (!frm.is_new()) {
            frm.add_custom_button(__("New Feedback for Same Candidate"), function () {
                frappe.new_doc("Interview Feedback", {
                    candidate: frm.doc.candidate,
                    candidate_name: frm.doc.candidate_name,
                    job_title: frm.doc.job_title
                });
            }, __("Actions"));
        }
    },

    interview_schedule: function (frm) {
        if (frm.doc.interview_schedule) {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Interview Schedule",
                    filters: { name: frm.doc.interview_schedule },
                    fieldname: ["candidate", "candidate_name", "job_title", "interview_round"]
                },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value("candidate", r.message.candidate);
                        frm.set_value("candidate_name", r.message.candidate_name);
                        frm.set_value("job_title", r.message.job_title);
                        if (!frm.doc.interview_round) {
                            frm.set_value("interview_round", r.message.interview_round);
                        }
                    }
                }
            });
        }
    }
});
