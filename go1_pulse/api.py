import frappe
from frappe import _
from frappe.utils import now, getdate, date_diff, get_last_day, get_first_day, add_days, add_months
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
import ast
import json
from erpnext.setup.utils import get_exchange_rate
import math
from frappe.utils import today
from frappe.model.db_query import check_parent_permission
from frappe.desk.reportview import validate_args
from dateutil import parser
from erpnext.assets.doctype.asset.depreciation import make_depreciation_entry,get_gl_entries_on_asset_disposal,depreciate_asset
from go1_pulse.queries import get_sales_order_billing_methods,get_employee,get_recognised_revenue,order_items_query,order_item,get_count,get_invoice_sum_of_so,get_revenue_recognized_sum

@frappe.whitelist()
def get_billing_details(parent):
	return frappe.get_all("Billing Method Type", {"parent": parent}, "type", pluck="type")


@frappe.whitelist()
def get_journal_entry(parent):
	return frappe.get_all("Journal Entry", {"sales_order": parent,"docstatus":1})

@frappe.whitelist()
def get_sales_order_offering(sales_order, item_code):
	return frappe.get_value("Sales Order Item", {"parent": sales_order,"item_code":item_code }, "offering")


def create_common_project(doc, method):
	for row in doc.items:
		if row.project:
			com_pro = frappe.new_doc("Common Project Mapper")
			com_pro.project = row.project
			com_pro.customer = doc.customer
			com_pro.end_customer = row.end_customer
			com_pro.cost_center = row.cost_center
			com_pro.mandate = row.mandate
			com_pro.sales_order = doc.name
			com_pro.sales_order_item = row.name
			com_pro.amount = round((row.amount - row.revenue_recognised_amount), 3)
			com_pro.offering = row.offering
			com_pro.currency = doc.currency
			com_pro.exchange_rate = doc.conversion_rate
			com_pro.recognised_amount = row.revenue_recognised_amount
			
			com_pro.revenue_recognition_credit_acount = frappe.get_value("Associated Offering Account", {"parent":row.offering, "lob": row.line_of_business, "mandate": row.mandate}, "credit_account") or \
														frappe.get_value("Associated Offering Account", {"parent":row.offering, "lob": row.line_of_business}, "credit_account")
			
			com_pro.revenue_recognition_debit_acount = frappe.get_value("Associated Offering Account", {"parent":row.offering, "lob": row.line_of_business, "mandate": row.mandate}, "debit_account") or \
													frappe.get_value("Associated Offering Account", {"parent":row.offering, "lob": row.line_of_business}, "debit_account")
			for bm in doc.billing_methods:
				if not bm.basis:
					frappe.throw(_("Basis is Mandatory", "Error"))
				if bm.basis.lower() == "activity" and bm.item_id == row.name:
					com_pro.append("activities_status",{"billing_milestone": bm.billing_milestone,"billing_reference":bm.name})
			
			com_pro.insert()

def update_common_project_mapper(doc, method):
	amount = 0
	vld_method = 0
	for row in doc.items:
		if row.project:
			amount = round((row.amount - row.revenue_recognised_amount), 3)
			frappe.db.sql(""" UPDATE `tabCommon Project Mapper` set amount =%(value)s WHERE sales_order=%(so_id)s and sales_order_item=%(soi_id)s
						""" ,{'value':amount,'so_id':doc.name,'soi_id':row.name})
			frappe.db.commit()

	so_billing_methods_validate = get_sales_order_billing_methods(doc.name)
	if so_billing_methods_validate:
		for x in so_billing_methods_validate:
			if x.so_amount != x.billing_amount:
				vld_method = vld_method + 1
		if vld_method > 0:
			frappe.msgprint("Total Amount Greater Than Billing Method Amount Please Update <br> <b>Billing Method (Billing) 234 </b>")


def update_common_project(doc, method):
	for item in doc.items:
		if item.billing_method not in ["Milestones", "Frequency"]:
			continue
		com_pro_name = frappe.get_value("Common Project Mapper", {"sales_order": doc.name, "sales_order_item": item.name}, "name")
		com_pro = frappe.get_doc("Common Project Mapper", com_pro_name)
		for cpm in com_pro.activities_status:
			for bm in doc.billing_methods:
				if cpm.billing_reference == bm.name and bm.basis.lower() == "activity":
					break
			else:
				frappe.db.delete("Associated Activity", {"name": cpm.name})
	
		for bm in doc.billing_methods:
			for cpm in com_pro.activities_status:
				if bm.name == cpm.billing_reference:
					break
			else:
				if bm.basis == "Activity":
					com_pro.append("activities_status",{"billing_milestone": bm.billing_milestone,"billing_reference":bm.name})
				
		com_pro.save()

	
def make_journal_entry(doc, method):
	if doc.revenue_recognition_voucher:
		if not doc.is_delivered:
			doc.is_delivered = 1
			
	if doc.is_delivered:           
		credit = doc.revenue_recognition_credit_acount or ""
		debit = doc.revenue_recognition_debit_acount or ""
		
		if doc.get_doc_before_save():
			if (not credit or not debit) and doc.offering:
				frappe.throw(f"Please Select Valid <b>Credit</b> And <b>Debit</b> Account In Offering <b>{doc.offering}</b>")
			
			if not credit and not debit: 
				return
			
			c_party_type , c_party = None,None
			d_party_type ,d_party = None,None 
			reference_type ,reference_name = None,None
			c_acc_type = frappe.get_value("Account", credit, "account_type")
			d_acc_type = frappe.get_value("Account", debit, "account_type")
			
			if c_acc_type in ["Receivable"]:
				c_party_type = "Customer"
				c_party = doc.customer
				reference_type = "Sales Order"
				reference_name = doc.sales_order
			
			if d_acc_type in ["Receivable"]:
				d_party_type = "Customer"
				d_party = doc.customer
				reference_type = "Sales Order"
				reference_name = doc.sales_order
			create_journal(doc=doc,c_party_type=c_party_type,credit=credit,c_party=c_party,debit=debit,d_party_type=d_party_type,d_party=d_party,reference_name=reference_name,reference_type=reference_type)

