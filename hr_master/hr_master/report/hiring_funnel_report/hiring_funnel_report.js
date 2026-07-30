frappe.query_reports["Hiring Funnel Report"] = {
    filters: [
        {fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},
        {fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
        {fieldname:"job_description",label:__("Job Description"),fieldtype:"Link","options":"Job Description"},
    ]
};
