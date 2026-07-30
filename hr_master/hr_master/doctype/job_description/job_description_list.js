// Job Description List View Script for HR Master
frappe.listview_settings["Job Description"] = {
    add_fields: [
        "job_title",
        "department",
        "status",
        "posting_date",
        "vacancies",
        "portal_search_status",
    ],
    filters: [["status", "!=", "Cancelled"]],
    get_indicator: function (doc) {
        const status_colors = {
            Draft: "gray",
            Open: "blue",
            "In Progress": "orange",
            Filled: "green",
            Closed: "red",
            Cancelled: "darkgray",
        };
        return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
    },
    button: {
        show: function (doc) {
            return doc.status === "Open";
        },
        get_label: function () {
            return __("Search");
        },
        get_description: function (doc) {
            return __("Search portals for {0}", [doc.job_title]);
        },
        action: function (doc) {
            frappe.call({
                method: "hr_master.api.search_api.search_candidates_for_jd",
                args: {
                    job_description_name: doc.name,
                },
                freeze: true,
                callback: function () {
                    frappe.msgprint(__("Search initiated for {0}", [doc.job_title]));
                },
            });
        },
    },
};
