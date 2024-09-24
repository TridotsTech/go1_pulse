# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from hrms.hr.doctype.leave_application.leave_application import get_holidays
from datetime import date, datetime

class TimesheetAggregator(Document):
	def validate(self):
		self.billable_amount = 0
		for log in self.details:
			if not log.billing_amount:
				log.billing_amount = 0.0
			self.billable_amount += log.billing_amount

	def on_trash(self):
		frappe.db.delete("Timesheet Aggregator Detail", filters={"parent": self.name})

	def on_cancel(self):
		if self.name:
			jv_name = frappe.db.get_value("Journal Entry", {"emp_expense_reference": self.name}, "name")
			if jv_name:
				jv_doc = frappe.get_doc("Journal Entry", jv_name)
				if jv_doc.docstatus == 1:
					jv_doc.cancel()
				if jv_doc.docstatus == 0:
					jv_doc.delete()
     
     

@frappe.whitelist()
def get_customer_timesheets(start_date, end_date):
	date1 = datetime.strptime(start_date, "%Y-%m-%d")
	date2 = datetime.strptime(end_date, "%Y-%m-%d")
	total_days = date2 - date1
	
	# get employee approved timesheet hours
	logs = frappe.db.sql("""
		SELECT
			ts.employee,
			SUM(tsd.hours) AS hours,
			(
				SELECT payroll_cost_center
				FROM `tabEmployee`
				WHERE name = ts.employee
			) AS cost_center,
			tsd.project
		FROM
			`tabTimesheet` ts
			LEFT JOIN `tabTimesheet Detail` tsd ON ts.name = tsd.parent
		WHERE
			tsd.to_time BETWEEN '{0}' AND '{1}'
			AND tsd.approval_status = 'Approved'
			AND tsd.docstatus = 1
		GROUP BY
			ts.employee,
			tsd.project
	""".format(start_date, end_date), as_dict=True)
	
	
	if logs:
		get_employee_total_worked_hours(logs=logs,total_days=total_days,start_date=start_date,end_date=end_date)


def get_employee_total_worked_hours(logs=None,total_days=None,start_date=None,end_date=None):
	total_hrs = 0
	total_amount = 0
	# get employee total worked hours
	employees_total_wrkd_hrs = frappe.db.sql("""
		SELECT
			ts.employee AS employee,
			SUM(tsd.hours) AS hours
		FROM
			`tabTimesheet` ts
		LEFT JOIN
			`tabTimesheet Detail` tsd ON ts.name = tsd.parent
		WHERE
			tsd.to_time BETWEEN '{0}' AND '{1}'
			AND tsd.approval_status = 'Approved'
			AND tsd.docstatus = 1
		GROUP BY
			ts.employee
	""".format(start_date, end_date ), as_dict=True)
	
	employees_total_wrkd_hrs = {emp.get('employee') : emp.get('hours') for emp in employees_total_wrkd_hrs }

	for log in logs:
		sal_details = None
		emp_std_wrk_hrs_pd = frappe.get_value("Employee", {"name":log.employee},"standard_working_hours_per_day")
		query = """
			SELECT
				esid.days AS days,
				esid.salary_amount AS salary_amount
			FROM
				`tabEmployee Salary Importer Details` esid,
				`tabEmployee Salary Importer` esi
			WHERE
				esi.docstatus = 1
				AND esi.name = esid.parent
				AND esid.employee = '{0}'
				AND esi.start_date = '{1}'
				AND esi.end_date = '{2}'
		""".format(log.employee, start_date, end_date)
		
		sal_details = frappe.db.sql(query, as_dict=True)[0] if frappe.db.sql(query, as_dict=True) else None
		salary = sal_details.salary_amount if sal_details else 0
		
		if salary:
			log['salary_amount'] = salary
		
		holidays  = get_holidays(log['employee'], start_date, end_date)
		
		log["total_working_days"] = total_days.days - holidays
		log["employee_worked_days"] = sal_details.days if sal_details else 0
		
		if log.get('employee') in employees_total_wrkd_hrs:
			log['employee_worked_hours'] = employees_total_wrkd_hrs[log.get('employee')]
		if log['employee_worked_hours'] > (emp_std_wrk_hrs_pd * log["employee_worked_days"]):
			cost = round(salary/log['employee_worked_hours'], 2)
			log['cost_per_hour'] = cost
		else:
			cost = round((salary/(emp_std_wrk_hrs_pd * log["employee_worked_days"])),2)
			log['cost_per_hour'] = cost
			
		log["billing_amount"] = cost * log.hours
		
		if log.hours:
			total_hrs += log.hours
		if log.billing_amount:
			total_amount += log.billing_amount 
	if total_hrs and total_amount:
		indirect_billable_cost(logs=logs,total_hrs=total_hrs,total_amount=total_amount,start_date=start_date,end_date=end_date)
  
  
