// Candidate Ranking Client Script for HR Master (ERPNext v15+)
frappe.ui.form.on("Candidate Ranking", {
    refresh: function (frm) {
        // Color code based on match score
        if (frm.doc.total_match_score !== undefined) {
            let color = "red";
            if (frm.doc.total_match_score >= 80) color = "green";
            else if (frm.doc.total_match_score >= 60) color = "blue";
            else if (frm.doc.total_match_score >= 40) color = "orange";

            frm.dashboard.add_indicator(
                __("Match Score: {0}%", [frm.doc.total_match_score]),
                color
            );
        }

        // View candidate profile
        if (frm.doc.candidate) {
            frm.add_custom_button(__("View Candidate"), function () {
                frappe.set_route("Form", "Candidate", frm.doc.candidate);
            }, __("View"));

            frm.add_custom_button(__("View JD"), function () {
                frappe.set_route("Form", "Job Description", frm.doc.job_description);
            }, __("View"));
        }

        // Shortlist action
        if (frm.doc.status === "Evaluated") {
            frm.add_custom_button(__("Shortlist"), function () {
                frm.set_value("status", "Shortlisted");
                frm.save();
            }, __("Actions"));

            frm.add_custom_button(__("Reject"), function () {
                frm.set_value("status", "Rejected");
                frm.save();
            }, __("Actions"));
        }

        // Schedule interview
        if (frm.doc.status === "Shortlisted") {
            frm.add_custom_button(__("Schedule Interview"), function () {
                frappe.new_doc("Interview Schedule", {
                    candidate: frm.doc.candidate,
                    candidate_name: frm.doc.candidate_name,
                    job_description: frm.doc.job_description,
                    job_title: frm.doc.job_title,
                });
            }, __("Actions"));
        }
    },
});
