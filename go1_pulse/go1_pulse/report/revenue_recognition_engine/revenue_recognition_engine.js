// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Revenue Recognition Engine"] = {
	"filters": [
		{
			"fieldname": "revenue_type",
			"label": __("Revenue Type"),
			"fieldtype": "Select",
			"options": ["POC", "Equal revenue over the contract period"],
			"default": "POC"
		},
		{
			"fieldname": "posting_date",
			"label": __("Posting Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		}
	],
	after_datatable_render: table_instance => {
		frappe.query_report.datatable.options.checkboxColumn = true
	},
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true
		});
	},
	onload: function (report) {
		report.page.add_inner_button(__("Make Journal"), function () {
			frappe.confirm('Are you sure you want to proceed?',()=>{
				let dialog = new frappe.ui.Dialog({
					title: __("Select Account"),
					fields: [
						{
							"label": __("Posting Date"),
							"fieldname": "posting_date",
							"fieldtype": "Date",
							"default": frappe.query_report.filters[1].value,
							"reqd": 1,
							"read_only":1
						}
					],
					primary_action: function () {
						let exp_type = frappe.query_report.filters[0].value
						
						const visible_idx = report.datatable.rowmanager.getCheckedRows().map(i => Number(i));
						if (visible_idx.length == 0) {
							frappe.throw("Please Select a row for Make Journal")
						}
						var selected_rows = [];
						let indexes = report.datatable.rowmanager.getCheckedRows();
						for (let row = 0; row < indexes.length; ++row) {
							selected_rows.push({ "Data": report.data[indexes[row]] });
						}
						
						if(exp_type){
							const date = dialog.get_values();
							frappe.call({
								method: "go1_pulse.go1_pulse.doctype.common_project_mapper.common_project_mapper.make_journal_for_expense",
								freeze: true,
								freeze_message: __("Creating Journal"),
								args: {
									expense_type : exp_type,
									datas: selected_rows,
									posting_date: date.posting_date,
								},
							});
						}
						dialog.hide();
					},
					primary_action_label: __("Create Journal Entry")
				});
			dialog.show();
		});
		})
		report.page.add_inner_button(__("View Journals"), function () {
			const date =  frappe.query_report.filters[1].value
			frappe.set_route("journal-entry", { "is_from_report": 1, "creation": ['<', frappe.datetime.add_days(date, 1)]})
		})
	}
};