def  indirect_billable_cost(logs=None,total_hrs=None,total_amount=None,start_date=None,end_date=None):
	# employee in-direct billable hours cost
	id_billable_hours = {}
	id_total_amount = 0
	total_ctc = 0
	cost_center_wise_expe = {}
	for log in logs:
		if log.cost_center in cost_center_wise_expe:
			cost_center_wise_expe[log.cost_center] += log.billing_amount
		else:
			cost_center_wise_expe[log.cost_center] = log.billing_amount
		
		query = """
			SELECT
				esid.days AS days,
				esid.salary_amount AS salary_amount
			FROM
				`tabEmployee Salary Importer Details` esid,
				`tabEmployee Salary Importer` esi
			WHERE
				esi.docstatus = 1
				And esi.name = esid.parent
				AND employee = '{0}'
				AND esi.start_date = '{1}'
				AND esi.end_date = '{2}'
		""".format(log.employee, start_date, end_date)

		sal_details = frappe.db.sql(query, as_dict=True)[0] if frappe.db.sql(query, as_dict=True) else None
		salary = sal_details.salary_amount if sal_details else 0
		
		if salary:
			log['salary_amount'] = salary
		if log.employee in id_billable_hours:
			id_billable_hours[log.employee]['billing_amount'] -= log.billing_amount
			if id_billable_hours[log.employee]['billing_amount'] < 0:
				id_billable_hours[log.employee]['billing_amount'] = 0
		else:
			id_billable_hours[log.employee] = {"employee": log.employee, "billing_amount":round(salary, 3) - log.billing_amount, "cost_center": log.cost_center}
			if id_billable_hours[log.employee]['billing_amount'] < 0:
				id_billable_hours[log.employee]['billing_amount'] = 0
			total_ctc += round(salary, 3)
   
	for emp, data in list(id_billable_hours.items()):
		if not id_billable_hours[emp]["billing_amount"]:
			id_billable_hours.pop(emp)
		else:
			id_total_amount += data["billing_amount"]
	data = {
		"details": logs + list(id_billable_hours.values()),
		"total_hours": total_hrs,
		"billable_amount": total_amount + id_total_amount,
		"total_ctc":total_ctc,
		}
	
	return data




@frappe.whitelist()
def make_journal_entry(source_name= None, account = None):
	if not source_name and not account:
		return
	
	target = frappe.new_doc("Journal Entry")
	target.emp_expense_reference = source_name
	timesheet_agg = frappe.get_doc("Timesheet Aggregator", source_name)
	
	
	group_by_proj = {}
	group_by_cc = {}
	i = 0
	
	for row in timesheet_agg.details:
		if row.cost_center in group_by_cc:
			group_by_cc[row.cost_center] += row.billing_amount
		else:
			if row.billing_amount:
				group_by_cc[row.cost_center] = row.billing_amount
			

	for row in timesheet_agg.details:
		if row.project in  group_by_proj:
			group_by_proj[row.project][0] += row.billing_amount
		elif not row.project:
			if row.billing_amount:
				i+=1
				group_by_proj['No Project'+str(i)] = [row.billing_amount, row.cost_center]
		else:
			if row.billing_amount:
				group_by_proj[row.project] = [row.billing_amount, row.cost_center]	
			
	if not timesheet_agg.billable_amount:
		frappe.throw("Expenses can't be made for zero amount")
	
	for cc in group_by_cc:
		target.append("accounts",{"account": account, "cost_center": cc,  "credit_in_account_currency": group_by_cc[cc],
			"debit_in_account_currency": 0})
 
	for project in group_by_proj:
		if "No Project" in project:
			target.append("accounts", {"account": account, "cost_center":group_by_proj[project][1],  "debit_in_account_currency": group_by_proj[project][0],
								"credit_in_account_currency" : 0, "project": ""})
		else:
			mandate = frappe.get_value("Project", {"name": project}, "mandate") or ""
			cost_center = frappe.get_value("Project", {"name": project}, "cost_center") or ""
			target.append("accounts", {"account": account, "cost_center":cost_center,  "debit_in_account_currency": group_by_proj[project][0],
								"credit_in_account_currency" : 0, "project": project, "mandate": mandate})

	target.run_method("set_missing_values")

	return target
