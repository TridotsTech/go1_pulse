# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from frappe.model.document import Document
from erpnext.controllers.accounts_controller import update_child_qty_rate
from frappe.utils import now
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.general_ledger import check_freezing_date
import json
from go1_pulse.api import make_equal_revenue
from go1_pulse.queries import get_billing_hours

class CommonProjectMapper(Document): 
    def get_diff_item(self, element):
        return element.item_id != self.sales_order_item
    
    def get_same_item(self, element):
        return element.item_id == self.sales_order_item and element.is_billed
    
    def get_new_rows(self, element):
        return not element.is_billed
    
    def before_save(self):
        if self.revenue_recognition_voucher and not self.is_delivered :
            self.is_delivered = 0
            
        #update hour or units in sales order billing method table
        if self.hours_or_units:
            doc = frappe.get_doc("Sales Order", self.sales_order)
            item_code = frappe.get_value("Sales Order Item", {"parent": self.sales_order, "name": self.sales_order_item}, "item_code")
            
            old_diff_data= list(filter(self.get_diff_item, doc.billing_methods))
            old_same_data= list(filter(self.get_same_item, doc.billing_methods))
            new_rows = list(filter(self.get_new_rows, self.hours_or_units))
            frappe.log_error(title="test",message=new_rows)
            
            con_data= old_diff_data + old_same_data
            doc.billing_methods = []
            
            for data in con_data:
                doc.append("billing_methods", data.as_dict())
            for data in new_rows:
                doc.append("billing_methods",
                            {"item_code": item_code,
                            "item_id": self.sales_order_item,
                            "basis": "Date", 
                            "date": data.to_date,
                            "offering": self.offering,
                            "hours":data.total_hours_or_units,
                            "cpm":self.name,
                            "cpm_details": data.name,
                            "is_billed": data.is_billed,
                            "activity_status": data.is_completed
                            })
            doc.save()
            
            
    def validate(self):
        if self.is_delivered:
            check_freezing_date(self.date_of_completion)

    def on_trash(self):
        frappe.db.delete("Associated Activity", {"parent": self.name})
        frappe.db.delete("Common Project Hour Or Unit", {"parent": self.name})

@frappe.whitelist()
def get_timesheet_billing_hours(project = None, f_date = None, t_date= None):
    if not project:
        return
    billing_hrs = frappe.db.sql("""SELECT 
                                SUM(hours) AS hours
                                FROM `tabTimesheet Detail`
                                WHERE project = '{0}' AND approval_status= 'Approved' AND docstatus = 1 AND to_time BETWEEN '{1}' AND '{2}' 
                                GROUP BY project""" .format(project, f_date, t_date))
    if billing_hrs:
        if billing_hrs[0]:
            if billing_hrs[0][0]:
                return billing_hrs[0][0]
        else:
            frappe.throw("No Record found")
            
            
