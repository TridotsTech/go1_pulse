import frappe
import os
from frappe.utils import now, getdate
from frappe import _
from frappe.model.utils.user_settings import get_user_settings
import json
from datetime import datetime, timedelta
from go1_pulse.queries import get_filtered_users_query,fetch_projects_query,get_employee_query,get_data_query

@frappe.whitelist()
def get_project_activity_types(doctype, txt, searchfield, start, page_len, filters):
	condition=''
	if txt:
		condition += " AND activity_type like '%"+txt+"%'"
	query = """ SELECT activity_type as name FROM `tabLOB Activity Type` LA
				INNER JOIN `tabLine of Business` LB ON LA.parent = LB.name
				INNER JOIN `tabProject` P ON LB.name = P.lob
				WHERE P.name='{project}' {condition}""".format(project=filters.get("project"),condition=condition)
	return frappe.db.sql(query)
@frappe.whitelist()
def get_filtered_users(doctype, txt, searchfield, start, page_len, filters):
	condition=''
	if txt:
		frappe.log_error(title="text",message=txt)
		condition += " AND (name like '%{}%' OR full_name like '%{}%')".format(txt, txt)
	return get_filtered_users_query(condition)


@frappe.whitelist()
def timesheet_update(doc,method):
	if doc.time_logs:
		for x in doc.time_logs:
			if x.hours and frappe.session.user == doc.owner:
				x.actual_hrs = x.hours
	if doc.parent_project:
		pr_mgr = frappe.db.get_value("Project",doc.parent_project,"project_manager")
		if pr_mgr:
			doc.project_manager = pr_mgr

def get_permitted_records(user):
	if not user: user=frappe.session.user
	user_roles = frappe.get_roles(user)
	if "System Manager" in user_roles or "Employee" in user_roles:
		return None
	if "Projects Manager" in user_roles:
		return f"(`tabTimesheet`.project_manager = '{user}')"

# Checks if employee was present during this time.
@frappe.whitelist()
def check_absent(date, employee):
	attendance = frappe.db.get_all("Attendance", filters={"employee": employee, "attendance_date":date}, fields=["status"])
	if attendance and attendance[0].status == "Absent":
		return True
	return False

# Filter for projects in Timesheet Tool
@frappe.whitelist()
def get_projects(doctype, txt, searchfield, start, page_len, filters, role=[]):
	user = filters.get("user")
	condition = ""
	if txt:
		condition += " AND P.project_name like '%"+txt+"%'"
	roles = frappe.get_roles(user)
	if not role or len(role) == 1:
		if "Reporting Manager" in roles and not "System Manager" in roles :
			reporting_manager = frappe.db.get_value("Employee", {"user_id":filters.get("user")}, ["employee"])
			condition += f" AND E.reports_to = '{reporting_manager}'"
		if "Projects Manager" in roles and not "System Manager" in roles:
			condition += f" AND P.project_manager ='{filters.get('user')}'"
	else:
		if "Projects Manager" in roles and not "System Manager" in roles:
			condition += f" AND P.project_manager ='{filters.get('user')}'"

	return fetch_projects_query(condition)



# Filter for employee in Timesheet Tool
@frappe.whitelist()
def get_employee(txt=None, filters=None, role=""):
	user = filters.get("user")	
	condition = ""
	if txt:
		condition += " AND E.employee_name like '%"+txt+"%'"
	roles = frappe.get_roles(user)
	if filters.get("projects"):
		projects = ""
		for project in filters.get("projects"):
			projects += f"'{project}',"
		projects = projects[:-1]
		condition = f" AND TSD.project IN ({projects})"
	if not role or len(role) == 1:
		if "Reporting Manager" in roles and not "System Manager" in roles:
			reporting_manager = frappe.db.get_value("Employee", {"user_id":filters.get("user")}, ["employee"])
			condition += f" AND E.reports_to = '{reporting_manager}'"
		if "Projects Manager" in roles and not "System Manager" in roles:
			condition += f" AND P.project_manager ='{filters.get('user')}'"
	else:
		if "Projects Manager" in roles and not "System Manager" in roles:
			condition += f" AND P.project_manager ='{filters.get('user')}'"

	return get_employee_query(condition)

