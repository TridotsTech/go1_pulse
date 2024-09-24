// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employee Cost Allocation"] = {
	"filters": [
		{
			"fieldname": "timesheet_aggregator",
			"label": __("Timesheet Aggregator"),
			"fieldtype": "Link",
			"options": "Timesheet Aggregator",
			"reqd": 1,
			"read_only": 1
		},
	],

	onload: function (report) {
		report.page.add_inner_button(__("Make Journal"), function () {
			let dialog = new frappe.ui.Dialog({
				title: __("Select Account"),
				fields: [{
						"label": __("Account"),
						"fieldname": "account",
						"fieldtype": "Link",
						"options": "Account",
						"reqd": 1,
					},
					{
						"label": __("Posting Date"),
						"fieldname": "posting_date",
						"fieldtype": "Date",
						"reqd": 1,
					}],

				primary_action: function(){
					var args = dialog.get_values();
					frappe.call({
						method: "go1_pulse.go1_pulse.doctype.employee_salary_importer.employee_salary_importer.make_journal_entry",
						args: {
							"datas": report.data.slice(0, -1),
							"args": args,
							"ta_name": frappe.query_report.filters[0].value
						},
						callback: function (res) {
							
							if (res.message) {
								frappe.model.sync(res.message);
								frappe.set_route("Form", res.message.doctype, res.message.name);
							}
						}
					});
					dialog.hide();
				},
				
				primary_action_label: __("Create Journal Entry")
			});
			dialog.show();
		})		
	}
};

