// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Timesheet Defaulters"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"fieldtype": "Date",
			"label": __("From Date"),
			"default": last_week_date()
		},
		{
			"fieldname": "to_date",
			"fieldtype": "Date",
			"label": __("To Date"),
			"default": today_date()
		},
		{
			"fieldname": "employee",
			"fieldtype": "Link",
			"label": __("Employee"),
			"options": "Employee"
		}
	],
	"after_datatable_render": function(s){
		setTimeout(function(){
			$("[data-label='Download%20Report']").css("display","none")
		}, 1000)
	}
};

function today_date(){
	var date = new Date()
	return `${date.getFullYear()}-${date.getMonth()+1}-${date.getDate()}`
}

function last_week_date(){
	var date = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) 
	return `${date.getFullYear()}-${date.getMonth()+1}-${date.getDate()}`
}