@frappe.whitelist()
def get_employee(doctype, txt, searchfield, start, page_len, filters, role=""):
	condition = ""
	if txt:
		condition += " AND E.employee_name like '%"+txt+"%'"
	if filters.get("projects"):
		projects = ""
		for project in filters.get("projects"):
			projects += f"'{project}',"
		projects = projects[:-1]
		condition = f" AND TSD.project IN ({projects})"
	if not role or len(role) == 1:
		if "Reporting Manager" in frappe.get_roles(filters.get("user")) and not "System Manager" in frappe.get_roles(filters.get("user")):
			reporting_manager = frappe.db.get_value("Employee", {"user_id":filters.get("user")}, ["employee"])
			condition += f" AND E.reports_to = '{reporting_manager}'"
		if "Projects Manager" in frappe.get_roles(filters.get("user")) and not "System Manager" in frappe.get_roles(filters.get("user")):
			condition += f" AND P.project_manager ='{filters.get('user')}'"
	else:
		if "Projects Manager" in frappe.get_roles(filters.get("user")) and not "System Manager" in frappe.get_roles(filters.get("user")):
			condition += f" AND P.project_manager ='{filters.get('user')}'"
	query = f"""SELECT TS.employee, E.employee_name FROM `tabTimesheet` TS 
			INNER JOIN `tabTimesheet Detail` TSD ON TSD.parent = TS.name
			INNER JOIN `tabEmployee` E ON E.name = TS.employee
			INNER JOIN `tabProject` P ON P.name = TSD.project
			WHERE TS.employee IS NOT NULL
			{condition}
			GROUP BY TS.employee
			"""
	return frappe.db.sql(query)


# Query Output for Timesheet Tool child table.

@frappe.whitelist()
def get_data(projects="", employees="", from_date="", to_date="", role=""):
	roles = frappe.get_roles(frappe.session.user)
	condition =""
	if projects != '[]':
		projects = projects[1:-1]
		condition += f" AND TSD.project IN ({projects})"
	if employees != '[]':
		employees = employees[1:-1]
		condition += f" AND TS.employee IN ({employees})"
	if from_date:
		condition += f" AND TS.log_date >= '{from_date}'"
	if to_date:
		condition += f" AND TS.log_date <= '{to_date}'"


	# Can have multiple roles based on user role profile.
	if not role:
		if "Reporting Manager" in roles and not "System Manager" in roles:
			reporting_manager = frappe.db.get_value("Employee", {"user_id":frappe.session.user}, ["employee"])
			condition += f" AND TSD.approval_status = 'RM Pending'"
			condition += f" AND E.reports_to = '{reporting_manager}'"
		if "Projects Manager" in roles and not "System Manager" in roles:
			condition += f" AND TSD.approval_status = 'PM Pending'"
			condition += f" AND P.project_manager ='{frappe.session.user}'"
		if any(role in roles for role in ("HR User", "HR Manager"))  and not "System Manager" in roles:
			condition += f" AND TSD.approval_status = 'HR Pending'"


	# Checks with assigned role value on clicking custom buttons.
	if role and not "System Manager" in roles:
		if "Reporting Manager" in role:
			reporting_manager = frappe.db.get_value("Employee", {"user_id":frappe.session.user}, ["employee"])
			condition += f" AND TSD.approval_status = 'RM Pending'"
			condition += f" AND E.reports_to = '{reporting_manager}'"
		if "Projects Manager" in role:
			condition += f" AND TSD.approval_status = 'PM Pending'"
			condition += f" AND P.project_manager ='{frappe.session.user}'"
		if "HR" in role:
			condition += f" AND TSD.approval_status = 'HR Pending'"


	# For Admin to view all timesheets irrespective of reports_to and project_manager.
	if role and "System Manager" in roles:
		if "Reporting Manager" in role:
			condition += f" AND TSD.approval_status = 'RM Pending'"
		if "Projects Manager" in role:
			condition += f" AND TSD.approval_status = 'PM Pending'"
		if "HR" in role:
			condition += f" AND TSD.approval_status = 'HR Pending'"

	
	query = f"""
			SELECT TS.employee_name, TSD.project, TSD.customer, TSD.activity_type, TSD.description, TSD.hours, TS.log_date, TSD.name, TSD.approval_status
			FROM `tabTimesheet` TS
			INNER JOIN `tabTimesheet Detail` TSD ON TSD.parent = TS.name
			INNER JOIN `tabEmployee` E ON E.name = TS.employee
			INNER JOIN `tabProject` P ON P.name = TSD.project
			WHERE TS.employee IS NOT NULL
			AND TS.docstatus = 0
			AND TS.sent_for_approval = 1
			AND TSD.approval_status NOT IN ("Employee Pending", "Approved")
			{condition}
			ORDER BY TS.employee_name asc, TSD.project asc, TSD.customer asc, TSD.activity_type asc, TS.log_date asc
			"""

	value=frappe.db.sql(query)

	return value

