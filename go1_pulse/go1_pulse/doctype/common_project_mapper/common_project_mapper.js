// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt

frappe.ui.form.on('Common Project Mapper', {
	date_of_completion: function (frm) {
		if (moment(frm.doc.date_of_completion) > moment(frappe.datetime.get_today())) {
			frm.set_value("date_of_completion", frappe.datetime.get_today())
			frappe.msgprint("Future dates are not allowed.")
		}
	},

	project: function(frm){
	    if(frm.doc.project){
            frappe.db.get_value("Project", frm.doc.project, ["customer", "offering"],
				(res)=>{
					if(res.customer){
						frm.set_value("customer", res.customer);   
					}
					if(res.offering){
						frm.set_value("offering", res.offering);
					}
            	});	        
	    }
	},

	onload: function(frm){
		let off_classification = ["Recurring Revenue", "Perpertual License", "Completed Contract", "Fixed Price - POC", "Percentage of Completion"];
		if(off_classification.includes(frm.doc.offering_classification)){
			frm.get_field("activities_status").grid.cannot_add_rows = true;
			frm.refresh_field("activities_status");
		}
        frm.set_query("project", ()=> {
				if(frm.doc.customer){
					return {
						filters: {
							"customer": frm.doc.customer
								}
						};
					}
				else{
					return {
						filters: {
							"cost_center": frm.doc.cost_center
							}
						};
					}
		});
		
		
		frm.set_query("revenue_recognition_debit_acount", () => {
			return {
				filters: {
					"is_group": 0, 
					"company": frappe.defaults.get_global_default("company"), 
					"account_currency": "INR" 
				}
			};
			
		});
		frm.set_query("revenue_recognition_credit_acount", () => {
			return {
				filters: {
					"is_group": 0, 
					"company": frappe.defaults.get_global_default("company")
				}
			};

		});
		frm.set_query( "end_customer", function(frm, cdt, cdn){
			let row= locals[cdt][cdn];
			let c_list=[];
			frappe.call({
				method:"go1_pulse.api.get_customer_list",
				args: {customer: cur_frm.doc.customer || ""},
				async: false,
				callback: function(res){
					c_list = res.message;
				}
			});
			if(c_list){
				return { filters:{"name":["in",c_list ] } };
			}
		});
    },



	refresh: function (frm) {
		if (frm.doc.offering == "Hourly Rate") {
			frm.add_custom_button(__("Fetch Timesheet"), function () {
				let d = new frappe.ui.Dialog({
					title: __("Fetch Timesheet"),
					fields: [
						{
							"label": __("From Date"),
							"fieldname": "from_date",
							"fieldtype": "Date",
							"reqd": 1,
						},
						{
							"label": __("To Date"),
							"fieldname": "to_date",
							"fieldtype": "Date",
							"reqd": 1,
						},
						{
							"label": __("Project"),
							"fieldname": "project",
							"fieldtype": "Link",
							"options": "Project",
							"reqd": 1,
							"default": frm.doc.project
						},
					],
					primary_action: function () {
						const data = d.get_values();
						
						frappe.call({
							method: "go1_pulse.go1_pulse.doctype.common_project_mapper.common_project_mapper.get_timesheet_billing_hours",
							freeze: true,
							freeze_message: __("Fetching Timesheet Billable Hours"),
							args: {
								project: data.project,
								f_date : data.from_date,
								t_date : data.to_date,
							},
							callback: function(res){
								let values = {"from_date": data.from_date, "to_date": data.to_date,  "total_hours_or_units": res.message}
								let c_flag = 0
								if(res.message){
									frm.doc.hours_or_units.forEach(element => {
										if (element.from_date == values.from_date && element.to_date == values.to_date) {
											c_flag=1;
										}
										else{
											console.log(moment(data.date[0]), (moment(element.date)))
											if (moment(data.from_date).isBefore(moment(element.end_date))) {
												frappe.throw(`Selected date range ${data.from_date} - ${data.to_date} already exists`)
											}
										}
									});
									if (!c_flag) {
										frm.add_child("hours_or_units", values)
										frm.refresh_field("hours_or_units")
									}
									else{
										frappe.throw(`Selected date range <b>${data.from_date} - ${data.to_date}</b> already exists`)
									}
								}
								else{
									frappe.throw("Records Not Found")
								}
							}
							});
						d.hide();
					},
					primary_action_label: __("Get Timesheets")
				});
				d.show();
			});
		}
		

		if (frm.doc.offering_classification == "Recurring Revenue") {
			var msg=""
			frm.add_custom_button(__("Test Revenue Recognition"), function () {
				let d = new frappe.ui.Dialog({
					title: __("Test Revenue Recognition"),
					fields: [
						{
							"label": __("Date"),
							"fieldname": "date",
							"fieldtype": "Date",
							"reqd": 1,
						},
					],
					primary_action: function () {
						const data = d.get_values();

						frappe.call({
							method: "go1_pulse.api.make_equal_revenue",
							freeze: true,
							freeze_message: __("Creating Journal"),
							args: {
								c_date: data.date,
								so: frm.doc.sales_order
							}
						});
						d.hide();
					},
					primary_action_label: __("Create")
				});
				d.show();
			});
		}


		if (frm.doc.offering_classification == "Percentage of Completion"){
			frm.add_custom_button(__("Make Journal"), function () {
				let d = new frappe.ui.Dialog({
					title: __("Make Journal"),
					fields: [
						{
							"label": __("Posting Date"),
							"fieldname": "posting_date",
							"fieldtype": "Date",
							"reqd": 1,
						},
					],
					primary_action: function () {
						const data = d.get_values();

						frappe.call({
							method: "go1_pulse.go1_pulse.doctype.common_project_mapper.common_project_mapper.make_journal_for_poc",
							args: {
								source : frm.doc.name,
								posting_date: data.posting_date,
								is_from_report:1
							},
							callback:function(r){
								console.log(r.message[0])
								frappe.msgprint(r.message[0])
							}
						});
						d.hide();
					},
					primary_action_label: __("Create Journal")
				});
				d.show();
			});
		}


	},


	
	send_notification: function(){
		frappe.call({
			method: "go1_pulse.api.sendNotification", 
			freeze:true, 
			freeze_message:__("Sending Notification"),
			callback: function (res) {
				if (res) {
					frappe.msgprint(res);
					
				}
			}
		})
	},


	update_status: function(){
		frappe.call({
			freeze:true, 
			method: "go1_pulse.api.update_status", 
			callback: function(res){
				frappe.msgprint("Finished");
			}
	})
	},
	
});