def create_journal(doc=None,credit=None,debit=None,c_party_type=None,c_party=None,d_party=None,d_party_type=None,reference_type=None,reference_name=None):

	if doc.is_delivered and not doc.revenue_recognition_voucher:	
		new_journal = frappe.new_doc("Journal Entry")
		new_journal.posting_date = doc.date_of_completion or now()
		new_journal.sales_order = doc.sales_order
		new_journal.sales_order_item = doc.sales_order_item
		new_journal.so_currency = doc.currency
		new_journal.is_from_report = 1
		new_journal._is_custom_journal_entry = 0
		
		so_currency = doc.currency
		company_currency = frappe.defaults.get_global_default("currency")
		
		exchange_rate = None
		if so_currency != company_currency:
			exchange_rate = get_exchange_rate(so_currency, company_currency, doc.date_of_completion)
			if not exchange_rate:
				return
		else:
			exchange_rate = 1
		new_journal.append("accounts", {"account": credit , "party_type": c_party_type,  "party": c_party,  "credit": doc.amount, 
						"credit_in_account_currency": doc.amount * exchange_rate if exchange_rate else 1, "reference_type": reference_type, "reference_name": reference_name,
						"so_currency": so_currency,  "so_exchange_rate": exchange_rate if exchange_rate else 1, "project": doc.project, "cost_center": doc.cost_center})
		
		new_journal.append("accounts", {"account": debit, "party_type": d_party_type,  "party": d_party, "debit":doc.amount , 
						"debit_in_account_currency": doc.amount * exchange_rate if exchange_rate else 1, "so_currency": so_currency,  
						"so_exchange_rate": exchange_rate if exchange_rate else 1, "project": doc.project, "cost_center": doc.cost_center})
		new_journal.insert()
		doc.revenue_recognition_voucher = new_journal.name
	

def check_billing_percentage(doc, method):
	item = {}
	for d in doc.billing_methods:
		if d.cpm_details:
			continue
		if d.billing_based_on == "Percentage":
			check_and_update_item(d, 'billing', 100, "Billing Percentage Can't Be Greater than 100%",item)
			
		elif d.billing_based_on == "Amount":
			check_and_update_item(d, 'billing_amt', doc.total, "Billing Amount Can't Be Greater than Total Amount",item)

	if len(item):
		for id in item:
			if item[id][2] == "Percentage" and float(item[id][0]) < 99.9:
					frappe.throw(f"Billing Percentage Can't Be Below 100% in table <b>Billing Methods</b>")
			elif item[id][2] == "Amount":
				so_amount = frappe.get_value('Sales Order Item',id,"amount")
				if float(item[id][0]) < so_amount:
					frappe.throw(f"Billing Amount Can't Be Below Total Amount in table <b>Billing Methods</b>")
			else:
				if float(item[id][0]) < 99.9:
					frappe.throw(f"Billing Percentage Can't Be Below 100% in table <b>Billing Methods </b>")

def check_and_update_item(d, key, limit, error_msg,item):
	value = getattr(d, key, None)
	
	if value and (d.item_id in item):
		item[d.item_id][0] += value
		item[d.item_id][1] = d.idx
		if float(item[d.item_id][0]) > limit:
			frappe.throw(f"{error_msg} in table <b>Billing Methods</b>")
		else:
			item[d.item_id] = [value, d.idx, d.billing_based_on]
			if float(value) > limit:
				frappe.throw(f"{error_msg} in table <b>Billing Methods</b>")
	

@frappe.whitelist()
def sendNotification(so = None, bm_ref = None):
	# sent notification for Activity basis
	if so and bm_ref:
		so_doc = frappe.get_doc("Sales Order", so)
		for row in so_doc.billing_methods:
			if row.basis == "Activity":
				if row.name == bm_ref:
					td = frappe.new_doc("Note")
					td.title = f"Activity({row.billing_milestone}) - {so_doc.name} - {row.name}"
					td.content = f"Date : {getdate()} \nYou Recieved This Notification For {row.billing}% Of Billing"
					exist = frappe.get_value("Note", td.get_title(), "name")
					if exist:
						return "Notification Sent Already"
					else:
						td.insert()
						frappe.db.set_value("Sales Order Billing Method",row.name, "activity_status", 1)
						return "Notification Sent Successfully"
	notification_based_on_date(so=so)
					
def notification_based_on_date(so=None):
	#sent notification for Date basis
	res = ""
	if not so:
		for name in frappe.get_all("Sales Order", {"docstatus": 1}):
			doc = frappe.get_doc("Sales Order", name)
			for row in doc.billing_methods:
				if row.basis == "Date" and row.date and getdate(row.date)  == getdate() and not row.is_billed and not row.activity_status:
					td = frappe.new_doc("Note")
					td.title = f"Date {getdate()} - {doc.name} - {row.name}"
					td.content = f"Date :{getdate()} \nYou Recieved This Notification For {row.billing}% Of Billing"
					exist = frappe.get_value("Note", td.get_title(), "name")
					if exist:
						res += "Notification Sent Already<br><hr>"
					else:
						td.insert()
						res += "Notification Sent Successfully<br><hr>"
	if res:
		return res


								
@frappe.whitelist()     
def get_common_project(offering = None, lob = None, mandate = None, cost_center = None):
	cp = ""
	if offering and lob and mandate and cost_center:
		cp = frappe.get_value("Associated Common Project", {"parent":offering, "lob": lob, "mandate":mandate, "cost_center": cost_center}, "project")
	elif offering and lob and cost_center:
		cp = frappe.get_value("Associated Common Project", {"parent":offering, "lob": lob, "cost_center": cost_center}, "project")	
	return cp



@frappe.whitelist()
def get_project_list(offering, mandate, lob,cost_center):
	pl = []
	if offering and mandate and lob and cost_center:
		pl = frappe.get_all("Associated Common Project", {"parent":offering, "lob": lob, "mandate":mandate,"cost_center":cost_center}, "project", pluck= "project")
	elif offering and lob and cost_center:
		pl = frappe.get_all("Associated Common Project", {"parent":offering, "lob": lob,"cost_center":cost_center}, "project",  pluck= "project")
	if pl:
		return pl
	return []


@frappe.whitelist()
def get_customer_list(customer):
	l = frappe.get_all("Customer", {"is_channel_partner": 0 , "channel_partner": customer}, "name", pluck= "name")
	return l

@frappe.whitelist()
def generate_employee_users():
	employees = get_employee()
	for x in employees:
		if not x.prefered_email:
			employee = frappe.get_doc("Employee",x.name)
			employee.prefered_email=x.company_email if x.prefered_contact_email == "Company Email" else x.personal_email
			employee.save(ignore_permissions=True)
			frappe.db.commit()
	
		employee = frappe.get_doc("Employee",x.name)
		if not frappe.db.get_all("User",{"email":employee.prefered_email}):
			if employee.prefered_email:
				user = create_user(x.name,email=employee.prefered_email)
				employee.user_id = user
				employee.save(ignore_permissions=True)
		else:
			employee.user_id = employee.prefered_email
			employee.save(ignore_permissions=True)

			
def create_user(employee, user=None, email=None):
	emp = frappe.get_doc("Employee", employee)

	employee_name = emp.employee_name.split(" ")
	middle_name = last_name = ""

	if len(employee_name) >= 3:
		last_name = " ".join(employee_name[2:])
		middle_name = employee_name[1]
	elif len(employee_name) == 2:
		last_name = employee_name[1]
	first_name = employee_name[0]
	user = frappe.new_doc("User")
	user.update(
		{
			"name": emp.employee_name,
			"email": emp.prefered_email,
			"enabled": 1,
			"first_name": first_name,
			"middle_name": middle_name,
			"last_name": last_name,
			"gender": emp.gender,
			"birth_date": emp.date_of_birth,
			"phone": emp.cell_number,
			"bio": emp.bio,
			"send_welcome_email":0,
		}
	)
	user.insert()
	return user.name