# Update approval status in employee Timesheet Detail
@frappe.whitelist()
def update_timesheet(changed_data, approved_data, role=""):
	json_changed_data = json.loads(changed_data)
	json_approved_data = json.loads(approved_data)
	roles = frappe.get_roles(frappe.session.user)
	
	count = check_multiple_roles()

	if not role and ("System Manager" in roles or "System Manager" not in roles):
		if len(count) > 1:
			frappe.throw("Please choose a role to act as.")

		else:
			for row in json_changed_data:
				status = "Employee Pending"
				if "Reporting Manager" in roles:
					status = "PM Pending"
				if "Projects Manager" in roles:
					status = "HR Pending"
				if any(role in roles for role in ("HR User", "HR Manager")):
					status = "Approved"
				update_timesheet_details(row=row,status=status)
			
			for row in json_approved_data:
				status = ""
				if "Reporting Manager" in roles:
					status = "PM Pending"
				if "Projects Manager" in roles:
					status = "Approved"
				if any(role in roles for role in ("HR User", "HR Manager")):
					status = "Approved"
				update_timesheet_details(row=row,status=status)
				# frappe.db.set_value("Timesheet Detail", row["tsd_name"], {"hours": row["hours"], "approval_status": status})
			check_for_submit(json_changed_data, json_approved_data)
	if role:
		check_role_based_json(json_changed_data=json_changed_data,role=role,json_approved_data=json_approved_data)
		
def check_role_based_json(json_changed_data=None,role=None,json_approved_data=None):
	for row in json_changed_data:
		status = "Employee Pending"
		if "Reporting Manager" in role:
			status = "PM Pending"
		if "Projects Manager" in role:
			status = "HR Pending"
		if "HR" in role:
			status = "Approved"
		update_timesheet_details(row=row,status=status)
  
	for row in json_approved_data:
		status = "Employee Pending"
		if "Reporting Manager" in role:
			status = "PM Pending"
		if "Projects Manager" in role:
			status = "Approved"
		if "HR" in role:
			status = "Approved"
		update_timesheet_details(row=row,status=status)
			
	check_for_submit(json_changed_data, json_approved_data)

def update_timesheet_details(row, status):	
	docs = frappe.db.get_all("Timesheet Detail", filters={"name": row["tsd_name"]}, fields=["parent"])
	frappe.log_error(title="docs",message=docs)
	if docs:
		doc = frappe.get_doc("Timesheet", docs[0].parent)
		for tsd in doc.time_logs:
			if tsd.name == row["tsd_name"]:
				tsd.hours = float(row["hours"])
				tsd.approval_status = status
		doc.save(ignore_permissions=True)


# Changes status back to null on ejection of timesheets.
@frappe.whitelist()
def reject_timesheet(rejected_data, role=""):
	count = check_multiple_roles()
	if not role:
		if len(count) > 1:
			frappe.throw("Please choose a role to act as.")
	json_rejected_data = json.loads(rejected_data)
	for row in json_rejected_data:
		status = "Employee Pending"
		docs = frappe.db.get_all("Timesheet Detail", filters={"name": row["tsd_name"]}, fields=["parent"])
		if docs:
			doc = frappe.get_doc("Timesheet", docs[0].parent)
			for TSD in doc.time_logs:
				if TSD.name == row["tsd_name"]:
					TSD.hours = float(row["hours"])
					TSD.approval_status = status
			doc.save(ignore_permissions=True)

# Auto submit timesheet when all child table values are approved.
def check_for_submit(changed_data, approved_data):
	data = []
	check_dates = []
	for row in changed_data:
		data.append(row)
	for row in approved_data:
		data.append(row)
	for row in data:
		check_dates.append(row["log_date"])
	timesheets = frappe.db.get_all("Timesheet", filters={"log_date": ["in", check_dates], "docstatus": 0}, fields=["name", "total_hours"])
	frappe.log_error(title="timesheet",message=timesheets)
	for timesheet in timesheets:
		doc = frappe.db.get_all("Timesheet Detail", filters={"parent": timesheet.name}, fields=["approval_status", "hours"])
		if doc:
			timesheet_to_update = frappe.get_doc("Timesheet", timesheet.name)
			flag = False
			count = 0
			for row in doc:
				if row["approval_status"] == "Approved":
					count += 1
			if count == len(doc):
				flag = True
			if flag == True:
				total_hours = 0
				for row in doc:
					total_hours += row["hours"]
				if timesheet["total_hours"] != total_hours:
					timesheet_to_update.total_hours = total_hours
				timesheet_to_update.docstatus = 1
				timesheet_to_update.save(ignore_permissions=True)

