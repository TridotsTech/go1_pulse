// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Timesheet Aggregator', {

	refresh: function(frm) {
		if (frm.doc.docstatus == 1){
			frm.add_custom_button(__('Create Expense'), () =>
				frm.trigger("make_journal")
			);
		}
	},
	
	make_journal: function(frm){
		let fields = [{
			"fieldtype": "Link",
			"label": __("Account"),
			"fieldname": "account",
			"options": "Account"
		}];

		let dialog = new frappe.ui.Dialog({
			title: __("Create Journal Entry"),
			fields: fields
		});

		dialog.set_primary_action(__('Create Journal Entry'), () => {
			var args = dialog.get_values();
			if(!args) return;
			dialog.hide();
			return frappe.call({
				type: "GET",
				method: "go1_pulse.go1_pulse.doctype.timesheet_aggregator.timesheet_aggregator.make_journal_entry",
				args: {
					"source_name": frm.doc.name,
					"account": args.account,
				},
				freeze: true,
				callback: function(r) {
					if(!r.exc) {
						frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				}
			});
		});
		dialog.show();
	},
	

	start_date: function (frm) {
		let end_date = frappe.datetime.add_days(frappe.datetime.add_months(frm.doc.start_date, 1), -1);
		frm.set_value("end_date", end_date);
	},
	
	
	get_details: function(frm) {
		if(frm.doc.start_date && frm.doc.end_date){
			frappe.call({
				method: "go1_pulse.go1_pulse.doctype.timesheet_aggregator.timesheet_aggregator.get_customer_timesheets",
				freeze: true,
				freeze_message: "Fetching Timesheet Details",
				args: {
					start_date: frm.doc.start_date,
					end_date: frm.doc.end_date,
				},
				callback: function(r) {
					cur_frm.doc.details = [];
					r.message.details.forEach(function (item) {
						let row = frm.add_child("details");
						row.employee = item.employee;
						row.employee_worked_hours = item.hours;
						row.cost_center = item.cost_center;
						row.billing_amount = item.billing_amount;
						row.project = item.project;
						row.employee_worked_days = item.employee_worked_days;
						row.total_working_days = item.total_working_days;
						row.salary_amount = item.salary_amount;
						row.cost_per_hour = item.cost_per_hour;
					});
					frm.doc.total_hours = r.message.total_hours;
					frm.doc.billable_amount = r.message.billable_amount;
					frm.doc.total_ctc = r.message.total_ctc;
					frm.refresh_fields()
				}
			});
		}
		else{
			frappe.msgprint(__("<b>Start-date</b> and <b>End-Date</b> Can't be empty"))
		}
	}
});
