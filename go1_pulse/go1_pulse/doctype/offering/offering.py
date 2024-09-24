# Copyright (c) 2023, Tridots Team and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Offering(Document):
	def on_trash(self):
		frappe.db.delete('Associated Common Project', {'parent': self.name})
		frappe.db.delete('Associated Offering Account', {'parent': self.name})