# # Copyright (c) 2023, Tridots Team and contributors
# # For license information, please see license.txt

import frappe
from frappe.utils import date_diff, add_days, getdate
from erpnext.setup.utils import get_exchange_rate
from go1_pulse.queries import revenue_recognition_engine_query

# def execute(filters=None):
# 	return get_columns(filters= filters), get_data(filters= filters)

# def get_data(filters):
# 	datas = None
# 	condition = ""

# 	if filters.get("revenue_type"):
# 		condition += "AND soi.revenue_method= '{0}'".format(filters.get("revenue_type"))
# 		frappe.log_error(title="condition",message=condition)
# 	if condition:
# 		date=filters.get("posting_date")
# 		datas=revenue_recognition_engine_query(condition=condition,date=date)
# 		frappe.log_error(title="datas",message=datas)
	
# 		if datas:
# 			if filters.get("revenue_type") == "POC":
# 				frappe.log_error(title="Revenue_type",message="POC")
# 				for data in datas:
# 					to_currency = frappe.get_value("Company", data.company, "default_currency") or frappe.defaults.get_global_default("currency")
# 					if not to_currency:
# 						continue
# 					conversion_rate = get_exchange_rate(data.so_currency, to_currency, filters.get("posting_date") )
					
# 					data['real_time_ex_rate'] = conversion_rate
# 					budget = data.budget_cost
					
# 					if not data.actual_cost:
# 						continue
					
# 					poc = round(data.actual_cost / budget, 2)
					
# 					if round((data.net_amount * poc), 2) <= data.bc_recognised_revenue:
# 						continue
					
# 					bc_rec_revenue = (data.net_amount * poc) - data.bc_recognised_revenue
					
# 					if (data.bc_recognised_revenue +  bc_rec_revenue) > data.net_amount:
# 						bc_rec_revenue =  data.net_amount - data.bc_recognised_revenue
					
# 					if bc_rec_revenue > 0:
# 						data['real_time_ex_rate'] = conversion_rate
# 						data['real_time_amount_bc'] = bc_rec_revenue
# 						if float(data['bc_unrecognised_revenue'])==0:
# 							data['real_time_amount_bc'] = 0
# 						data['real_time_amount'] = bc_rec_revenue * conversion_rate
								
# 			else:
# 				for data in datas:
# 					frappe.log_error(title="data",message=data.company)
# 					to_currency = frappe.get_value("Company", data.company, "default_currency") or frappe.defaults.get_global_default("currency")
# 					if not to_currency:
# 						continue
# 					conversion_rate = get_exchange_rate(data.so_currency, to_currency, filters.get("posting_date") )
# 					data['real_time_ex_rate'] = conversion_rate
					
# 					amount_to_consider = data.net_amount
     
# 					so = frappe.get_doc("Sales Order", data.get("sales_order"))
# 					soi = frappe.get_doc("Sales Order Item", data.get("so_item"))
     
# 					amount_to_consider = data.net_amount - data.bc_recognised_revenue
# 					l_date = data.last_journal_date
     
# 					if not l_date:
# 						l_date = soi.start_date
      
# 					posting_date = filters.get("posting_date")
     
# 					if getdate(filters.get("posting_date")) > getdate(data.end_date):
# 						posting_date = data.end_date
      
# 					data['bc_unrecognised_revenue'] = data.net_amount - data.bc_recognised_revenue
# 					data['unrecognised_revenue'] = data.base_net_amount - data.recognised_revenue
     
# 					total_days = date_diff(data.end_date, data.start_date)  if date_diff(data.end_date, data.start_date) else 0
# 					if data["recognised_until"]:
# 						total_days = (date_diff(data.end_date, data["recognised_until"])) if date_diff(data.end_date, data["recognised_until"]) else 0
      
# 					billing_days = date_diff(posting_date , l_date)
# 					if getdate(filters.get("posting_date")) > getdate(data.end_date):
# 						billing_days = total_days
      
# 					if not billing_days:
# 						data['real_time_amount'] = 0
# 						data['billing_days'] = 0
      
# 					if total_days:
# 						data['billing_days'] = billing_days if billing_days > 0 else 0
# 						data['real_time_amount'] = ((amount_to_consider * conversion_rate )/total_days) * billing_days if billing_days > 0 else 0
# 						data['real_time_amount_bc'] = (amount_to_consider/total_days) * billing_days if billing_days > 0 else 0
# 						if float(data['bc_unrecognised_revenue'])==0:
# 							data['real_time_amount_bc'] = 0
						

# 	if datas:
# 		return datas

# def get_columns(filters):
# 	columns = [
# 		{
# 			"fieldname": "sales_order",
# 			"label": "SO Number",
# 			"fieldtype": "Link",
# 			"options": "Sales Order",
# 			"width": 170,
# 		},
		