@frappe.whitelist()
def update_billing_status(si_doc= None, event= None):
	if not si_doc: return
	if si_doc.is_return: return
	list_bm ,list_cpm = None,None
	
	for item in si_doc.items:
		if item.sales_order and item.so_detail and item.bm_details:
			if item.cpm_details:
				list_cpm =  item.cpm_details.split('*')
			if item.bm_details:
				list_bm = item.bm_details.split('*')
			if list_bm:
				for bm in list_bm:
					bm_doc = frappe.get_doc("Sales Order Billing Method", bm)
					if not bm_doc.cpm_details and si_doc.docstatus !=0:
						is_billed=1 if si_doc.docstatus == 1  else 0
						frappe.db.set_value("Sales Order Billing Method", bm, {"is_billed":is_billed,"from_april": is_billed})
		
						if frappe.db.exists("Associated Activity", {"billing_reference":bm}):
							frappe.db.set_value("Associated Activity", frappe.db.exists("Associated Activity", {"billing_reference":bm}), "is_billed" , is_billed)
							
					elif bm_doc.cpm_details:
						frappe.db.set_value("Sales Order Billing Method", bm, {"is_billed":is_billed,"from_april": is_billed})
					
			if list_cpm:
				for cpm in list_cpm:
					frappe.db.set_value("Common Project Hour Or Unit", cpm, "is_billed", is_billed)
							


@frappe.whitelist()
def update_project_users(doc,method):
	if doc.users:
		frappe.db.sql("DELETE FROM `tabDocShare` WHERE share_doctype='Project' AND share_name='"+doc.name+"' ")
		frappe.db.commit()
		for x in doc.users:
			from frappe.share import add
			add(doctype="Project",name=doc.name,user=x.email,read=1)


@frappe.whitelist()
def update_is_billed_in_cpm(doc,method=None):
	for item in doc.items:
		com_pro_name = frappe.get_value("Common Project Mapper",
							{"sales_order": item.sales_order, "sales_order_item": item.so_detail}, "name")
		com_pro = frappe.get_doc("Common Project Mapper", com_pro_name)

		all_billed = frappe.db.sql(f"""SELECT CASE WHEN MIN(is_billed) = 1 AND MAX(is_billed) = 1 
								THEN 1 ELSE 0 END AS all_billed FROM `tabSales Order Billing Method` 
								WHERE parent = '{item.sales_order}' AND parentfield = 'billing_methods' 
								AND parenttype = 'Sales Order' AND item_id = '{item.so_detail}'""",as_dict=True)
		if all_billed[0]['all_billed']:
			com_pro.is_billed = 1
		com_pro.save()
		frappe.db.commit()


@frappe.whitelist()
def update_status():
	doc_list =  frappe.get_all("Sales Invoice", {"status":"Paid"}, pluck="name")
	for sid in doc_list:
		si_doc = frappe.get_doc("Sales Invoice", sid)
		
		for item in si_doc.items:
			if item.sales_order and item.so_detail:
				so_doc = frappe.get_doc("Sales Order", item.sales_order)
				for bm in so_doc.billing_methods:
					if bm.invoice_reference == si_doc.name:
						so_doc.billing_methods[bm.idx - 1].is_paid = 1
				so_doc.save()

@frappe.whitelist()
def month_diff(ed_date, st_date):
	if not ed_date and not st_date:
		return
	st_date = getdate(st_date); ed_date = getdate(ed_date)
	return (ed_date.year - st_date.year) * 12 + ed_date.month - st_date.month + 1



@frappe.whitelist()
def check_offering(so= None, soi= None):
	if not so and not soi: return
	bm = frappe.get_value("Sales Order Item", {"parent": so, "name": soi}, "billing_method")
	if bm == "Number of Units x Rate" or bm == "Monthly for hours worked":
		return 1
	else: return 0


def make_journal_for_equal_revenue(doc = None, event = None):
	if doc and doc.items:
		for row in doc.items:
			if row.revenue_method == "Equal revenue over the contract period":
				tran_date = None
				if getdate(doc.transaction_date) >= get_last_day(row.start_date):
					tran_date= get_last_day(row.start_date) if  getdate(doc.transaction_date) == get_last_day(row.start_date) else get_last_day(row.end_date) if getdate(doc.transaction_date) >= get_last_day(row.end_date) else add_days(get_first_day(doc.transaction_date), -1)
				else:
					return
			
				amount_to_consider = row.amount
				if row.revenue_recognised_amount:
					amount_to_consider = row.amount -row.revenue_recognised_amount
				
				if amount_to_consider < 1:continue
				
				total_days = date_diff(row.end_date, row.start_date) + 1 if date_diff(row.end_date, row.start_date) else 0
				billing_days = date_diff(tran_date, row.start_date) +1 if date_diff(tran_date, row.start_date) else 0
				
				if not billing_days:
					return
				if total_days:
					billable_amt = (amount_to_consider/total_days) * billing_days
				else:
					billable_amt = amount_to_consider
				create_journal_for_make_equal_revenue(row=row,billable_amt=billable_amt,doc=doc,tran_date=tran_date)
	
def create_journal_for_make_equal_revenue(row=None,doc=None,billable_amt=None,tran_date=None):
	credit_acount = frappe.get_value("Associated Offering Account", {"parent":row.offering, "lob": row.line_of_business, "mandate": row.mandate}, "credit_account") or frappe.get_value("Associated Offering Account", {"parent":row.offering, "lob": row.line_of_business}, "credit_account")
	debit_acount = frappe.get_value("Associated Offering Account", {"parent":row.offering, "lob": row.line_of_business, "mandate": row.mandate}, "debit_account") or frappe.get_value("Associated Offering Account", {"parent":row.offering, "lob": row.line_of_business}, "debit_account")
	
	if not credit_acount or not debit_acount:
		off_link = '<a href="/app/offering/{0}">{0}</a>'.format(row.offering)
		frappe.throw(_("Select Accounting Details for Offering <b>{0}</b>".format(off_link),  title=_("Accounting Details Missing")))
	
	c_party_type = None; c_party = None;d_party_type = None; d_party = None; reference_type = None; reference_name = None
	
	c_acc_type = frappe.get_value("Account", credit_acount, "account_type")
	d_acc_type = frappe.get_value("Account", debit_acount, "account_type")
	
	if c_acc_type in ["Receivable"] or d_acc_type in ["Receivable"]:
		c_party_type = "Customer"
		c_party = doc.customer
	
	if d_acc_type in ["Receivable"]:
		d_party_type = "Customer"
		d_party = doc.customer
		
	so_currency = doc.currency
	company_currency = frappe.defaults.get_global_default("currency")
	
	exchange_rate = None
	if so_currency != company_currency:
		exchange_rate = get_exchange_rate(so_currency, company_currency, tran_date)
		if not exchange_rate:
			return
	else:
		exchange_rate = 1
	
	new_journal = frappe.new_doc("Journal Entry")
	new_journal.voucher_type = "Deferred Revenue"
	new_journal.posting_date = tran_date
	new_journal.sales_order = doc.name
	new_journal.sales_order_item = row.name
	new_journal.is_from_report = 1
	new_journal.append("accounts", {"account": credit_acount , "party_type": c_party_type,  "party": c_party,  "credit": billable_amt, 
				"credit_in_account_currency": billable_amt * exchange_rate if exchange_rate else 1, "reference_type": reference_type, "reference_name": reference_name , 
				"so_currency": so_currency, "so_exchange_rate": exchange_rate if exchange_rate else 1, "project": row.project, "cost_center": row.cost_center})
	
	new_journal.append("accounts", {"account": debit_acount, "party_type": d_party_type, "party": d_party, "debit":billable_amt , 
				"debit_in_account_currency": billable_amt * exchange_rate if exchange_rate else 1, "so_currency": so_currency,
				"so_exchange_rate": exchange_rate if exchange_rate else 1, "project": row.project, "cost_center": row.cost_center})

	new_journal.insert()


