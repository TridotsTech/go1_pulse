// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Profitability Analysis iris"] = {
		"filters": [
			{
				"fieldname": "company",
				"label": __("Company"),
				"fieldtype": "Link",
				"options": "Company",
				"default": frappe.defaults.get_user_default("Company"),
				"reqd": 1
			},
			{
				"fieldname": "based_on",
				"label": __("Based On"),
				"fieldtype": "Select",
				"options": ["Cost Center", "Project", "Mandate"],
				"default": "Cost Center",
				"reqd": 1
			},
			{
				"fieldname": "fiscal_year",
				"label": __("Fiscal Year"),
				"fieldtype": "Link",
				"options": "Fiscal Year",
				"default": frappe.defaults.get_user_default("fiscal_year"),
				"reqd": 1,
				"on_change": function(query_report) {
					var fiscal_year = query_report.get_values().fiscal_year;
					if (!fiscal_year) {
						return;
					}
					frappe.model.with_doc("Fiscal Year", fiscal_year, function(r) {
						var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
						frappe.query_report.set_filter_value({
							from_date: fy.year_start_date,
							to_date: fy.year_end_date
						});
					});
				}
			},
			{
				"fieldname": "from_date",
				"label": __("From Date"),
				"fieldtype": "Date",
				"default": frappe.defaults.get_user_default("year_start_date"),
			},
			{
				"fieldname": "to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.defaults.get_user_default("year_end_date"),
			},
			{
				"fieldname": "show_zero_values",
				"label": __("Show zero values"),
				"fieldtype": "Check"
			}
		],

		"formatter": function(value, row, column, data, default_formatter) {
			if (column.fieldname=="account") {
				value = data.account_name;

				column.link_onclick =
					"frappe.query_reports['Profitability Analysis iris'].open_profit_and_loss_statement(" + JSON.stringify(data) + ")";
				column.is_tree = true;
			}

			value = default_formatter(value, row, column, data);

			if (!data.parent_account && data.based_on != 'project') {
				value = $(`<span>${value}</span>`);
				var $value = $(value).css("font-weight", "bold");
				if (data.warn_if_negative && data[column.fieldname] < 0) {
					$value.addClass("text-danger");
				}
				value = $value.wrap("<p></p>").parent().html();
			}
			return value;
		},
		

		"open_profit_and_loss_statement": function(data) {
			if (!data.account) return;

			frappe.route_options = {
				"company": frappe.query_report.get_filter_value('company'),
				"from_fiscal_year": data.fiscal_year,
				"to_fiscal_year": data.fiscal_year
			};

			if(data.based_on == 'cost_center'){
				frappe.route_options["cost_center"] = data.account
			} else {
				frappe.route_options["project"] = data.account
			}

			frappe.set_route("query-report", "Profit and Loss Statement");
		},
		"tree": true,
		"name_field": "account",
		"parent_field": "parent_account",
		"initial_depth": 3
	}

	
	erpnext.dimension_filters.forEach((dimension) => {
		frappe.query_reports["Profitability Analysis iris"].filters[1].options.push(dimension["document_type"]);
	});

});

