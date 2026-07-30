frappe.query_reports["Skill Gap Analysis Report"] = {
    filters: [
        {fieldname:"skill",label:__("Skill"),fieldtype:"Link",options:"Skill"},
        {fieldname:"min_gap",label:__("Min Gap %"),fieldtype:"Percent"},
    ],
    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "gap_percentage" && value >= 80) {
            value = `<span class="text-danger font-weight-bold">${value}%</span>`;
        } else if (column.fieldname === "gap_percentage" && value >= 50) {
            value = `<span class="text-warning font-weight-bold">${value}%</span>`;
        }
        return value;
    }
};