@frappe.whitelist()
def make_equal_revenue(c_date=None, so=None, is_from_report=None):
	frappe.log_error(title="1",message=c_date)
	if not so:
		return


	c_date = getdate(c_date)
	doc = frappe.get_doc("Sales Order", so)
	messages = []

	for row in doc.items:
		if row.revenue_method == "Equal revenue over the contract period":
			process_revenue_item(doc, row, c_date, is_from_report, messages)
			



def process_revenue_item(doc, row, c_date, is_from_report, messages):
	frappe.log_error(title="2",message=doc)
	last_posting_date = frappe.db.get_list("Journal Entry",filters={"sales_order": doc.name, "sales_order_item": row.name, "docstatus": 1},
						fields=["posting_date"], order_by='posting_date desc',page_length=1)
	last_posting_date = last_posting_date[0]['posting_date'] if last_posting_date else None



	if c_date > row.end_date:
		c_date = row.end_date
	
	if not last_posting_date:
		last_posting_date = row.start_date
	
	if last_posting_date and last_posting_date < c_date:
		amount_to_consider = row.amount - row.revenue_recognised_amount if row.revenue_recognised_amount else row.amount
		total_jv =get_recognised_revenue(doc.name, row.name)

		total_recognized_revenue = total_jv[0].bc_recognised_revenue if total_jv else 0
		amount_to_consider -= total_recognized_revenue

		if amount_to_consider < 1:
			return
	
		total_days = date_diff(row.end_date, row.start_date) or 0
	
		billing_days = date_diff(c_date, last_posting_date) or 0
	
		billable_amt = (amount_to_consider / total_days) * billing_days if total_days else amount_to_consider
	
		if billable_amt > 0:
			create_journal_entry(doc, row, c_date, billable_amt, is_from_report, messages)



def create_journal_entry(doc, row, posting_date, billable_amt, is_from_report, messages):
	credit_account = frappe.get_value("Associated Offering Account", {"parent": row.offering, "lob": row.line_of_business, "mandate": row.mandate}, "credit_account") or \
					frappe.get_value("Associated Offering Account", {"parent": row.offering, "lob": row.line_of_business}, "credit_account")
					
					
	debit_account = frappe.get_value("Associated Offering Account", {"parent": row.offering, "lob": row.line_of_business, "mandate": row.mandate}, "debit_account") or \
					frappe.get_value("Associated Offering Account", {"parent": row.offering, "lob": row.line_of_business}, "debit_account")
	frappe.log_error(title="credit_account",message=credit_account)
	frappe.log_error(title="debit_account",message=debit_account)
	frappe.log_error(title="row",message=row)
	
							
	company_currency = frappe.defaults.get_global_default("currency")
	exchange_rate = get_exchange_rate(doc.currency, company_currency, posting_date) if doc.currency != company_currency else 1

	new_journal = frappe.new_doc("Journal Entry")
	new_journal.update({
		"voucher_type": "Deferred Revenue",
		"posting_date": posting_date,
		"sales_order": doc.name,
		"sales_order_item": row.name,
		"is_from_report": is_from_report or 0,
		"accounts": [
			{
				"account": credit_account,
				"party_type": "Customer" if frappe.get_value("Account", credit_account, "account_type") in ["Receivable"] else None,
				"party": doc.customer if frappe.get_value("Account", credit_account, "account_type") in ["Receivable"] else None,
				"credit": billable_amt,
				"credit_in_account_currency": billable_amt * exchange_rate,
				"so_currency": doc.currency,
				"so_exchange_rate": exchange_rate,
				"project": row.project,
				"cost_center": row.cost_center
			},
			{
				"account": debit_account,
				"party_type": "Customer" if frappe.get_value("Account", debit_account, "account_type") in ["Receivable"] else None,
				"party": doc.customer if frappe.get_value("Account", debit_account, "account_type") in ["Receivable"] else None,
				"debit": billable_amt,
				"debit_in_account_currency": billable_amt * exchange_rate,
				"so_currency": doc.currency,
				"so_exchange_rate": exchange_rate,
				"project": row.project,
				"cost_center": row.cost_center
			}
		]
	})
	new_journal.insert()
	
	frappe.db.commit()
	frappe.log_error(title="new_journal",message=new_journal)
	


@frappe.whitelist()
def create_invoice(source_name = None, datas = None, hours = None, billing= None,billing_amt= None, sales_order_item = None, cpm= None, cpm_details = None, bm_details=None, sales_return_details = None  ):

	if sales_return_details:
		return get_invoice_details(source_name, sales_return_details)
	
	if not datas and not all([source_name, sales_order_item, bm_details]) and (hours or billing):
		return
	
	so = frappe.get_doc("Sales Order", source_name)
	target = frappe.new_doc("Sales Invoice")
	target.customer = so.customer
	target.customer_address = so.customer_address
	target.currency = so.currency
	target.project = so.project
	
	if not datas:
		soi = frappe.get_doc("Sales Order Item", sales_order_item)
		item_hsn_code = frappe.db.get_value("Item", soi.item_code,'gst_hsn_code')
		offering_hsn_code = frappe.db.get_value('Offering', soi.offering, 'custom_hsnsac')
		income_account = frappe.get_doc("Offering", soi.offering).offering_income_account
		target.cost_center = soi.cost_center
		target.mandate = soi.mandate
		
		target.append(
			"items", {
				"item_code": soi.item_code, 
				"qty": hours if float(hours)> 0 else 1.0 , 
				"rate": soi.rate if float(hours) else (float(soi.amount)-float(soi.revenue_recognised_amount)) * (float(billing)/100),
				"so_rate": soi.rate if float(hours) else (float(soi.amount)-float(soi.revenue_recognised_amount)) * (float(billing)/100),
				"sales_order": source_name, 
				"so_detail": sales_order_item,
				"cpm" : cpm,
				"gst_hsn_code_c" : offering_hsn_code if offering_hsn_code else item_hsn_code,
				"gst_hsn_code" : offering_hsn_code if offering_hsn_code else item_hsn_code,
				"cpm_details": cpm_details ,
				"bm_details": bm_details ,
				"cost_center": soi.cost_center ,
				"project": soi.project ,
				"mandate":soi.mandate if soi.mandate else '',
				"income_account":income_account if income_account else None,
				})
		target.run_method("set_missing_values")
		return target
	if datas:
		create_invoice_if_data(datas=datas,source_name=source_name,target=target)
	target.run_method("set_missing_values")
	return target


