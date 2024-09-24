# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	return get_columns(filters), get_data(filters)

def get_columns(filters):
	columns = [
		{
			"fieldname": "employee",
			"label": "Employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150,
		},
		{
			"fieldname": "project",
			"label": "Project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 150,
		}, 
		{
			"fieldname": "cost_center",
			"label": "Cost Center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 150,
		},
		{
			"fieldname": "total_working_days",
			"label": "Working Days",
			"fieldtype": "Float",
			"width": 150,
		},
		{
			"fieldname": "employee_worked_days",
			"label": "Worked Days",
			"fieldtype": "Float",
			"width": 150,
		},
		{
			"fieldname": "employee_worked_hours",
			"label": "Worked Hours",
			"fieldtype": "Float",
			"width": 150,
		},
		{
			"fieldname": "billing_amount",
			"label": "Billing Amount",
			"fieldtype": "Currency",
			"width": 150,
		},
		]
	
	return columns

def get_data(filters):
	return frappe.get_all("Timesheet Aggregator Detail", {"parent": filters.get("timesheet_aggregator")},
      	['employee', 'project', 'total_working_days', 'employee_worked_days', 'employee_worked_hours', 'billing_amount', 'cost_center']
        )
