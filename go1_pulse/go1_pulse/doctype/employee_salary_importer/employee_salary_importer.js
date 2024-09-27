// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Salary Importer', {
	refresh: function(frm){
		if (frm.doc.docstatus === 1 && !frm.doc.cost_allocation_reference){
			frm.add_custom_button(__("Process Cost Allocation"), function () {
			frappe.call({
				method: "go1_pulse.go1_pulse.doctype.employee_salary_importer.employee_salary_importer.create_timesheet_aggregator",
				freeze:true,
				freeze_message: "Creating Cost Allocation", 
				args: {
					start_date: frm.doc.start_date,
					end_date: frm.doc.end_date,
				},
				callback: function (r) {
					console.log(r)
					frm.set_value("cost_allocation_reference" , r.message);
					frm.save("Update")
					}
				}); 
			});
		}
		if (frm.doc.cost_allocation_reference){
			frm.add_custom_button(__("Cost Allocation Details"), function () {
				frappe.set_route("query-report", "Employee Cost Allocation", { "timesheet_aggregator": frm.doc.cost_allocation_reference })	
			});
		}
	},
	start_date: function (frm) {
		let end_date = frappe.datetime.add_days(frappe.datetime.add_months(frm.doc.start_date, 1), -1);
		frm.set_value("end_date", end_date);
	},

	end_date: function (frm) {
		frappe.call({
			method: "go1_pulse.go1_pulse.doctype.employee_salary_importer.employee_salary_importer.get_employee_list",
			args: { start_date: frm.start_date, end_date: frm.end_date },
			async: false,
			freeze: true, freeze_message: __("Getting Employee Data"),
			callback: (res) => {
				if (!res.exc) {
					if (res.message.length > 0) {
						res.message.forEach((element) => {
							frm.add_child("salary_details", element)
						})
					}
				}
			}
		})
		frm.refresh_field('salary_details');
	},
});