def create_invoice_if_data(datas=None,source_name=None,target=None):
		
		items = {}
		msg =""
		
		for data in json.loads(datas):
		
			soi = frappe.get_doc("Sales Order Item", data['item_id'])
			
			item_hsn_code = frappe.db.get_value("Item", soi.item_code,'gst_hsn_code')
			
			offering_hsn_code = frappe.db.get_value('Offering', soi.offering, 'custom_hsnsac')
			
			
			if  int(data['is_billed']):
				continue
			
			if data['basis'] == "Activity" and frappe.db.exists("Associated Activity", {"billing_reference": data['name']}) and not frappe.get_doc("Associated Activity", {"billing_reference": data['name']}).completed:
				msg += "Activity status not completed for <b>billing milestone - {0}</b><br><hr>".format(data['billing_milestone'])
				continue
				
			if data['basis'] == "Date" and data['hours'] and not data['activity_status']:
				msg += "Activity status not completed at <b>Row - {0}</b><br><hr>".format(data['idx'])
			if data.get('billing_based_on'):
				if data['billing_based_on'] == "Amount":
					rate_value = float(data['billing_amt'])
				if data['billing_based_on'] == "Percentage":
					rate_value = soi.rate if float(data['hours']) else float(data['billing'])
			else:
				rate_value = soi.rate if float(data['hours']) else float(data['billing'])
		
			if data['item_id'] not in items:
				items[data['item_id']] = {
										"item_code": soi.item_code, 
										"qty": {"hours":float(data['hours'])} if float(data['hours'])>0 else 1.0 , 
										"rate": rate_value,
										"sales_order": source_name, 
										"so_detail": data['item_id'],
										"gst_hsn_code_c" : offering_hsn_code if offering_hsn_code else item_hsn_code,
										"gst_hsn_code" : offering_hsn_code if offering_hsn_code else item_hsn_code,
										"cost_center": soi.cost_center ,
										"project": soi.project ,
										"mandate":soi.mandate if soi.mandate else '',
										"cpm" :data['cpm'] if 'cpm' in data else "",
										"list_cpm_details": [data['cpm_details']] if 'cpm_details' in data else [] ,
										"list_bm_details": [data['name']],
										}			
			else:
				items[data['item_id']]["qty"] = {"hours":data['hours'] + items[data['item_id']]['qty']['hours']} if int(data['hours'])> 0 else 1.0
				if data.get('billing_based_on'):
					if data['billing_based_on'] == "Amount":
						items[data['item_id']]["rate"] = soi.rate if int(data['hours'])> 0 else items[data['item_id']]["rate"] + rate_value
					if data['billing_based_on'] == "Percentage":
						items[data['item_id']]["rate"] = soi.rate if int(data['hours'])> 0 else items[data['item_id']]["rate"] + float(data['billing'])
				else:
					items[data['item_id']]["rate"] = soi.rate if int(data['hours'])> 0 else items[data['item_id']]["rate"] + float(data['billing'])
				
				if 'cpm_details' in data:
					items[data['item_id']]["list_cpm_details"].append(data['cpm_details'])
				items[data['item_id']]["list_bm_details"].append(data['name'])
		
		if items:
			sales_order_item(items=items,target=target,data=data,msg=msg)
		if not items and not msg:
			return "No Data"
		if msg:
			frappe.throw(msg)


def sales_order_item(items=None,target=None,data=None,msg=None):
	for item in items:
		crate = items[item]['rate']
	
		soi = frappe.get_doc("Sales Order Item", item)
		item_hsn_code = frappe.db.get_value("Item", soi.item_code,'gst_hsn_code')
		offering_hsn_code = frappe.db.get_value('Offering', soi.offering, 'custom_hsnsac')
		income_account = frappe.get_doc("Offering", soi.offering).offering_income_account
		
		target.cost_center = soi.cost_center
		target.mandate = soi.mandate
		so_rate_amt = 0
		if data.get('billing_based_on'):
			
			if data['billing_based_on'] == "Percentage":
				so_rate_amt = items[item]['rate'] if type(items[item]['qty']) is dict else float(soi.amount) * (float(items[item]['rate'])/100)
			if data['billing_based_on'] == "Amount":
				so_rate_amt = items[items[item]['so_detail']]["rate"]
		else:
		
			so_rate_amt = items[item]['rate'] if type(items[item]['qty']) is dict else float(soi.amount) * (float(items[item]['rate'])/100)
		target.append(
			"items", {
				"item_code": items[item]['item_code'],
				"qty": items[item]['qty']['hours'] if type(items[item]['qty']) is dict else 1.0,
				"rate":  so_rate_amt,
				"so_rate":  so_rate_amt,
				"sales_order": items[item]['sales_order'], 
				"so_detail": items[item]['so_detail'], 
				"cost_center": soi.cost_center ,
				"project": soi.project ,
				"mandate":soi.mandate if soi.mandate else '',
				"cpm" : items[item]['cpm'], 
				"gst_hsn_code_c" : offering_hsn_code if offering_hsn_code else item_hsn_code,
				"gst_hsn_code" : offering_hsn_code if offering_hsn_code else item_hsn_code,
				"cpm_details": '*'.join(items[item]['list_cpm_details']), 
				"bm_details": '*'.join(items[item]['list_bm_details']) , 
				"income_account":income_account if income_account else None, 
				})



def get_invoice_details(so, sales_return_details):
	sales_return_details = json.loads(sales_return_details)
	flag = any([sd.get('amount') for sd in sales_return_details ])
	if sales_return_details and flag:
		so = frappe.get_doc("Sales Order", so)
		target = frappe.new_doc("Sales Invoice")
		target.customer = so.customer
		target.currency = so.currency
		target.project = so.project
		target.return_so_ref = so.name
	
		for data in sales_return_details:
			soi = frappe.get_doc("Sales Order Item", data.get('item_name'))
			income_account = frappe.get_doc("Offering", soi.offering).offering_income_account
			target.append(
				"items", {
					"item_code": soi.item_code, 
					"qty": 1.0,
					"rate": data.get('amount'),
					"sales_order": so.name, 
					"so_detail": soi.name,
					"income_account":income_account if income_account else None,
					"cost_center": soi.cost_center,
					"mandate": soi.mandate,
					"project": soi.project,
					"so_return_id":data.get('name')
					})
		target.run_method("set_missing_values")	
		return target


