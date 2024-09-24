// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Timesheet Summary"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": __("From Date"),
			"default": last_week_date()
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": __("To Date"),
			"default": today_date()
		},
		{
			"fieldname": "employee",
			"fieldtype": "Link",
			"label": __("Employee"),
			"options": "Employee"
		},
		{
			"fieldname": "project",
			"fieldtype": "Link",
			"label": __("Project"),
			"options": "Project"
		},
		{
			"fieldname": "approval_status",
			"fieldtype": "Select",
			"label": __("Approval Status"),
			"options": ["", "Employee Pending", "RM Pending", "PM Pending", "HR Pending", "Approved"]
		}
	]
};

function today_date(){
	var date = new Date()
	return `${date.getFullYear()}-${date.getMonth()+1}-${date.getDate()}`
}

function last_week_date(){
	var date = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) 
	return `${date.getFullYear()}-${date.getMonth()+1}-${date.getDate()}`
}