frappe.ui.form.on('Associated Activity', {

	completed : function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if(row.completed){
			frappe.model.set_value(cdt, cdn, "notification_status", 1);
			frappe.call({
				method: "go1_pulse.api.sendNotification",
				args: {
					so: frm.doc.sales_order,
					bm_ref: row.billing_reference
				},
				freeze: true,
				freeze_message: __("Sending Notification"),
				callback: function (res) {
					if(res){
						frappe.run_serially([
							() => frm.save(),
							() => frappe.msgprint(res),
						]);
					}
				}
			})
		}
	},


	before_activities_status_remove: function (frm, cdt, cdn) {
		let hu_data = frm.fields_dict.activities_status.grid.get_selected_children()
		if (hu_data) {
			console.log(hu_data)
			hu_data.forEach((element) => {
				if (element.is_billed) {
					frappe.throw(`Billed row Can't be deleted`)
				}
			})
		}
	},
	
})


frappe.ui.form.on('Common Project Hour Or Unit', {
	before_hours_or_units_remove: function(frm, cdt, cdn){
		let hu_data = frm.fields_dict.hours_or_units.grid.get_selected_children()
		if(hu_data){
			console.log(hu_data)
			hu_data.forEach((element)=>{
				if(element.is_billed){
					frappe.throw(`Billed row Can't be deleted`)			
				}
			})
		}
	},
})
