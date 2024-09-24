// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Offering', {
	onload: function(frm) {
		frm.fields_dict.accounting_details.grid.get_field('debit_account').get_query = function (frm, cdt, cdn) {
			return {
				filters: { "is_group": 0,}
				};
			}
		frm.fields_dict.accounting_details.grid.get_field('credit_account').get_query = function (frm, cdt, cdn) {
			return {
				filters: { "is_group": 0,}
			};
		}
	}
});