# 		{
# 			"fieldname": "transaction_date",
# 			"label": "SO Date",
# 			"fieldtype": "Date",
# 			"width": 100,
# 		},
# 		{
# 			"fieldname": "conversion_rate",
# 			"label": "SO Exchange Rate",
# 			"fieldtype": "Float",
# 			"precision":9,
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "so_item",
# 			"label": "Item ID",
# 			"fieldtype": "Data",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "item_code",
# 			"label": "Item Code",
# 			"fieldtype": "Link",
# 			"options": "Item",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "customer",
# 			"label": "Customer",
# 			"fieldtype": "Link",
# 			"options": "Customer",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "end_customer",
# 			"label": "End Customer",
# 			"fieldtype": "Link",
# 			"options": "Customer",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "mandate",
# 			"label": "Mandate",
# 			"fieldtype": "link",
# 			"options": "Mandate"
# 		},
# 		{
# 			"fieldname": "offering",
# 			"label": "Offering",
# 			"fieldtype": "link",
# 			"options": "Offering",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "revenue_method",
# 			"label": "Rev Method",
# 			"fieldtype": "Data",
# 			"width": 150,
# 		},]
# 	columns += [
# 		{
# 			"fieldname": "cost_center",
# 			"label": "Cost Center",
# 			"fieldtype": "link",
# 			"options": "Cost Center",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "project",
# 			"label": "Project Code",
# 			"fieldtype": "link",
# 			"options": "Project Code",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "project_manager",
# 			"label": "Project Manager",
# 			"fieldtype": "Data",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "credit_note_value",
# 			"label": "Credit Note Value",
# 			"fieldtype": "curr",
# 			"options": "Sales Invoice",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "journal_entry_value",
# 			"label": "Journal Entry",
# 			"fieldtype": "Float",
# 			"options": "",
# 			"precision":2,
# 			"width": 150,
# 		},
# 		]
# 	if filters.get("revenue_type") == "Equal revenue over the contract period":
# 		columns += [{
# 			"fieldname": "start_date",
# 			"label": "Start Date",
# 			"fieldtype": "Date",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "end_date",
# 			"label": "End Date",
# 			"fieldtype": "Date",
# 			"width": 150,
# 		},] 
# 	if filters.get("revenue_type") == "POC":
# 		columns += [{
# 			"fieldname": "budget_cost",
# 			"label": "Budt. Cost",
# 			"fieldtype": "Currency",
# 			"options": "",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "actual_cost",
# 			"label": "Actual Cost",
# 			"fieldtype": "Currency",
# 			"options": "",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "per_complete",
# 			"label": "POC",
# 			"fieldtype": "Percent",
# 			"options": "",
# 			"width": 150,
# 		},
# 	]
# 	columns += [
# 		{
# 			"fieldname": "so_currency",
# 			"label": "So Currency",
# 			"fieldtype": "Link",
# 			"options": "Currency",
# 			"width": 100,
# 		},
# 		{
# 			"fieldname": "net_amount",
# 			"label": "Contract Value (Base Currency)",
# 			"fieldtype": "Currency",
# 			"options": "so_currency",
# 			"width": 200,
# 		},
# 		{
# 			"fieldname": "bc_recognised_revenue",
# 			"label": "Recognised Revenue (Base Currency)",
# 			"fieldtype": "Currency",
# 			"options": "so_currency",
# 			"width": 250,
# 		},
# 		{
# 			"fieldname": "bc_unrecognised_revenue",
# 			"label": "Un Recognised Revenue (Base Currency)",
# 			"fieldtype": "Currency",
# 			"options": "so_currency",
# 			"width": 250,
# 		},]
# 	if filters.get("revenue_type") == "Equal revenue over the contract period":
# 		columns += [{
# 			"fieldname": "base_net_amount",
# 			"label": "Contract Value",
# 			"fieldtype": "Currency",
# 			"options": "",
# 			"width": 150,
# 		},]
# 	columns += [
# 		{
# 			"fieldname": "recognised_revenue",
# 			"label": "Recognised Revenue.",
# 			"fieldtype": "Currency",
# 			"options": "",
# 			"width": 150,
# 		},]
# 	if filters.get("revenue_type") == "Equal revenue over the contract period":
# 		columns += [{
# 			"fieldname": "unrecognised_revenue",
# 			"label": "Un Recognised Revenue",
# 			"fieldtype": "Currency",
# 			"options": "",
# 			"width": 150,
# 		},]
# 	columns += [
# 		{
# 			"fieldname": "recognised_until",
# 			"label": "Recognised Until",
# 			"fieldtype": "Date",
# 			"width": 150,
# 		},
# 		{
# 			"fieldname": "real_time_amount_bc",
# 			"label": "Real-time Amount( Base Currency )",
# 			"fieldtype": "Currency",
# 			"width": 250,
# 			"options": "so_currency"
# 		},
# 		{
# 			"fieldname": "real_time_ex_rate",
# 			"label": "Real-time Ex-Rate",
# 			"fieldtype": "Float",
# 			"width": 150,
# 			"precision": 9,
# 		},
# 		{
# 			"fieldname": "real_time_amount",
# 			"label": "Real-time Amount",
# 			"fieldtype": "Currency",
# 			"width": 150,
# 		}]
# 	if filters.get("revenue_type") == "Equal revenue over the contract period":
# 		columns += [
# 		{
# 			"fieldname": "billing_days",
# 			"label": "Billing Days",
# 			"fieldtype": "float",
# 			"width": 150,
# 		}]
		
