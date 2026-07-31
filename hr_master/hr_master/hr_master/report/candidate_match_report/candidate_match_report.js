// Candidate Match Report Script for HR Master (ERPNext v15+)
frappe.query_reports["Candidate Match Report"] = {
    filters: [
        {
            fieldname: "job_description",
            label: __("Job Description"),
            fieldtype: "Link",
            options: "Job Description",
        },
        {
            fieldname: "candidate",
            label: __("Candidate"),
            fieldtype: "Link",
            options: "Candidate",
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: [
                "",
                "Pending",
                "Evaluated",
                "Shortlisted",
                "Interview Scheduled",
                "Rejected",
                "On Hold",
            ],
        },
        {
            fieldname: "recommendation",
            label: __("Recommendation"),
            fieldtype: "Select",
            options: [
                "",
                "Strong Yes",
                "Yes",
                "Maybe",
                "No",
                "Strong No",
            ],
        },
        {
            fieldname: "min_score",
            label: __("Min Match Score"),
            fieldtype: "Percent",
        },
        {
            fieldname: "max_score",
            label: __("Max Match Score"),
            fieldtype: "Percent",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
        },
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "total_match_score") {
            if (value >= 80) {
                value = `<span class="text-success font-weight-bold">${value}</span>`;
            } else if (value >= 60) {
                value = `<span class="text-info font-weight-bold">${value}</span>`;
            } else if (value >= 40) {
                value = `<span class="text-warning font-weight-bold">${value}</span>`;
            } else {
                value = `<span class="text-danger font-weight-bold">${value}</span>`;
            }
        }

        if (column.fieldname === "ranking_order" && value === 1) {
            value = `<span class="text-success font-weight-bold">🥇 ${value}</span>`;
        } else if (column.fieldname === "ranking_order" && value === 2) {
            value = `<span class="text-info font-weight-bold">🥈 ${value}</span>`;
        } else if (column.fieldname === "ranking_order" && value === 3) {
            value = `<span class="text-warning font-weight-bold">🥉 ${value}</span>`;
        }

        return value;
    },

    onload: function (report) {
        // Add a button to export to CSV
        report.page.add_inner_button(__("Export Top 10"), function () {
            frappe.query_report.export_report("CSV");
        });
    },
};
