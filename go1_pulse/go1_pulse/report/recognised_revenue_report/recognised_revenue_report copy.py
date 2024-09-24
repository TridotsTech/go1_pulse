# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate

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
			"fieldname": "base_currency_credit_value",
			"label": " Base Currency Credit Notes / Journals",
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
			"fieldname": "base_currency_credit_value_inr",
			"label": " INR Credit Notes / Journals",
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
	
	if filters.get("date"):
		cond += " and so.transaction_date <= '{0}'".format(filters.get("date"))
	
	if filters.get("customer"):
		cond += " and so.customer= '{0}'".format(filters.get("customer"))
		
	if filters.get("profit_center"):
		cond += " and soi.cost_center= '{0}'".format(filters.get("profit_center"))
	
	if filters.get("lob"):
		cond += " and soi.line_of_business= '{0}'".format(filters.get("lob"))
		
	if filters.get("mandate"):
		cond += " and soi.mandate= '{0}'".format(filters.get("mandate"))
	
	if filters.get("offering"):
		cond += " and soi.offering= '{0}'".format(filters.get("offering"))
	
	if cond:
		return  cond
	
	return ""
def get_data(filters):
	condition = ""
	condition = get_condition(filters)
	datas =  frappe.db.sql("""
			SELECT
			soi.parent,
			soi.transaction_date,
			soi.mandate,
			soi.name as so_item,
			soi.item_code,
			soi.offering,
			soi.revenue_method,
			soi.start_date,
			soi.end_date,
			soi.cost_center,
			soi.project,
			(SELECT project_manager FROM `tabProject` WHERE name = soi.project) AS project_manager,
			so.currency,
			soi.net_amount,
			so.customer,
			soi.end_customer,
			so.conversion_rate,
			( ((SELECT 
					SUM(billing) 
				FROM `tabSales Order Billing Method` sobm
				WHERE sobm.item_id = soi.name AND sobm.parent = so.name AND docstatus = 1 AND sobm.is_billed = 1 AND sobm.from_april = 0 )/100) * soi.net_amount)
			AS billed_till_march,
			COALESCE(
				(
					SELECT ABS(SUM(sii.amount) )
					FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 0 AND si.status != 'Credit Note Issued'
				), 0
			)
			AS billed_from_april,
			( ((SELECT 
					SUM(billing) 
				FROM `tabSales Order Billing Method` 
				WHERE item_id = soi.name AND parent = so.name AND docstatus = 1 AND is_billed = 1 )/100) * soi.net_amount)
			AS base_currency_billed,
			CASE
				WHEN
					(
						COALESCE(
							(
								SELECT ABS(SUM(sii.amount) )
								FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
								WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
							), 0
						)
						-
						COALESCE(
							(
								SELECT ABS(SUM(sii.amount))
								FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
								WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1
							), 0
						)
					) < 0
				THEN
					0
				ELSE(
					COALESCE(
						(
							SELECT ABS(SUM(sii.amount))
							FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
							WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
						), 0
					)
					-
					COALESCE(
						(
							SELECT ABS(SUM(sii.amount))
							FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
							WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1
						), 0
					)
				)
			END AS base_currency_credit_value,
			CASE
				WHEN
					(
						COALESCE(
							(
								SELECT ABS(SUM(sii.base_amount) )
								FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
								WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
							), 0
						)
						-
						COALESCE(
							(
								SELECT ABS(SUM(sii.base_amount))
								FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
								WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1
							), 0
						)
					) < 0
				THEN
					0
				ELSE(
					COALESCE(
						(
							SELECT ABS(SUM(sii.base_amount))
							FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
							WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 1
						), 0
					)
					-
					COALESCE(
						(
							SELECT ABS(SUM(sii.base_amount))
							FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
							WHERE sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1
						), 0
					)
				)
			END AS base_currency_credit_value_inr,
			COALESCE(
					(
					SELECT
						SUM(jea.debit_in_account_currency/ jea.so_exchange_rate)
					FROM
						`tabJournal Entry` je
					LEFT JOIN
						`tabJournal Entry Account` jea
					ON
						je.name = jea.parent
					WHERE
						sales_order = so.name
						AND sales_order_item = soi.name
						AND je.docstatus = 1
						AND je.is_from_report = 0
						AND je.posting_date <= '{date}'
					),
					0
				) AS journal_entry_value,
			COALESCE(
				(
					SELECT
						SUM(jea.debit_in_account_currency)
					FROM
						`tabJournal Entry` je
					LEFT JOIN
						`tabJournal Entry Account` jea
					ON
						je.name = jea.parent
					WHERE
						sales_order = so.name
						AND sales_order_item = soi.name
						AND je.docstatus = 1
						AND je.is_from_report = 0
						AND je.posting_date <= '{date}'
					),
					0
				) AS journal_entry_value_inr,
			soi.revenue_recognised_amount AS recognised_revenue_till_march,
			
			COALESCE((SELECT SUM(debit_in_account_currency / so_exchange_rate)
					FROM `tabJournal Entry Account` jea
					LEFT JOIN `tabJournal Entry` je ON je.name = jea.parent
					WHERE je.docstatus = 1 AND sales_order = so.name AND sales_order_item = soi.name and je.posting_date <= '{date}'), 0)
			AS recognised_revenue_from_april,

			COALESCE((SELECT SUM(debit_in_account_currency / so_exchange_rate)
					FROM `tabJournal Entry Account` jea
					LEFT JOIN `tabJournal Entry` je ON je.name = jea.parent
					WHERE je.docstatus = 1 AND sales_order = so.name AND sales_order_item = soi.name), 0) + soi.revenue_recognised_amount 
			AS recognised_revenue,
			
			soi.amount - COALESCE((SELECT SUM(debit_in_account_currency / so_exchange_rate)
								FROM `tabJournal Entry Account` jea
								LEFT JOIN `tabJournal Entry` je ON je.name = jea.parent
								WHERE je.docstatus = 1 AND sales_order = so.name AND sales_order_item = soi.name), 0) + soi.revenue_recognised_amount 
			AS unrecognised_revenue,
			
			soi.base_net_amount AS net_amount_c,
			0 as inr_forex,
			( ((SELECT 
					SUM(billing) 
				FROM `tabSales Order Billing Method` sobm
				WHERE sobm.item_id = soi.name AND sobm.parent = so.name AND docstatus = 1 AND sobm.is_billed = 1 AND sobm.from_april = 0)/100) * soi.base_net_amount)
			AS billed_till_march_inr,
			COALESCE(
				(
					SELECT ABS(SUM(sii.base_amount) )
					FROM `tabSales Invoice`si LEFT JOIN `tabSales Invoice Item`sii ON si.name = sii.parent
					WHERE si.posting_date <= '{date}' AND sii.sales_order = so.name AND sii.so_detail = soi.name AND si.docstatus = 1 AND si.is_return = 0 AND si.status != 'Credit Note Issued'
				), 0
			)
			AS billed_from_april_inr,
			( ((SELECT 
					SUM(billing) 
				FROM `tabSales Order Billing Method` sobm
				inner join `tabSales Invoice Item` sii on sobm.item_id = sii.so_detail
				WHERE sobm.item_id = soi.name AND sobm.parent = so.name AND sii.docstatus = 1 AND sobm.is_billed = 1 )/100) * soi.base_net_amount)
			AS billed_inr,
			(soi.revenue_recognised_amount * so.conversion_rate ) AS recognised_revenue_till_march_inr,
			
			COALESCE((SELECT SUM(debit_in_account_currency)
					FROM `tabJournal Entry Account` jea
					LEFT JOIN `tabJournal Entry` je ON je.name = jea.parent
					WHERE je.docstatus = 1 AND sales_order = so.name AND sales_order_item = soi.name and je.posting_date <= '{date}'), 0)
			AS recognised_revenue_from_april_inr,
			
			COALESCE((SELECT SUM(debit_in_account_currency)
					FROM `tabJournal Entry Account` jea
					LEFT JOIN `tabJournal Entry` je ON je.name = jea.parent
					WHERE je.docstatus = 1 AND sales_order = so.name AND sales_order_item = soi.name), 0) + (soi.revenue_recognised_amount * so.conversion_rate ) 
			AS recognised_revenue_c,
			
			(SELECT estimated_costing FROM `tabProject` WHERE name = soi.project) AS inr_budget_cost,
			(SELECT total_employee_cost + total_purchase_cost FROM `tabProject` WHERE name = soi.project) AS inr_actual_cost,
			CASE
				WHEN (SELECT (((total_employee_cost + total_purchase_cost) / estimated_costing) * 100) FROM `tabProject` WHERE name = soi.project) > 100 THEN 100
				ELSE (SELECT ROUND(((total_employee_cost + total_purchase_cost) / estimated_costing) * 100) FROM `tabProject` WHERE name = soi.project)
			END AS inr_per_complete
		FROM
			`tabSales Order` so,
			`tabSales Order Item` soi
		WHERE
			so.docstatus = 1
			AND soi.parent = so.name {condition}
		""".format(condition=condition,date=filters.get("date")), as_dict=True)
	for data in datas:
		#accrued deferred base currency
		x1 = (data['recognised_revenue_till_march'] or 0) + (data['recognised_revenue_from_april'] or 0) + (data['journal_entry_value'] or 0 )
		y1 = (data['billed_till_march'] or 0) + (data['base_currency_credit_value'] or 0) + (data['billed_from_april'] or 0)
		
		# frappe.log_error("@revenueX1"+data['parent'],x1)
		# frappe.log_error("@journal"+data['parent'],data['journal_entry_value'])
		data['accrued_deferred'] = x1 - y1
		
		#INR Forex
		a = (data['recognised_revenue_till_march_inr'] or 0) + (data['journal_entry_value_inr'] or 0) + (data['recognised_revenue_from_april_inr'] or 0)
		b = (data['recognised_revenue_till_march'] or 0) + (data['journal_entry_value'] or 0) + (data['recognised_revenue_from_april'] or 0)
		c = (data['billed_till_march'] or 0)  +  (data['base_currency_credit_value'] or 0) +  (data['billed_from_april'] or 0)
		d = (data['billed_till_march_inr'] or 0) + (data['base_currency_credit_value_inr'] or 0) + (data['billed_from_april_inr'] or 0)
		
		try:
			data['inr_forex'] = a/b*c-d
			# frappe.log_error("@Forexa"+data['parent'],a)
			# frappe.log_error("@Forexb"+data['parent'],b)
			# frappe.log_error("@Forexc"+data['parent'],c)
			# frappe.log_error("@Forexd"+data['parent'],d)
		except:
			data['inr_forex'] = 0
			
		#accrued deferred in INR
		x2 = (data['recognised_revenue_till_march_inr'] or 0) + (data['journal_entry_value_inr'] or 0) + (data['recognised_revenue_from_april_inr'] or 0)
		y2 = (data['billed_till_march_inr'] or 0) + (data['base_currency_credit_value_inr'] or 0) + (data['billed_from_april_inr'] or 0)
		z2 = data['inr_forex']
		
		data['accrued_deferred_inr'] = x2 - y2 - z2
			
	return datas
