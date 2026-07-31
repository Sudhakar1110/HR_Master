frappe.query_reports["Time-to-Hire Report"] = {
    filters: [
        {fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},
        {fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
        {fieldname:"recruiter",label:__("Recruiter"),fieldtype:"Link",options:"User"},
    ],
    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "days_to_hire" && value > 60) {
            value = `<span class="text-danger font-weight-bold">${value}</span>`;
        } else if (column.fieldname === "days_to_hire" && value > 30) {
            value = `<span class="text-warning font-weight-bold">${value}</span>`;
        }
        return value;
    }
};