def create_new_custom_fields():
	custom_fields = {
		"Sales Invoice Item":[
			dict(
				fieldname="gst_hsn_code_c",
				fieldtype="Link",
				label="HSN/SAC",
				options="GST HSN Code",
				insert_after="item_group",
				fetch_from= "item_code.gst_hsn_code"
			),
		],
}
	custom_fields_c = {
		"Address":[
			dict(
				fieldname="gstin",
				fieldtype="Data",
				label="GSTIN",
				insert_after="links",
			),
			dict(
				fieldname="gst_category",
				fieldtype="Data",
				label="GST Category",
				insert_after="links",
			),
		],
}
	if "india_compliance" in frappe.get_installed_apps():
		create_custom_fields(custom_fields)
	else:
		unlink_custom_fields()
		create_custom_fields(custom_fields_c)

	
def unlink_custom_fields():
	frappe.db.set_value(
		"Custom Field",
		{"dt": "Sales Invoice Item", "fieldname": "gst_hsn_code_c"},
		{"fieldtype": "Data", "options": ""},
	)
	
	
def gen_billing_methods(frm= None, event= None):
		if not frm:
			return
		try:
			if frm.is_data_import and not frm.is_imported:
			
				frm.billing_methods = []
				for d in frm.items:
					if d.offering and d.billing_method_details and d.billing_method_details == "Single":
						r = frm.append("billing_methods")
						r.item_id = d.name
						r.item_code = d.item_code
						r.offering = d.offering
						r.billing = 100
						r.customer = d.end_customer
					
					if d.offering and d.billing_method_details and d.billing_method_details == "Multiple":
						for i in  range(d.no_of_process):
							r = frm.append("billing_methods")
							r.item_id = d.name
							r.item_code = d.item_code
							r.offering = d.offering
							r.billing = 100/d.no_of_process
							r.customer = d.end_customer
					
					if d.offering and d.billing_method == "Frequency":
						date = d.actual_start_date if d.actual_start_date else d.start_date
						nom = month_diff(ed_date= d.end_date, st_date= d.actual_start_date if d.actual_start_date else d.start_date)
						
						if not d.billing_method_details == "Monthly":
							if d.actual_start_date if d.actual_start_date else d.start_date <= d.actual_start_date if d.actual_start_date else d.start_date:
								nom -= 1
						
						nor =  math.ceil(nom/12) if d.billing_method_details == "Annual" else  math.ceil(nom/6) if d.billing_method_details == "Half Yearly" else math.ceil(nom/3) if d.billing_method_details == "Quarterly" else  math.ceil(nom/1) if d.billing_method_details in ["Monthly", "Number of Units x Rate", "Monthly for hours worked"] else 0
						noi =  12 if d.billing_method_details == "Annual" else  6 if d.billing_method_details == "Half Yearly" else  3 if d.billing_method_details == "Quarterly" else 1 if d.billing_method_details in ["Monthly", "Number of Units x Rate", "Monthly for hours worked"] else 0
						
						for  i in  range(nor):
							r = frm.append("billing_methods")
							r.item_code = d.item_code
							r.item_id = d.name
							r.customer = d.end_customer
							if d.billing_method_details != "Monthly":
								r.billing = 100/nor
								
							r.offering = d.offering
							r.basis = "Date"
							if d.billing_method_details == "Monthly":
								if i+1 == nor:
									r.date = d.end_date
									r.billing = 100/nor
				
								else:
									r.date = date
									r.billing = 100/nor
				
							else:
								r.date = add_days(add_months(date,noi),-1)
							
							date = add_days(add_months(date,noi), -1)
							date = add_days(date, 1)
				frm.is_imported = 1
		except Exception as e:
			pass



def update_employee_expense(self, event = None):
	total_debit_by_projects = {}
	total_credit_by_projects = {}

	for row in self.accounts:
		if row.debit:
			if row.project in total_debit_by_projects:
				total_debit_by_projects[row.project] += row.debit
			else:
				if row.project:
					total_debit_by_projects[row.project] = row.debit
					
	for row in self.accounts:
		if row.credit:
			if row.project in total_credit_by_projects:
				total_credit_by_projects[row.project] += row.credit
			else:
				if row.project:
					total_credit_by_projects[row.project] = row.credit
					
	if self.emp_expense_reference:               
		for project in total_debit_by_projects:
			old_exp = frappe.db.get_value("Project", project,"total_employee_cost")
			if  self.docstatus == 1:
				frappe.db.set_value("Project", project, "total_employee_cost", old_exp+total_debit_by_projects[project])
			if  self.docstatus == 2:
				frappe.db.set_value("Project", project, "total_employee_cost", old_exp-total_debit_by_projects[project])
	
			
def update_poc_revenue(self, event = None):
	total_credit_by_projects = {}
	for row in self.accounts:
		if row.credit and row.so_exchange_rate and row.so_exchange_rate > 0:
			if row.project in total_credit_by_projects:
				total_credit_by_projects[row.project] += round(row.credit/row.so_exchange_rate)
			else:
				if row.project:
					total_credit_by_projects[row.project] = (row.credit/row.so_exchange_rate)
	if self.sales_order and self.sales_order_item:   
		for project in total_credit_by_projects:
			old_rev = frappe.db.get_value("Common Project Mapper", {"sales_order": self.sales_order, "sales_order_item": self.sales_order_item},"recognised_amount") or 0
			if  self.docstatus == 1:
				frappe.db.set_value("Common Project Mapper",  {"sales_order": self.sales_order, "sales_order_item": self.sales_order_item}, "recognised_amount", old_rev + total_credit_by_projects[project])
			if  self.docstatus == 2:
				frappe.db.set_value("Common Project Mapper",  {"sales_order": self.sales_order, "sales_order_item": self.sales_order_item}, "recognised_amount", old_rev - total_credit_by_projects[project])


def check_project_budget(self, element):
	
	for row in self.items:
		if row.revenue_method and row.revenue_method.lower() ==  "poc":
			if row.project:
				budget = frappe.db.get_value("Project", row.project, "estimated_costing")
				if not budget:
					# pro_link = '<a href="/app/project/{0}">{0}</a>'.format(row.project)
					# frappe.throw(_("Please provide an estimated project cost for <b>{0}</b>".format(pro_link), title="Message"))
					pro_link = '<a href="/app/project/{0}">{0}</a>'.format(row.project)
					frappe.throw("Please provide an estimated project cost for <b>{0}</b>".format(pro_link), title="Message")