@frappe.whitelist()
def make_journal_for_poc(source, posting_date, is_from_report = None):
    msg = []
    doc = frappe.get_doc("Common Project Mapper", source)
    so_doc = frappe.get_doc("Sales Order Item", doc.sales_order_item)
    frappe.log_error(title="do_doc",message=so_doc)
    if not doc.project:
        return
   
    credit_acount = doc.revenue_recognition_credit_acount
    debit_acount = doc.revenue_recognition_debit_acount
    
    if not credit_acount and not debit_acount:
        credit_acount = frappe.get_value("Associated Offering Account", {"parent":doc.offering,"lob": frappe.get_doc("Sales Order Item", 
                        doc.sales_order_item).line_of_business, "mandate": frappe.get_doc("Sales Order Item", doc.sales_order_item).mandate}, "credit_account") or \
                        frappe.get_value("Associated Offering Account", 
                        {"parent":doc.offering, "lob": frappe.get_doc("Sales Order Item", doc.sales_order_item).line_of_business}, "credit_account")
            
        debit_acount =  frappe.get_value("Associated Offering Account", {"parent":doc.offering,"lob": frappe.get_doc("Sales Order Item", doc.sales_order_item).line_of_business, 
                        "mandate": frappe.get_doc("Sales Order Item", doc.sales_order_item).mandate}, "debit_account") or \
                        frappe.get_value("Associated Offering Account", 
                         {"parent":doc.offering, "lob": frappe.get_doc("Sales Order Item", doc.sales_order_item).line_of_business}, "debit_account")
    
   
    
    c_party_type = None; c_party = None;d_party_type = None; d_party = None; reference_type = None; reference_name = None
    c_acc_type= frappe.get_value("Account", credit_acount, "account_type")
    d_acc_type=frappe.get_value("Account",debit_acount,"account_type")
    
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
  
    new_journal = frappe.new_doc("Journal Entry")
    if is_from_report:
        new_journal.is_from_report = 1
    new_journal.posting_date = posting_date or now()
    new_journal.sales_order = doc.sales_order
    new_journal.sales_order_item = doc.sales_order_item
    new_journal.so_currency = doc.currency
    
    so_currency = doc.currency
    company_currency = frappe.defaults.get_global_default("currency")
    
    exchange_rate = None
    if so_currency != company_currency:
        exchange_rate = get_exchange_rate(so_currency, company_currency, posting_date or now())
        if not exchange_rate:
            return
    if not exchange_rate:
        exchange_rate = 1
        
    #poc calculation
    project = frappe.get_doc("Project", doc.project)
    budget = project.estimated_costing
    actual_cost = project.total_purchase_cost + project.total_employee_cost
    
    if not actual_cost:
        return
    poc = round((actual_cost / budget), 2 ) * 100
    
    if round((so_doc.amount * (poc/100)), 2) <= doc.recognised_amount:
        return ["No more revenue to recognise Sales Order - {0}".format(doc.sales_order)]

    rec_revenue = round((so_doc.amount * (poc/100)), 2) - doc.recognised_amount
    if rec_revenue < 1:
        return
        
    if (doc.recognised_amount + rec_revenue) > so_doc.amount:
        rec_revenue =  so_doc.amount - doc.recognised_amount
    new_journal.append("accounts", 
                       {"account": credit_acount , 
                        "party_type": c_party_type,  
                        "party": c_party, 
                        "credit_in_account_currency": rec_revenue * exchange_rate, 
                        "reference_type": reference_type, 
                        "reference_name": reference_name, 
                        "so_currency": so_currency,  
                        "so_exchange_rate":  exchange_rate, 
                        "project": doc.project, 
                        "cost_center": doc.cost_center })
    
    new_journal.append("accounts", 
                       {"account": debit_acount,
                        "party_type": d_party_type, 
                        "party": d_party,
                        "debit_in_account_currency": rec_revenue * exchange_rate,
                        "so_currency": so_currency,  "so_exchange_rate":  exchange_rate,
                        "project": doc.project,
                        "cost_center": doc.cost_center })
    new_journal.insert()
   
    doc.save()

    

@frappe.whitelist()
def make_journal_for_expense(expense_type = None, datas = None, posting_date = None):
    msg=validations_for_msgprint(datas=datas,posting_date=posting_date,expense_type=expense_type)
    frappe.msgprint("Every entry is added in the background.")
    frappe.enqueue(
        job_name= "Journal For {}".format(expense_type),
        method=my_enqueue,
		queue="long",
		timeout=600,
		is_async=True,
		**{"expense_type": expense_type, "datas": datas,"posting_date": posting_date}
    )

    
    
    
def my_enqueue(expense_type, datas,posting_date ):
    datas = json.loads(datas)
    if not datas: return
    datas = [data['Data'] for data in datas]
    
    if expense_type =="POC":
        for data in datas:
            frappe.log_error(title="data",message=data)
            source =  frappe.get_doc("Common Project Mapper", 
                                     {"sales_order":data.get("sales_order"), "sales_order_item": data.get("so_item")}).name
            if not source:continue
            ret_msg= make_journal_for_poc(source = source, posting_date= posting_date, is_from_report = 1) or []    
    else:
        for data in datas:
            frappe.log_error(title="test",message=data)
            ret_msg = make_equal_revenue(c_date= posting_date, so = data.get("sales_order"), is_from_report = 1) or []
           
           
           
           
           
            
   
