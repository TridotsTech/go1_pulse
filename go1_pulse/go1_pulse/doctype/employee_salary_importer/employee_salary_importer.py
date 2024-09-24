# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import ast
import json
from hrms.hr.doctype.leave_application.leave_application import get_holidays
from datetime import date, datetime
from go1_pulse.go1_pulse.doctype.timesheet_aggregator.timesheet_aggregator import get_customer_timesheets

class EmployeeSalaryImporter(Document):
	def validate(self):
		self.validate_date()
	def on_trash(self):
		frappe.db.sql("delete from `tabEmployee Salary Importer Details` where parent = '{}'".format(self.name) )
	def on_cancel(self):
		if self.cost_allocation_reference:
			ta_name = self.cost_allocation_reference
			frappe.db.set_value("Employee Salary Importer", self.name, "cost_allocation_reference", "")
			doc = frappe.get_doc("Timesheet Aggregator", ta_name)
			doc.cancel()
			doc.delete()
	def validate_date(self):
		if not self.start_date and not self.end_date:
			frappe.throw("Date Can't be empty", title="Date Missing")
	def before_save(self):
		d_name = frappe.get_value("Employee Salary Importer",{"start_date": self.start_date, "end_date": self.end_date, "docstatus": 1}, "name")
		if d_name:
			link = '<a href="/app/employee-salary-importer/{0}">{0}</a>'.format(d_name)
			frappe.throw("The specified date<b>[{0} - {1}]</b> is already present in the document. {2}".format(self.start_date, self.end_date, link))
	
@frappe.whitelist()
def get_employee_list():
	emp_list = frappe.get_list("Employee", ["name as employee", "employee_name", "payroll_cost_center as cost_center"])
	
	if emp_list:
		return emp_list
	return []


@frappe.whitelist()
def make_journal_entry(datas = None, args = None, ta_name= None):
	if not datas or not args:
		return
	if ta_name:
		jv_name = frappe.db.get_value("Journal Entry", {"emp_expense_reference": ta_name, "docstatus": ['!=', 2]},"name")
		if jv_name:
			jv_link = '<a href="/app/journal-entry/{0}">{0}</a>'.format(jv_name)
			frappe.throw("Already Expense mapped to the journal {}".format(jv_link))
	
	datas = json.loads(datas)
	args = json.loads(args)
	target = frappe.new_doc("Journal Entry")
	target.posting_date = args.get('posting_date')
	target.emp_expense_reference = ta_name

	group_by_proj = {}
	group_by_cc = {}
	credit_cost_centers = {}
	i = 0
	total_billable = 0
	for row in datas:
		if row.get('cost_center') in credit_cost_centers:
			credit_cost_centers[row.get('cost_center')] += row.get('billing_amount')
		else:
			credit_cost_centers[row.get('cost_center')] = row.get('billing_amount')
			
		if row.get('project') in  group_by_proj:
			group_by_proj[row.get('project')][0] += row.get('billing_amount')
			
		elif not row.get('project'):
			if row.get('cost_center') in group_by_cc:
				group_by_cc[row.get('cost_center')][0] += row.get('billing_amount')
			else:
				group_by_cc[row.get('cost_center')] = [row.get('billing_amount'), row.get('cost_center')]
		else:
			total_billable += row.get('billing_amount')
			group_by_proj[row.get('project')] = [row.get('billing_amount'), row.get('cost_center')]

	for c_cost_center in credit_cost_centers:
		if credit_cost_centers[c_cost_center]:
			target.append("accounts",{"account": args.get('account'), "cost_center": c_cost_center,  "credit_in_account_currency": credit_cost_centers[c_cost_center],
			"debit_in_account_currency": 0})
	
	for project in group_by_proj:
		if group_by_proj[project][0]:
			mandate = frappe.get_value("Project", {"name": project}, "mandate") or ""
			cost_center = frappe.get_value("Project", {"name": project}, "cost_center") or ""
			target.append("accounts", {"account": args.get('account'), "cost_center":cost_center,  
					"debit_in_account_currency": group_by_proj[project][0],"credit_in_account_currency" : 0, "project": project, "mandate": mandate})
	for cost_center in group_by_cc:
		target.append("accounts", {"account": args.get('account'), "cost_center":cost_center,  "debit_in_account_currency": group_by_cc[cost_center][0],"credit_in_account_currency" : 0})
	
	target.run_method("set_missing_values")

	return target
	


@frappe.whitelist()
def create_timesheet_aggregator(start_date, end_date):
	emp_sal_datas = get_customer_timesheets(start_date=start_date, end_date=end_date)
	if not emp_sal_datas:
		return
	
	ta_doc = frappe.new_doc("Timesheet Aggregator")
	ta_doc.start_date = start_date
	ta_doc.end_date = end_date
	for data in emp_sal_datas['details']:
		f_data = {}
		if "employee" in data:
			f_data.update({"employee" : data['employee'],})
		if "hours" in data:
			f_data.update({"employee_worked_hours" : data['hours'],})
		if "cost_center" in data:
			f_data.update({"cost_center" : data['cost_center'],})
		if "billing_amount" in data:
			f_data.update({"billing_amount" : data['billing_amount'],})
		if "project" in data:
			f_data.update({"project" : data['project'],})
		if "employee_worked_days" in data:
			f_data.update({"employee_worked_days" : data['employee_worked_days'],})
		if "total_working_days" in data:
			f_data.update({"total_working_days" : data['total_working_days'],})
		if "salary_amount" in data:
			f_data.update({"salary_amount" : data['salary_amount'],})
		
		ta_doc.append("details",f_data)
		
	ta_doc.total_hours = emp_sal_datas['total_hours']
	ta_doc.billable_amount = emp_sal_datas['billable_amount']
	ta_doc.save()
	ta_doc.submit()
	frappe.msgprint("Cost Allocation Successfully Created.")
	return ta_doc.name