def check_common_project_mapper_status(self, element):
	doc_id = frappe.db.get_list('Common Project Mapper',filters={'sales_order': self.name },fields=['name'],as_list=0)
	for row in doc_id:
		cpm_doc = frappe.get_doc('Common Project Mapper', row.name)
		if cpm_doc:
			cpm_doc.sales_order_status = self.status
			cpm_doc.save()


@frappe.whitelist(allow_guest=True)
def update_old_sales_invoice_project():
	rows = 0
	order_items = order_items_query()
	for row in order_items:
		rows = rows + 1
		if row.so_mandate:
			frappe.db.sql("""UPDATE `tabSales Invoice Item` set mandate =%(mandate)s WHERE name=%(sii_id)s""",{'mandate':row.so_mandate,'sii_id':row.si_id})
		frappe.db.sql("""UPDATE `tabSales Invoice Item` set project =%(project)s ,cost_center = %(cost_center)s WHERE name=%(sii_id)s""",
						{'project':row.so_project,'cost_center':row.cost_center,'sii_id':row.si_id})
		frappe.db.commit()
	if rows > 0 :
		return {"msg":"Total updated Rows " + str(rows)}
	else:
		return {"msg":"No Rows updated"}




@frappe.whitelist(allow_guest=True)
def update_old_common_project_mapper():
	rows = 0
	order_items = order_item()
	for row in order_items:
		rows = rows + 1
		frappe.db.sql("""UPDATE `tabCommon Project Mapper` set sales_order_status =%(data)s WHERE name=%(id)s""",{'data':row.so_status,'id':row.cpm_id})
		frappe.db.commit()
	if rows > 0 :
		return {"msg":"Total updated Rows " + str(rows)}
	else:
		return {"msg":"No Rows updated"}



def update_sales_return(doc, event):
	
	if doc.is_return:
		if doc.items:
			if doc.items[0].sales_order:
				so = frappe.get_doc("Sales Order", doc.items[0].sales_order)
				for item in doc.items:
					so.append("si_return_details", {"item_name": item.so_detail, "item_code": item.item_name, "amount":  abs(item.amount)})
				so.save()
	else:
		if doc.items:
			for item in doc.items:
				if item.so_return_id and item.sales_order:
					so_rt_doc = frappe.get_doc("Sales Order Return Amount Details",item.so_return_id)
					so_rt_doc.is_invoiced=1
					so_rt_doc.save()



def validate_service_date(doc, event):
	if doc.items:
		for item in doc.items:
			if item.revenue_method == "Equal revenue over the contract period" and (not item.start_date or not item.end_date):
				frappe.throw(_("Incorrect Start Date / End Date in the Item Table - <b>Row {0}</b>".format(item.idx),title="Date Missing"))

			
def add_user(doc, event):
	doc.user = doc.owner


@frappe.whitelist()
def post_depreciation_entry(datas):
	datas = json.loads(datas)
	flag = 0
	for data in datas:
		if parser.parse(data['Data']["scheduled_depreciation_date"]) < parser.parse(today()):
			flag = 1
		asset_name = data['Data']['asset_id']
		scheduled_depreciation_date = data['Data']['scheduled_depreciation_date']
		make_depreciation_entry(asset_name, scheduled_depreciation_date)
		frappe.db.commit()
	if not flag:
		return "No More Entries To Make Depreciation"

	return  "Entries Created Successfully"


def add_linked_po(doc, method):
	po_list = []
	for item in doc.items:
		if item.linked_purchase_order:
			p_list = [{ "purchase_order":po } for po in item.linked_purchase_order.split('\n') if po] 
			if p_list:
				po_list.extend(p_list)
	if po_list:
		for po in po_list:
			doc.append("purchase_order", po)


@frappe.whitelist()
def get_linked_order(name, doctype):
	count = get_count(name,doctype)
	frappe.errprint(count)
	return len(count) or 0 if count else 0


@frappe.whitelist()
def get_order_items(doctype, txt, searchfield, start, page_len, filters):
	try:
		txtcondition =""
		if txt:
			txtcondition += ' AND (o.item_name like %(txt)s or o.name like %(txt)s)'
		query = ''' SELECT o.name,o.item_name	FROM `tabSales Order Item` o WHERE o.parent="{orderid}" {txtcondition}  
					GROUP BY o.name,o.item_name	'''.format(txtcondition=txtcondition, orderid=filters.get('order_id'))
		return frappe.db.sql(query,{'txt':'%'+txt+'%'})
	except Exception:
		frappe.log_error(frappe.get_traceback(), "go1_pulse.go1_pulse.api.get_order_items") 


@frappe.whitelist()
def check_address(customer= None, customer_address= None):
	bm = frappe.get_value("Dynamic Link", {"parent": customer_address,"link_name":customer}, "link_name")
	if bm:
	
		return 1
	else:
		return 0


@frappe.whitelist()
def validate_link(doctype: str, docname: str, fields=None):
	
	if not isinstance(doctype, str):
		frappe.throw("DocType must be a string")

	if not isinstance(docname, str):
		frappe.throw("Document Name must be a string")

	if doctype != "DocType" and doctype != "Sales Order Item" and not (
		frappe.has_permission(doctype, "select") or frappe.has_permission(doctype, "read")
	):
		frappe.throw(
			_("You do not have Read or Select Permissions for {}").format(frappe.bold(doctype)),
			frappe.PermissionError,
		)
	
	values = frappe._dict()
	values.name = frappe.db.get_value(doctype, docname, cache=True)
	
	fields = frappe.parse_json(fields)

	if not "india_compliance" in frappe.get_installed_apps():
		if "gst_hsn_code" in fields:
			fields.remove("gst_hsn_code")
	
	if not values.name or not fields:
		return values

	try:
		values.update(get_value(doctype, fields, docname))
	except frappe.PermissionError:
		frappe.clear_last_message()
		frappe.msgprint(_("You need {0} permission to fetch values from {1} {2}").format(
				frappe.bold(_("Read")), frappe.bold(doctype), frappe.bold(docname)
			),
			title=_("Cannot Fetch Values"),
			indicator="orange",
		)
	return values	

@frappe.whitelist()
def get_value(doctype, fieldname, filters=None, as_dict=True, debug=False, parent=None):
	from frappe.utils import get_safe_filters
	"""Returns a value form a document
	:param doctype: DocType to be queried
	:param fieldname: Field to be returned (default `name`)
	:param filters: dict or string for identifying the record"""
	if frappe.is_table(doctype):
		check_parent_permission(parent, doctype)

	if not frappe.has_permission(doctype, parent_doctype=parent):
		frappe.throw(_("No permission for {0}").format(_(doctype)), frappe.PermissionError)

	filters = get_safe_filters(filters)
	if isinstance(filters, str):
		filters = {"name": filters}

	try:
		fields = frappe.parse_json(fieldname)
	except (TypeError, ValueError):
		fields = [fieldname]

	if not filters:
		filters = None

	if frappe.get_meta(doctype).issingle:
		value = frappe.db.get_values_from_single(fields, filters, doctype, as_dict=as_dict, debug=debug)
	else:
		value = get_list(doctype,filters=filters,fields=fields,debug=debug,limit_page_length=1,parent=parent,as_dict=as_dict)

	if as_dict:
		return value[0] if value else {}

	if not value:
		return

	return value[0] if len(fields) > 1 else value[0][0]