def validations_for_msgprint(datas=None,posting_date=None,expense_type=None):
    messages= ""
    if not posting_date:
        frappe.throw("Enter valid date")
    datas = json.loads(datas)
    if datas:
        frappe.log_error(title="datas",message=datas)
        datas = [data['Data'] for data in datas]
        
        #Expense Type Validation
        if expense_type != "POC":
            for data in datas:
                so=data.get("sales_order")
                doc = frappe.get_doc("Sales Order", so)
                
                if so:
                    
                    doc = frappe.get_doc("Sales Order", so)
                    for row in doc.items:
                        #validation For Equal Revenue Method
                        if row.revenue_method == "Equal revenue over the contract period":
                            frappe.log_error(title="lob",message=row.line_of_business)
                            credit_account = frappe.get_value("Associated Offering Account", {"parent": row.offering, "lob": row.line_of_business, "mandate": row.mandate}, "credit_account") or \
                                                frappe.get_value("Associated Offering Account", {"parent": row.offering, "lob": row.line_of_business}, "credit_account")
                        
                            frappe.log_error(title="credit",message=credit_account)
                            debit_account = frappe.get_value("Associated Offering Account", {"parent": row.offering, "lob": row.line_of_business, "mandate": row.mandate}, "debit_account") or \
                                            frappe.get_value("Associated Offering Account", {"parent": row.offering, "lob": row.line_of_business}, "debit_account")
                            frappe.log_error(title="debit",message=debit_account)
                            existing_journal = frappe.db.exists("Journal Entry", {"sales_order": doc.name, "sales_order_item": row.name, "is_from_report": 1, "docstatus": 0})
                            
                            # startdate & Enddate Validation
                            if not row.start_date or not row.end_date:
                                so_link = f'<a href="/app/sales-order/{doc.name}">{doc.name}</a>'
                                messages += f"Incorrect Start Date, End Date in the Sales Order - <b>{so_link}</b><br> <b>row {row.idx}</b>"
                                
                                frappe.throw(messages)
                            
                            #credit a/c Debit A/c Validations
                            if not credit_account or not debit_account:
                                off_link = f'<a href="/app/offering/{row.offering}">{row.offering}</a>'
                                messages += f"Select Accounting Details for Offering <b>{off_link}</b>"
                                frappe.log_error(2)
                                frappe.throw(messages)
                                
                            #Existing Journal Entry Validation
                            if existing_journal:
                                jv_link = f'<a href="/app/journal-entry/{existing_journal}">{existing_journal}</a>'
                                messages += f"Already created a journal entry for the sales order {doc.name} <br> {jv_link}"
                                
                                frappe.throw(messages)
                                
        #validation For Poc 
        if expense_type == "POC":
            for data in datas:
                so=data.get("sales_order")
                so_item=data.get("so_item")
                doc = frappe.get_doc("Sales Order", so)
                source =  frappe.get_doc("Common Project Mapper", 
                                    {"sales_order":so, "sales_order_item": so_item}).name
                frappe.log_error(title="source",message=source)
                if source:
                    cpm = frappe.get_doc("Common Project Mapper", source)
                    so_doc = frappe.get_doc("Sales Order Item", cpm.sales_order_item)
                    if cpm.recognised_amount >= so_doc.amount:
                        messages += f"Poc Percentage Completed Sales Order - <b>{doc.sales_order}</b>"
                        frappe.throw(messages)
 
                    frappe.log_error(title="cpm",message=cpm)
                    frappe.log_error(title="credit_acount",message=cpm.revenue_recognition_credit_acount)
                    frappe.log_error(title="debit_acount",message=cpm.revenue_recognition_debit_acount)
                    credit_acount = cpm.revenue_recognition_credit_acount
                    debit_acount = cpm.revenue_recognition_debit_acount
                    
                    if not credit_acount and not debit_acount:
                        credit_acount = frappe.get_value("Associated Offering Account", {"parent":cpm.offering,"lob": frappe.get_doc("Sales Order Item", 
                                        cpm.sales_order_item).line_of_business, "mandate": frappe.get_doc("Sales Order Item", cpm.sales_order_item).mandate}, "credit_account") or \
                                        frappe.get_value("Associated Offering Account", 
                                        {"parent":cpm.offering, "lob": frappe.get_doc("Sales Order Item", cpm.sales_order_item).line_of_business}, "credit_account")
                            
                        debit_acount =  frappe.get_value("Associated Offering Account", {"parent":cpm.offering,"lob": frappe.get_doc("Sales Order Item", cpm.sales_order_item).line_of_business, 
                                        "mandate": frappe.get_doc("Sales Order Item", cpm.sales_order_item).mandate}, "debit_account") or \
                                        frappe.get_value("Associated Offering Account", 
                                        {"parent":cpm.offering, "lob": frappe.get_doc("Sales Order Item", cpm.sales_order_item).line_of_business}, "debit_account")
                                        
                        #credit a/c Debit A/c Validations
                        if not credit_acount or not debit_acount:
                            off_link = f'<a href="/app/offering/{row.offering}">{row.offering}</a>'
                            messages += f"Select Accounting Details for Offering <b>{off_link}</b>"
                            frappe.log_error(2)
                            frappe.throw(messages)
                            
                    existing_journal = frappe.db.exists("Journal Entry", {"sales_order": cpm.sales_order, "sales_order_item": cpm.sales_order_item, "docstatus": 0, "is_from_report": 1})
                    
                    #Existing Journal Entry Validation
                    if existing_journal:
                        jv_link = f'<a href="/app/journal-entry/{existing_journal}">{existing_journal}</a>'
                        messages += f"Already created a journal entry for the sales order {cpm.name} <br> {jv_link}"
                        
                        frappe.throw(messages)

        
                                