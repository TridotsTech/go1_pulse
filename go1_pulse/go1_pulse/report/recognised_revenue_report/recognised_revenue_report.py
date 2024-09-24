# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from go1_pulse.queries import recognised_revenue_report

def execute(filters=None):
	columns, data = [], []
	return get_columns(filters), get_data(filters)


def get_columns(filters):
	return [
		{
			"fieldname": "parent",
			"label": "SO Number",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 170,
		},
		{
			"fieldname": "transaction_date",
			"label": "SO Date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "customer",
			"label": "Customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 200,
		},
		{
			"fieldname": "end_customer",
			"label": "End Customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 200,
		},
		{
			"fieldname": "so_item",
			"label": "Item ID",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "item_code",
			"label": "Item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{
			"fieldname": "mandate",
			"label": "Mandate",
			"fieldtype": "link",
			"options": "Mandate"
		},
		{
			"fieldname": "offering",
			"label": "Offering",
			"fieldtype": "link",
			"options": "Offering",
			"width": 200,
		},
		{
			"fieldname": "revenue_method",
			"label": "Rev Method",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "start_date",
			"label": "Start Date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "end_date",
			"label": "End Date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "cost_center",
			"label": "Cost Center",
			"fieldtype": "link",
			"options": "Cost Center",
			"width": 200,
		},
		{
			"fieldname": "project",
			"label": "Project Code",
			"fieldtype": "link",
			"options": "Project Code",
			"width": 200,
		},
		{
			"fieldname": "project_manager",
			"label": "Project Manager",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "currency",
			"label": "Base Currency",
			"fieldtype": "Link",
			"options":"Currency",
			"width": 200,
		},
		{
			"fieldname": "net_amount",
			"label": "Base Currency Contract",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 200,
		},
		{
			"fieldname": "billed_till_march",
			"label": "Base Currency Billed (Till 31st March 2023)",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 300,
		},
		{
			"fieldname": "billed_from_april",
			"label": "Base Currency Billed (From 1st April 2023)",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 300,
		},
		{
			"fieldname": "base_currency_curent_credit_value",
			"label": " Base Currency Credit Notes",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 200,
		},
		{
			"fieldname": "recognised_revenue_till_march",
			"label": "Base Currency Rev. Recog. (Till 31st March 2023)",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 300,
		},
		{
			"fieldname": "recognised_revenue_from_april",
			"label": "Base Currency Rev. Recog. (From 1st April 2023)",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 300,
		},
		{
			"fieldname": "journal_entry_value",
			"label": "Base Currency Journal Entry Value",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 200,
		},
		{
			"fieldname": "accrued_deferred",
			"label": "Base Currency Acc / (Def)",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 200,
		},
		{
			"fieldname": "net_amount_c",
			"label": "INR Contract Value",
			"fieldtype": "Currency",
			"width": 200,
		},
		{
			"fieldname": "billed_till_march_inr",
			"label": "INR Billed (Till 31st March 2023)",
			"fieldtype": "Currency",
			"options": "",
			"width": 300,
		},
		{
			"fieldname": "billed_from_april_inr",
			"label": "INR Billed (From 1st April 2023)",
			"fieldtype": "Currency",
			"options": "",
			"width": 300,
		},
		{
			"fieldname": "base_currency_curent_credit_value_inr",
			"label": " INR Credit Notes",
			"fieldtype": "Currency",
			"options": "",
			"width": 200,
		},
		{
			"fieldname": "recognised_revenue_till_march_inr",
			"label": "INR Rev. Recog. (Till 31st March 2023)",
			"fieldtype": "Currency",
			"options": "",
			"width": 300,
		},
		{
			"fieldname": "recognised_revenue_from_april_inr",
			"label": "INR Rev. Recog. (From 1st April 2023)",
			"fieldtype": "Currency",
			"options": "",
			"width": 300,
		},
		{
			"fieldname": "journal_entry_value_inr",
			"label": "INR Journal Entry Value",
			"fieldtype": "Currency",
			"options": "",
			"width": 200,
		},
		{
			"fieldname": "accrued_deferred_inr",
			"label": "INR Acc / (Def)",
			"fieldtype": "Currency",
			"options": "",
			"width": 200,
		},
		{
			"fieldname": "inr_forex",
			"label": "INR Forex.",
			"fieldtype": "Currency",
			"options": "",
			"width": 200,
		},
	]

def get_condition(filters):
	cond = ""
	

	
	if filters.get("customer"):
		cond += " and so.customer= '{0}'".format(filters.get("customer"))
		
	if filters.get("profit_center"):
		cond += " and soi.cost_center= '{0}'".format(filters.get("profit_center"))
	
	if filters.get("lob"):
		cond += " and soi.line_of_business= '{0}'".format(filters.get("lob"))
		
	if filters.get("mandate"):
		cond += " and soi.mandate= '{0}'".format(filters.get("mandate"))
	
	if filters.get("offering"):
		cond += " and soi.offering = '{0}'".format(filters.get("offering"))
	
	if cond:
		return  cond
	
	return ""


def get_data(filters):
	condition = ""
	condition = get_condition(filters)
	frappe.log_error(title="condition",message=condition)
 
	date=filters.get("date")
	datas=recognised_revenue_report(condition=condition,date=date)
	frappe.log_error(title="datas",message=datas)
 
	for data in datas:
		x1 = (data['recognised_revenue_till_march'] or 0) + (data['recognised_revenue_from_april'] or 0) + (data['journal_entry_value'] or 0 )
		y1 = (int(data['billed_till_march']) or 0) + (data['base_currency_curent_credit_value'] or 0) + (data['billed_from_april'] or 0)
		
		data['accrued_deferred'] = x1 - y1
	
		a = (data['recognised_revenue_till_march_inr'] or 0) + (data['journal_entry_value_inr'] or 0) + (data['recognised_revenue_from_april_inr'] or 0)
		
		b = (data['recognised_revenue_till_march'] or 0) + (data['journal_entry_value'] or 0) + (data['recognised_revenue_from_april'] or 0)
		
		c = (int(data['billed_till_march']) or 0)  +  (data['base_currency_curent_credit_value'] or 0) +  (data['billed_from_april'] or 0)
		
		d = (int(data['billed_till_march_inr']) or 0) + (data['base_currency_curent_credit_value_inr'] or 0) + (data['billed_from_april_inr'] or 0)
		
		try:
			value_rev = round(a/b,5)
			value_bil = round(d/c,5)
		
			if c < b:
				data['inr_forex']  = ((value_bil-value_rev)*c)
			else:
				data['inr_forex']  = ((value_bil-value_rev)*b)
			
		except:
			data['inr_forex'] = 0
			
		#accrued deferred in INR
		x2 = (data['recognised_revenue_till_march_inr'] or 0) + (data['journal_entry_value_inr'] or 0) + (data['recognised_revenue_from_april_inr'] or 0)
		y2 = (int(data['billed_till_march_inr']) or 0) + (data['base_currency_curent_credit_value_inr'] or 0) + (data['billed_from_april_inr'] or 0)
		z2 = (data['inr_forex'])
		
		data['accrued_deferred_inr'] = x2 - y2 + z2
			
	return datas
