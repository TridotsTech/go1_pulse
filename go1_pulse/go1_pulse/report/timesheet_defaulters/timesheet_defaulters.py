# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
	columns = []
	columns.append(_("Date") + ":Date:100")
	columns.append(_("Employee ID")+":Link/Employee:150")
	columns.append(_("Employee Name") + ":Data:150:")
	columns.append(_("Employee Email ID")+":Data:200")
	columns.append(_("Reporting Manager") + ":Link/Employee:150")
	columns.append(_("Reporting Manager Name")+":Data:200")
	columns.append(_("Reporting Manager Email ID")+":Data:200")
	columns.append(_("Employee Status")+":Data:100")
	return columns

def get_data(filters):
	condition = ""
	if filters.get("employee"):
		condition += f" AND E.employee = '{filters.get('employee')}'"
	if filters.get("from_date"):
		condition += f" AND A.attendance_date >= '{filters.get('from_date')}'"
	if filters.get("to_date"):
		condition += f" AND A.attendance_date <= '{filters.get('to_date')}'"
	holiday_list = get_holiday_list()[1:-1]
	if holiday_list:
		condition += f"AND A.attendance_date NOT IN ({holiday_list})"
	query = f"""
			SELECT
				A.attendance_date date,
				E.name employee_id,
				A.employee_name employee_name,
				E.company_email employee_email_id,
				E.reports_to reporting_manager,
				EMP.employee_name reporting_manager_name,			
				EMP.company_email reporting_manager_email_id,
				E.status employee_status
			FROM
				`tabAttendance` A
				LEFT JOIN `tabTimesheet` TS ON A.employee = TS.employee AND A.attendance_date = TS.log_date
				INNER JOIN `tabEmployee` E ON A.employee = E.employee
				INNER JOIN `tabEmployee` EMP ON EMP.employee = E.reports_to
			WHERE
				TS.log_date IS NULL
				AND A.status NOT IN ("Absent", "On Leave")
				{condition}
	"""
	data = frappe.db.sql(query, as_dict=1)
	return data

def get_holiday_list():
	holiday_list = frappe.db.sql(f"""
									SELECT
										H.holiday_date
									FROM
										`tabHoliday List` HL
									INNER JOIN `tabHoliday` H ON H.parent = HL.name
									INNER JOIN `tabEmployee` E ON E.holiday_list = HL.name
	""")
	holidays = []
	for date in list(holiday_list):
		for date_value in date:
			holidays.append(f"{date_value.year}-{date_value.month}-{date_value.day}")
	return str(holidays)