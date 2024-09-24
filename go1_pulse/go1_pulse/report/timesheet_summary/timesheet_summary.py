# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
	columns = [
		{
			"fieldname": "id",
			"label": "ID",
			"fieldtype": 'Link',
			"options": "Timesheet",
		},
		{
			"fieldname": "title",
			"label": "Title",
			"fieldtype": 'Data',
		},
		{
			"fieldname": "status",
			"label": "Status",
			"fieldtype": 'Data',
		},
		{
			"fieldname": "employee",
			"label": "Employee",
			"fieldtype": 'Link',
			"options": "Employee"
		},
		{
			"fieldname": "log_date",
			"label": "Start Date",
			"fieldtype": 'Date',
		},
		{
			"fieldname": "actual_hours",
			"label": "Hours Recorded",
			"fieldtype": 'Data',
		},
		{
			"fieldname": "hours",
			"label": "Hours Approved",
			"fieldtype": 'Data',
		},
		{
			"fieldname": "is_modified",
			"label": "Is Modified",
			"fieldtype": "Select",
			"options": ["Yes","No"],
		},
		{
			"fieldname": "approval_status",
			"label": "Approval Status",
			"fieldtype": 'Data',
		}
	]
	return columns

def get_data(filters):
	conditions = ""
	if filters.get("from_date"):
		conditions += f" AND TS.log_date >= '{filters.get('from_date')}'"
	if filters.get("to_date"):
		conditions += f" AND TS.log_date <= '{filters.get('to_date')}'"
	if filters.get("employee"):
		conditions += f" AND TS.employee = '{filters.get('employee')}'"
	if filters.get("project"):
		conditions += f" AND TSD.project = '{filters.get('project')}'"
	if filters.get("approval_status"):
		conditions += f" AND TSD.approval_status = '{filters.get('approval_status')}'"

	query = f"""
			SELECT
				TS.name id, 
				TS.employee_name title, 
				TS.status status, 
				TS.employee employee, 
				TS.log_date log_date, 
				TSD.actual_hrs actual_hours,
				TSD.hours hours,
				CASE 
					WHEN TSD.actual_hrs = TSD.hours THEN 'No'
					ELSE 'Yes'
				END AS is_modified,
				TSD.approval_status approval_status
			FROM
				`tabTimesheet` as TS
				INNER JOIN `tabTimesheet Detail` as TSD ON TSD.parent = TS.name
			WHERE TS.docstatus != 2
			{conditions}
	"""

	data = frappe.db.sql(query)
	return data