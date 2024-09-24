// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Recognised Revenue Report"] = {
	"filters": [
		{
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
		},
		{
			"fieldname": "profit_center",
			"label": __("Profi Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
		},
		{
			"fieldname": "lob",
			"label": __("LOB"),
			"fieldtype": "Link",
			"options": "Line of Business",
		},
		{
			"fieldname": "mandate",
			"label": __("Mandate"),
			"fieldtype": "Link",
			"options": "Mandate",
		},
		{
			"fieldname": "offering",
			"label": __("Offering"),
			"fieldtype": "Link",
			"options": "Offering",
		}

	]
};
 