// Copyright (c) 2023, Tridots Team and contributors
// For license information, please see license.txt

var data = []
var role = ""
frappe.ui.form.on('Timesheet Tool', {
	onload: function(frm){
		role = ""
		// Creates nested buttons on detection of overlapping roles.
		$(".section-head").last().text("")
		frappe.call({
			method: "go1_pulse.timesheet.check_multiple_roles",
		}).then(value => {
			var group_name = "Act As"
			const roles = value.message;
			console.log(roles)
			if (roles.length > 1){
				if (roles.includes("Projects Manager")){
					frm.add_custom_button(__('Project Manager'), function(){
						$(".section-head").last().text("Acting as Projects Manager")
						role = "Projects Manager"
						get_details(frm, role)
					}, __(group_name));
				}
				if (roles.includes("Reporting Manager")){
					frm.add_custom_button(__('Reporting Manager'), function(){
						$(".section-head").last().text("Acting as Reporting Manager")
						role = "Reporting Manager"
						get_details(frm, role)
					}, __(group_name));
				}
				if (roles.includes("HR User") || roles.includes("HR Manager")){
					frm.add_custom_button(__('HR'), function(){
						$(".section-head").last().text("Acting as HR")
						role = "HR"
						get_details(frm, role)
					}, __(group_name));
				}
			}
			if (roles.includes("System Manager") || roles.length == 1){
				get_details(frm)
			}
			frm.add_custom_button(__('Reject'), function(){
				if (!role && roles.length != 1){
					frappe.throw(__("Please choose a role to act as."))
				}
				reject_details(frm, role)
			});
			frm.add_custom_button(__('Approve'), function(){
				if (!role && roles.length != 1){frappe.throw(__("Please choose a role to act as."))}
				update_details(frm, role)
			});
			$('[data-label="Reject"]').removeClass("btn-default").addClass("btn-danger");
            $('[data-label="Approve"]:first').removeClass("btn-default").addClass("btn-primary");
		});
	},
	// Sets initial link queries and hides buttons.
	refresh: function(frm) {
		$('[data-label="Approve"]:first').addClass("btn-primary")
		$('[data-label="Reject"]').addClass("btn-danger")
		if(frappe.session.user!="Administrator" && !has_common(frappe.user_roles, ['System Manager'])){
			$('head').append('<style>[id="page-Timesheet Tool"] div[data-fieldname="timesheet"] .grid-row .col:last-child{display:none !important;}</style>')
		}
		$('head').append('<style>[id="page-Timesheet Tool"] button[class="btn btn-xs btn-secondary grid-add-row"]{display:none !important;}</style>')
		$('head').append('<style>[id="page-Timesheet Tool"] button[class="btn btn-xs btn-danger grid-remove-rows"]{display:none !important;}</style>')
		$('head').append('<style>[id="page-Timesheet Tool"] button[data-label="Save"]{display:none !important;}</style>')
		$('head').append('<style>[id="page-Timesheet Tool"] button[data-original-title="Menu"]{display:none !important;}</style>')
		frm.set_query("projects", function(){
			return {
				"query":"go1_pulse.timesheet.get_projects",
				"filters": {
					"user":frappe.session.user
				}
			}
		});
		frm.set_query("employees", function() {
			var projects = []
			for (var row of frm.doc.projects) {
				projects.push(row.projects)
			};
			return {
				"query":"go1_pulse.timesheet.get_employee",
				"filters": {
					"projects":projects,
					"user":frappe.session.user
				}
			}
		})
	},
	// Button to get data.
	get_details: function(frm){
		get_details(frm)
	}
});

function get_details(frm, role=""){

	frm.clear_table("timesheet")
	var projects = []
	var employees = []
	data = []

	for (var row of frm.doc.projects) {
		projects.push(row.projects)
	};

	for (var row of frm.doc.employees) {
		employees.push(row.employees)
	};
	
	frappe.call({
		method: "go1_pulse.timesheet.get_data",
		args: {
			"projects": projects,
			"employees": employees,
			"from_date": frm.doc.from_date,
			"to_date": frm.doc.to_date,
			"role": role
		},
		callback: function(r) {
			for (var row of r.message) {
				var child = frm.add_child("timesheet")
				child.employee = row[0]
				child.project = row[1]
				child.customer = row[2]
				child.activity = row[3]
				child.description = row[4]
				child.hours = row[5]
				child.log_date = row[6]	
				child.tsd_name = row[7]
				child.status = row[8]
				data.push({"employee":row[0],"project":row[1],"customer":row[2],"activity":row[3],"description":row[4],"hours":row[5],"log_date":row[6],"tsd_name":row[7], "status":row[8]})
			}
			frm.refresh_field("timesheet")
		}
	})
}


function update_details(frm, role="") {
	var validate = true
	for (var row of frm.get_field("timesheet").grid.grid_rows){
		if (row.doc.__checked){
			validate = false
			break
		}
	}
	if (validate){
		frappe.throw(__("No timesheets are selected!"))
	}else{
		frappe.confirm(
			__("Are you sure you want to approve the selected timesheets?"),
			function() {
				var new_data = []
				for (var row of frm.get_field("timesheet").grid.grid_rows) {
					new_data.push(row.doc)
				}
				console.log(new_data)
				var changed_data = []
				var approved_data = []
				for (let i=0;i<new_data.length;i++){
					if (new_data[i].hours == 0 && new_data[i].__checked == 1){
						frappe.throw("Hours cannot be 0.")
					}
					if (new_data[i].hours != data[i].hours && new_data[i].__checked == 1){
						changed_data.push(new_data[i])
					}
					else if (new_data[i].hours == data[i].hours && new_data[i].__checked == 1){
						approved_data.push(new_data[i])
					}
				}
				console.log("changed_data",changed_data)
				console.log("approved_Data",approved_data)
				console.log("role",role)
				frappe.call({
					method: "go1_pulse.timesheet.update_timesheet",
					args:{
						"changed_data": changed_data,
						"approved_data": approved_data,
						"role": role
					}
				})
				data = []
				frm.reload_doc()
			},
			function() {
				$(this).hide()
			}
		)
	}
}

function reject_details(frm, role="") {
	var validate = true
	for (var row of frm.get_field("timesheet").grid.grid_rows){
		if (row.doc.__checked){
			validate = false
			break
		}
	}
	if (validate){
		frappe.throw(__("No timesheets are selected!"))
	}else{
		frappe.confirm(
			__("Are you sure you want to reject the selected timesheets?"),
			function() {
				var new_data = []
				for (var row of frm.get_field("timesheet").grid.grid_rows) {
					new_data.push(row.doc)
				}
				var rejected_data = []
				for (let i=0;i<new_data.length;i++){
					if (new_data[i].__checked == 1){
						if (new_data[i].hours == 0){
							frappe.throw("Hours cannot be 0.")
						}else{
							rejected_data.push(new_data[i])
						}
					}
				}
				frappe.call({
					method: "go1_pulse.timesheet.reject_timesheet",
					args:{
						"rejected_data": rejected_data,
						"role": role
					}
				})
				data = []
				frm.reload_doc()
			},
			function() {
				$(this).hide()
			}
		)
	}
}