# 	return columns
	
# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import date_diff, add_days, getdate
from erpnext.setup.utils import get_exchange_rate

def execute(filters=None):
	return get_columns(filters= filters), get_data(filters= filters)

def get_data(filters):
	datas = None
	condition = ""
	if filters.get("revenue_type"):
		condition += "AND soi.revenue_method= '{0}'".format(filters.get("revenue_type"))
	if condition:
		date=filters.get("posting_date")
		datas=revenue_recognition_engine_query(condition=condition)
		if datas:
			if filters.get("revenue_type") == "POC":
				for data in datas:
					to_currency = frappe.get_value("Company", data.company, "default_currency") or frappe.defaults.get_global_default("currency")
					if not to_currency:
						continue
					conversion_rate = get_exchange_rate(data.so_currency, to_currency, filters.get("posting_date") )
					
					data['real_time_ex_rate'] = conversion_rate
					budget = data.budget_cost
					
					if not data.actual_cost:
						continue
					
					poc = round(data.actual_cost / budget, 2)
					
					if round((data.net_amount * poc), 2) <= data.bc_recognised_revenue:
						continue
					
					bc_rec_revenue = (data.net_amount * poc) - data.bc_recognised_revenue
					
					if (data.bc_recognised_revenue +  bc_rec_revenue) > data.net_amount:
						bc_rec_revenue =  data.net_amount - data.bc_recognised_revenue
					
					if bc_rec_revenue > 0:
						data['real_time_ex_rate'] = conversion_rate
						data['real_time_amount_bc'] = bc_rec_revenue
						if float(data['bc_unrecognised_revenue'])==0:
							data['real_time_amount_bc'] = 0
						data['real_time_amount'] = bc_rec_revenue * conversion_rate
								
			else:
				for data in datas:
					to_currency = frappe.get_value("Company", data.company, "default_currency") or frappe.defaults.get_global_default("currency")
					if not to_currency:
						continue
					conversion_rate = get_exchange_rate(data.so_currency, to_currency, filters.get("posting_date") )
					data['real_time_ex_rate'] = conversion_rate
					
					amount_to_consider = data.net_amount
					so = frappe.get_doc("Sales Order", data.get("sales_order"))
					soi = frappe.get_doc("Sales Order Item", data.get("so_item"))
				
					amount_to_consider = data.net_amount - data.bc_recognised_revenue
					l_date = data.last_journal_date
					
				
					if not l_date:
						l_date = soi.start_date
				
					posting_date = filters.get("posting_date")
					if getdate(filters.get("posting_date")) > getdate(data.end_date):
						posting_date = data.end_date
					data['bc_unrecognised_revenue'] = data.net_amount - data.bc_recognised_revenue
					data['unrecognised_revenue'] = data.base_net_amount - data.recognised_revenue
					total_days = date_diff(data.end_date, data.start_date)  if date_diff(data.end_date, data.start_date) else 0
					if data["recognised_until"]:
						total_days = (date_diff(data.end_date, data["recognised_until"])) if date_diff(data.end_date, data["recognised_until"]) else 0
					billing_days = date_diff(posting_date , l_date)
					if getdate(filters.get("posting_date")) > getdate(data.end_date):
						billing_days = total_days
				
					if not billing_days:
						data['real_time_amount'] = 0
						data['billing_days'] = 0
					if total_days:
						data['billing_days'] = billing_days if billing_days > 0 else 0
						data['real_time_amount'] = ((amount_to_consider * conversion_rate )/total_days) * billing_days if billing_days > 0 else 0
					
						data['real_time_amount_bc'] = (amount_to_consider/total_days) * billing_days if billing_days > 0 else 0
						if float(data['bc_unrecognised_revenue'])==0:
							data['real_time_amount_bc'] = 0
					
	if datas:
		return datas