@frappe.whitelist()
def get_list(doctype,fields=None,filters=None,order_by=None,limit_start=None,limit_page_length=20,parent=None,debug=False,as_dict=True,or_filters=None):
	"""Returns a list of records by filters, fields, ordering and limit

	:param doctype: DocType of the data to be queried
	:param fields: fields to be returned. Default is `name`
	:param filters: filter list by this dict
	:param order_by: Order by this fieldname
	:param limit_start: Start at this index
	:param limit_page_length: Number of records to be returned (default 20)"""
	if frappe.is_table(doctype):
		check_parent_permission(parent, doctype)

	args = frappe._dict(
		doctype=doctype,
		parent_doctype=parent,
		fields=fields,
		filters=filters,
		or_filters=or_filters,
		order_by=order_by,
		limit_start=limit_start,
		limit_page_length=limit_page_length,
		debug=debug,
		as_list=not as_dict,
	)

	validate_args(args)
	return frappe.get_list(**args)


@frappe.whitelist()
def scrap_asset(asset_name):

	date = today()
	asset = frappe.get_doc("Asset", asset_name)
	if asset.docstatus != 1:
		frappe.throw(_("Asset {0} must be submitted").format(asset.name))
	elif asset.status in ("Cancelled", "Sold", "Scrapped", "Capitalized", "Decapitalized"):
		frappe.throw(
			_("Asset {0} cannot be scrapped, as it is already {1}").format(asset.name, asset.status)
		)
	
	depreciation_series = frappe.get_cached_value(
		"Company", asset.company, "series_for_depreciation_entry"
	)
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.naming_series = depreciation_series
	je.posting_date = date
	je.company = asset.company
	je.remark = "Scrap Entry for asset {0}".format(asset_name)

	for entry in get_gl_entries_on_asset_disposal(asset, date):
		entry.update({"reference_type": "Asset", "reference_name": asset_name})
		je.append("accounts", entry)
	je.flags.ignore_permissions = True
	je.save()
	frappe.db.commit()

	frappe.db.set_value("Asset", asset_name, "disposal_date", date)
	frappe.db.set_value("Asset", asset_name, "journal_entry_for_scrap", je.name)
	asset.set_status("Scrapped")

	frappe.msgprint(_("Asset scrapped via Journal Entry {0}").format(je.name))


@frappe.whitelist()
def assets_list(names,docstatus,doctype):
	try:
		import json
		data = json.loads(names)
		if len(data)==0:
			frappe.throw(_('Please select any items'), title=_('Error'))
			
		else:
			
			assets =[]
			for item in data:
				asset_list= frappe.get_doc(doctype,item)
				if asset_list.status == "Fully Depreciated" or asset_list.status == "Partially Depreciated" or asset_list.status == "Submitted":
					assets.append({'name':asset_list.name,'item_name':asset_list.item_name})
				
					return assets
				else:
					frappe.throw(_('Asset status already changed to '+asset_list.status), title=_('Error'))
				
					
	except Exception:
		frappe.log_error(frappe.get_traceback(), "go1_pulse.api.assets_list") 

@frappe.whitelist()
def create_invoice_assets(assets_items = None):
	assets_items = json.loads(assets_items)
	if assets_items:
		target = frappe.new_doc("Sales Invoice")
		for row in assets_items:
			if row.get('status') == "Fully Depreciated" or row.get('status') == "Partially Depreciated" or row.get('status') == "Submitted":
				item_code = frappe.db.get_value('Asset', row.get('name'), 'item_code')
				item_name = frappe.db.get_value('Item', item_code, 'item_name')
				uom = frappe.db.get_value('Item', item_code, 'stock_uom')
				description = frappe.db.get_value('Item', item_code, 'description')
				target.append("items", {
						"item_code": item_code,
						"item_name": item_name,
						"qty": row.get('asset_quantity') if row.get('asset_quantity') else 1,
						"description":description,
						"uom":uom,
						"asset":row.get('name')
						})
		return target

@frappe.whitelist()
def create_transfer_assets(assets_items = None):
	assets_items = json.loads(assets_items)
	if assets_items:
		target = frappe.new_doc("Asset Movement")
		target.purpose = "Transfer"
		for row in assets_items:
			if row.get('status') == "Fully Depreciated":
			
				target.append("assets", {
						"asset": row.get('name'),
						"source_location": row.get('location')
						})
		return target


@frappe.whitelist()
def set_party_name(order_id = None):
	customer = frappe.db.get_value('Sales Order', order_id, 'customer')
	return customer


@frappe.whitelist()
def check_installed_app(app_name):
	if app_name in frappe.get_installed_apps():
		return {"status":"Success"}
	return {"status":"Failed"}


def get_jv_number_series(posting_date):
	if getdate(posting_date)> getdate('2024-03-31'):
		return "ACC-JV-2425-"
	else:
		return "ACC-JV-2024-"


@frappe.whitelist()
def update_jv_naming_series(doc,method):
	if doc.voucher_type in ["Journal Entry","Journal Voucher","Bank Entry",
						"Cash Entry","Credit Card Entry",
						"Contra Entry","Exchange Rate Revaluation",
						"Exchange Gain or Loss","Deferred Expense"]:
		jv_number_series = get_jv_number_series(doc.posting_date)
		doc.naming_series = jv_number_series

def generic_so_update_validation(doc, method=None):
	if doc.docstatus == 1:
		prev_total = frappe.db.get_value('Sales Order', doc.name, "rounded_total")
		updated_total = doc.rounded_total
		if prev_total != updated_total:
			invoice_sum_of_so = get_invoice_sum_of_so(doc.name)
			if updated_total < invoice_sum_of_so:
				frappe.throw(_("Error!"))


def update_so_tag(doc,method=None):
	if doc.custom_so_tag != "Revised":
		doc.custom_so_tag = 'Revised'

		
def so_update_approval(doc,method=None):
	if doc.docstatus == 1:
		prev_total = frappe.db.get_value('Sales Order',doc.name,"rounded_total")
		updated_total = doc.rounded_total

		if prev_total != updated_total:
			doc.so_status = 'On-Hold'
			doc.sent_for_approval = True

@frappe.whitelist()
def validate_before_closing(docName):
	sum_of_revenue_recognized = get_revenue_recognized_sum(docName)

	invoice_sum_of_so = get_invoice_sum_of_so(docName)
	frappe.log_error('validate_before_closing', [sum_of_revenue_recognized, invoice_sum_of_so])
	if sum_of_revenue_recognized != invoice_sum_of_so:
		frappe.throw(_("Can't Close! RR != Billed Value!"))

