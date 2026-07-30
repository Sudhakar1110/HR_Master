// JD Analysis Report Script for HR Master (ERPNext v15+)
frappe.query_reports["JD Analysis Report"] = {
    filters: [
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: [
                "",
                "Draft",
                "Open",
                "In Progress",
                "Filled",
                "Closed",
                "Cancelled",
            ],
        },
        {
            fieldname: "job_title",
            label: __("Job Title"),
            fieldtype: "Data",
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

        if (column.fieldname === "avg_match_score" && value) {
            if (value >= 70) {
                value = `<span class="text-success font-weight-bold">${value}%</span>`;
            } else if (value >= 50) {
                value = `<span class="text-warning font-weight-bold">${value}%</span>`;
            } else {
                value = `<span class="text-danger font-weight-bold">${value}%</span>`;
            }
        }

        return value;
    },
};