def get_columns(filters):
	columns = [
		{
			"fieldname": "sales_order",
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
			"fieldname": "conversion_rate",
			"label": "SO Exchange Rate",
			"fieldtype": "Float",
			"precision":9,
			"width": 150,
		},
		{
			"fieldname": "so_item",
			"label": "Item ID",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "item_code",
			"label": "Item Code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"fieldname": "customer",
			"label": "Customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
		},
		{
			"fieldname": "end_customer",
			"label": "End Customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150,
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
			"width": 150,
		},
		{
			"fieldname": "revenue_method",
			"label": "Rev Method",
			"fieldtype": "Data",
			"width": 150,
		},]
	columns += [
		{
			"fieldname": "cost_center",
			"label": "Cost Center",
			"fieldtype": "link",
			"options": "Cost Center",
			"width": 150,
		},
		{
			"fieldname": "project",
			"label": "Project Code",
			"fieldtype": "link",
			"options": "Project Code",
			"width": 150,
		},
		{
			"fieldname": "project_manager",
			"label": "Project Manager",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "credit_note_value",
			"label": "Credit Note Value",
			"fieldtype": "curr",
			"options": "Sales Invoice",
			"width": 150,
		},
		{
			"fieldname": "journal_entry_value",
			"label": "Journal Entry",
			"fieldtype": "Float",
			"options": "",
			"precision":2,
			"width": 150,
		},
		]
	if filters.get("revenue_type") == "Equal revenue over the contract period":
		columns += [{
			"fieldname": "start_date",
			"label": "Start Date",
			"fieldtype": "Date",
			"width": 150,
		},
		{
			"fieldname": "end_date",
			"label": "End Date",
			"fieldtype": "Date",
			"width": 150,
		},] 
	if filters.get("revenue_type") == "POC":
		columns += [{
			"fieldname": "budget_cost",
			"label": "Budt. Cost",
			"fieldtype": "Currency",
			"options": "",
			"width": 150,
		},
		{
			"fieldname": "actual_cost",
			"label": "Actual Cost",
			"fieldtype": "Currency",
			"options": "",
			"width": 150,
		},
		{
			"fieldname": "per_complete",
			"label": "POC",
			"fieldtype": "Percent",
			"options": "",
			"width": 150,
		},
	]
	columns += [
		{
			"fieldname": "so_currency",
			"label": "So Currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 100,
		},
		{
			"fieldname": "net_amount",
			"label": "Contract Value (Base Currency)",
			"fieldtype": "Currency",
			"options": "so_currency",
			"width": 200,
		},
		{
			"fieldname": "bc_recognised_revenue",
			"label": "Recognised Revenue (Base Currency)",
			"fieldtype": "Currency",
			"options": "so_currency",
			"width": 250,
		},
		{
			"fieldname": "bc_unrecognised_revenue",
			"label": "Un Recognised Revenue (Base Currency)",
			"fieldtype": "Currency",
			"options": "so_currency",
			"width": 250,
		},]
	if filters.get("revenue_type") == "Equal revenue over the contract period":
		columns += [{
			"fieldname": "base_net_amount",
			"label": "Contract Value",
			"fieldtype": "Currency",
			"options": "",
			"width": 150,
		},]
	columns += [
		{
			"fieldname": "recognised_revenue",
			"label": "Recognised Revenue.",
			"fieldtype": "Currency",
			"options": "",
			"width": 150,
		},]
	if filters.get("revenue_type") == "Equal revenue over the contract period":
		columns += [{
			"fieldname": "unrecognised_revenue",
			"label": "Un Recognised Revenue",
			"fieldtype": "Currency",
			"options": "",
			"width": 150,
		},]
	columns += [
		{
			"fieldname": "recognised_until",
			"label": "Recognised Until",
			"fieldtype": "Date",
			"width": 150,
		},
		{
			"fieldname": "real_time_amount_bc",
			"label": "Real-time Amount( Base Currency )",
			"fieldtype": "Currency",
			"width": 250,
			"options": "so_currency"
		},
		{
			"fieldname": "real_time_ex_rate",
			"label": "Real-time Ex-Rate",
			"fieldtype": "Float",
			"width": 150,
			"precision": 9,
		},
		{
			"fieldname": "real_time_amount",
			"label": "Real-time Amount",
			"fieldtype": "Currency",
			"width": 150,
		}]
	if filters.get("revenue_type") == "Equal revenue over the contract period":
		columns += [
		{
			"fieldname": "billing_days",
			"label": "Billing Days",
			"fieldtype": "float",
			"width": 150,
		}]
		
	return columns
	
