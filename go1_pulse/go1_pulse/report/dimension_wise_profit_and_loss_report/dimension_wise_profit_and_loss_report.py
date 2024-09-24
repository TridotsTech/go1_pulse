# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cstr, flt

import erpnext
from erpnext.accounts.report.financial_statements import (
	filter_accounts,
	filter_out_zero_value_rows,
)
from erpnext.accounts.report.trial_balance.trial_balance import validate_filters
from go1_pulse.queries import get_account_data, get_min_max_lft_rgt, get_account_names,get_gl_entries_by_account

def execute(filters=None):

	validate_filters(filters)
	dimension_list = get_dimensions(filters)

	if not dimension_list:
		return [], []

	columns = get_columns(dimension_list)
	data = get_data(filters, dimension_list)
	total_data = get_total_data(filters, dimension_list)

	return columns, data + total_data

def get_data(filters, dimension_list):
	company_currency = erpnext.get_company_currency(filters.company)

	acc = get_account_data(filters.company)
	if not acc:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(acc)
	min_lft, max_rgt = get_min_max_lft_rgt(filters.company)
	account = get_account_names(min_lft, max_rgt, filters.company)
	
	gl_entries_by_account = {}
	set_gl_entries_by_account(dimension_list, filters, account, gl_entries_by_account)
	format_gl_entries(
		gl_entries_by_account, accounts_by_name, dimension_list, frappe.scrub(filters.get("dimension"))
	)
	accumulate_values_into_parents(accounts, accounts_by_name, dimension_list)
	out = prepare_data(accounts, filters, company_currency, dimension_list)
	out = filter_out_zero_value_rows(out, parent_children_map)

	return out

def get_total_data(filters, dimension_list):
	company_currency = erpnext.get_company_currency(filters.company)

	acc = get_account_data(filters.company)
	if not acc:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(acc)

	min_lft, max_rgt = get_min_max_lft_rgt(filters.company)
	account = get_account_names(min_lft, max_rgt, filters.company)

	gl_entries_by_account = {}
	set_gl_entries_by_account(dimension_list, filters, account, gl_entries_by_account)
	format_gl_entries(
		gl_entries_by_account, accounts_by_name, dimension_list, frappe.scrub(filters.get("dimension"))
	)
	accumulate_values_into_parents(accounts, accounts_by_name, dimension_list)
	out = prepare_total_data(accounts, filters, company_currency, dimension_list)
	out = filter_out_zero_value_rows(out, parent_children_map)

	return out

def set_gl_entries_by_account(dimension_list, filters, account, gl_entries_by_account):
	condition = get_condition(filters.get("dimension"))
	if account:
		condition += " and account in ({})".format(", ".join([frappe.db.escape(d) for d in account]))

	gl_filters = {
		"company": filters.get("company"),
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date"),
		"finance_book": cstr(filters.get("finance_book")),
	}
	gl_filters["dimensions"] = set(dimension_list)

	if filters.get("include_default_book_entries"):
		gl_filters["company_fb"] = frappe.db.get_value(
			"Company", filters.company, "default_finance_book"
		)
  
	if filters.get("finance_book"):
		finance_book = f" and (finance_book in ('{filters.get('finance_book')}') or finance_book IS NULL)"
	else:
		finance_book = f" and finance_book IS NULL"

	gl_entries = get_gl_entries_by_account(frappe.scrub(filters.get("dimension")), condition, gl_filters,finance_book)

	for entry in gl_entries:
		gl_entries_by_account.setdefault(entry.account, []).append(entry)


def format_gl_entries(gl_entries_by_account, accounts_by_name, dimension_list, dimension_type):
	for entries in gl_entries_by_account.values():
		for entry in entries:
			d = accounts_by_name.get(entry.account)
			if not d:
				frappe.msgprint(
					_("Could not retrieve information for {0}.").format(entry.account),
					title="Error",
					raise_exception=1,
				)

			for dimension in dimension_list:
				if dimension == entry.get(dimension_type):
					d[frappe.scrub(dimension)] = (
						d.get(frappe.scrub(dimension), 0.0) + flt(entry.debit) - flt(entry.credit)
					)


def prepare_data(accounts, filters, company_currency, dimension_list):
	data = []
	pl_data = []
	for d in accounts:
		has_value = False
		total = 0
		row = {
			"account": d.name,
			"parent_account": d.parent_account,
			"indent": d.indent,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"currency": company_currency,
			"account_name": (
				"{} - {}".format(d.account_number, d.account_name) if d.account_number else d.account_name
			),
		}
		for dimension in dimension_list:
			row[frappe.scrub(dimension)] = (flt(d.get(frappe.scrub(dimension), 0.0), 3))

			if abs(row[frappe.scrub(dimension)]) >= 0.005:
				# ignore zero values
				has_value = True
				total += flt(d.get(frappe.scrub(dimension), 0.0), 3)
		row["has_value"] = has_value
		row["total"] = abs(total)
		data.append(row)
	for row in data:
		if row.get('account_name') == "Income":
			pl_data.append(row)
		if row.get('account_name') == "Expenses":
			pl_data.append(row)

	return data

def prepare_total_data(accounts, filters, company_currency, dimension_list):
	data = []
	has_value = False
	total = 0
	total_value = 0
	
	row = {
		"account": 'Expenses - IBSL',
		"parent_account": None,
		"indent": 0,
		"from_date": filters.from_date,
		"to_date": filters.to_date,
		"currency": company_currency,
		"account_name": 'Profit for The Year',
	}
	for dimension in dimension_list:
		indata = 0
		exdata = 0
		for d in accounts:
			if d.get('account_name') == "Income" or d.get('account_name') == "Expenses":
				if d.get('account_name') == "Income":
					indata = abs(flt(d.get(frappe.scrub(dimension), 0.0), 3))
				if d.get('account_name') == "Expenses":
					exdata = abs(flt(d.get(frappe.scrub(dimension), 0.0), 3))
					total_value = indata - exdata
					row[frappe.scrub(dimension)] = total_value
					if abs(row[frappe.scrub(dimension)]) >= 0.005:
						has_value = True
						total += total_value
		row["has_value"] = has_value
		row["total"] = total

	data.append(row)
	return data

def accumulate_values_into_parents(accounts, accounts_by_name, dimension_list):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			for dimension in dimension_list:
				accounts_by_name[d.parent_account][frappe.scrub(dimension)] = accounts_by_name[
					d.parent_account
				].get(frappe.scrub(dimension), 0.0) + d.get(frappe.scrub(dimension), 0.0)


def get_condition(dimension):
	conditions = []
	conditions.append("{0} in %(dimensions)s".format(frappe.scrub(dimension)))

	return " and {}".format(" and ".join(conditions)) if conditions else ""


def get_dimensions(filters):
	meta = frappe.get_meta(filters.get("dimension"), cached=False)
	query_filters = {}
	if meta.has_field("company"):
		query_filters = {"company": filters.get("company")}

	return frappe.get_all(filters.get("dimension"), filters=query_filters, pluck="name")


def get_columns(dimension_list):
	columns = [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 300,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]

	for dimension in dimension_list:
		columns.append(
			{
				"fieldname": frappe.scrub(dimension),
				"label": dimension,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 150,
			}
		)

	columns.append(
		{
			"fieldname": "total",
			"label": _("Total"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		}
	)

	return columns
