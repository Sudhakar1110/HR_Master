frappe.query_reports["Recruitment Dashboard Report"] = {
    filters: [
        {fieldname:"from_date",label:__("From Date"),fieldtype:"Date"},
        {fieldname:"to_date",label:__("To Date"),fieldtype:"Date"},
        {fieldname:"status",label:__("Status"),fieldtype:"Select",options:["","New","Contacted","Screened","Shortlisted","Interview Scheduled","Selected","Rejected","On Hold"]},
        {fieldname:"source",label:__("Source"),fieldtype:"Select",options:["","LinkedIn","Naukri","Indeed","Internal Referral","Direct Apply","Other"]},
    ]
};