# Sets user settings for child table fields in timesheet for new user.
@frappe.whitelist(allow_guest=True)
def update_timesheet_fields(login_manager):
	if frappe.session.user!="Guest":
		user_settings = get_user_settings("Timesheet")

		if not user_settings or user_settings == "{}":
			path = frappe.get_module_path("go1_pulse")
			timesheet_json = os.path.join(path, "time_sheet_fields.json")
			with open(timesheet_json) as jsonFile:
				jsonObject = json.load(jsonFile)
				jsonObject["updated_on"] = now()
				from frappe.model.utils.user_settings import save
				save(doctype="Timesheet",user_settings=json.dumps(jsonObject))



@frappe.whitelist()
def update_all_user_fields():
	if frappe.session.user!="Guest":
		users = frappe.db.get_all("User")
		for x in users:
			path = frappe.get_module_path("go1_pulse")
			timesheet_json = os.path.join(path, "time_sheet_fields.json")
			with open(timesheet_json) as jsonFile:
				jsonObject = json.load(jsonFile)
				jsonObject["updated_on"] = now()

				frappe.cache().hset("_user_settings", f"Timesheet::{x.name}", json.dumps(jsonObject))

# Auto send email to reports to manager on sending timesheets for approval.
@frappe.whitelist()
def send_mail(employee, name):
	reporting_manager = frappe.db.get_value("Employee", employee, "reports_to")
	user_id = frappe.db.get_value("Employee", reporting_manager, "user_id")

# Gives Reporting Manager role when reports_to is mapped in employee. If role is not available, creates a new Reorting Manager Role.
@frappe.whitelist()
def update_role(doc, method):
	reporting_user = frappe.db.get_value("Employee", doc.reports_to, "user_id")
	if reporting_user:
		role = frappe.db.get_all('Has Role',fields=['*'],filters={'parent':reporting_user,'role':'Reporting Manager'})
		if not role:
			if not frappe.db.exists("Role", "Reporting Manager"):
				doc = frappe.new_doc("Role")
				doc.name = "Reporting Manager"
				doc.role_name = "Reporting Manager"
				doc.desk_access = 1
				doc.insert(ignore_permissions = True)
			frappe.get_doc({
				"doctype": "Has Role",
				"name": reporting_user + "Reporting_Manager",
				"parent": reporting_user,
				"parentfield": "roles",
				"parenttype": "User",
				"role": "Reporting Manager"
				}).insert(ignore_permissions = True)


@frappe.whitelist()
def bulk_update_role():
	employees = frappe.db.get_all("Employee",filters={"status":"Active"},fields=['reports_to','name'])
	for emp in employees:
		reporting_user = frappe.db.get_value("Employee", emp.reports_to, "user_id")
		role = frappe.db.get_all('Has Role',fields=['*'],filters={'parent':reporting_user,'role':'Reporting Manager'})
		if not role:
			if not frappe.db.exists("Role", "Reporting Manager"):
				doc = frappe.new_doc("Role")
				doc.name = "Reporting Manager"
				doc.role_name = "Reporting Manager"
				doc.desk_access = 1
				doc.insert(ignore_permissions = True)
			frappe.get_doc({
				"doctype": "Has Role",
				"name": reporting_user + "Reporting_Manager",
				"parent": reporting_user,
				"parentfield": "roles",
				"parenttype": "User",
				"role": "Reporting Manager"
				}).insert(ignore_permissions = True)

# Checks if timesheets are available on the day absent is being marked and cancels it.
@frappe.whitelist()
def check_attendance(doc, method):
	employee = doc.employee
	date = doc.attendance_date
	status = doc.status
	if status == "Absent":
		timesheet = frappe.db.get_value("Timesheet",{'employee':employee, 'log_date':date}, "name")
		if timesheet:
			doc = frappe.get_doc("Timesheet", timesheet)
			doc.docstatus = 2
			doc.save(ignore_permissions=True)


# Checks if the user has multiple roles and sends a list of roles present in a default set.
@frappe.whitelist()
def check_multiple_roles():
	roles = frappe.get_roles(frappe.session.user)
	checks = ["Projects Manager", "Reporting Manager", "HR User", "HR Manager", "System Manager"]
	count = []
	for check in checks:
		if check in roles:
			count.append(check)
	return count


@frappe.whitelist()
def get_date(date,hours):
	value = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
	updated_value = value + timedelta(hours=float(hours))
	return updated_value.strftime("%Y-%m-%d %H:%M:%S")