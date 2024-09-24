
import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from frappe import _

class SalesInvoiceOR(SalesInvoice):
    #override so validation in sales invoice
    def so_dn_required(self):
        """check in manage account if sales order / delivery note required or not."""
        if self.is_return:
            return
        
        fixed_asset = 0
        for item in self.items:
            if item.get('asset') and item.get('is_fixed_asset'):
                fixed_asset = 1
                

        prev_doc_field_map = {
            "Sales Order": ["so_required", "is_pos"],
            "Delivery Note": ["dn_required", "update_stock"],
        }
        for key, value in prev_doc_field_map.items():
            if frappe.db.get_single_value("Selling Settings", value[0]) == "Yes":

                if frappe.get_value("Customer", self.customer, value[0]):
                    continue

                for d in self.get("items"):
                    if d.item_code and not d.get(key.lower().replace(" ", "_")) and not self.get(value[1]) and not fixed_asset:
                        frappe.msgprint(_("{0} is mandatory for Item {1}").format(key, d.item_code), raise_exception=1)


