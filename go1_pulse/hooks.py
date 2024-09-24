app_name = "go1_pulse"
app_title = "Go1 Pulse"
app_publisher = "TridotsTech"
app_description = "Go1 Pulse"
app_email = "info@tridotstech.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/go1_pulse/css/go1_pulse.css"
# app_include_js = "/assets/go1_pulse/js/go1_pulse.js"

# include js, css files in header of web template
# web_include_css = "/assets/go1_pulse/css/go1_pulse.css"
# web_include_js = "/assets/go1_pulse/js/go1_pulse.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "go1_pulse/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

doctype_js = {
        "Project" : "/public/js/project.js",
        "Timesheet" : "/public/js/time_sheet.js",
        "Sales Order" : "/public/js/sales_order.js",
        }

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

permission_query_conditions = {
        "Timesheet": "go1_pulse.timesheet.get_permitted_records"
}

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "go1_pulse.utils.jinja_methods",
# 	"filters": "go1_pulse.utils.jinja_filters"
# }

# Installation
# ------------


# before_install = "go1_pulse.install.before_install"
# after_install = "go1_pulse.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "go1_pulse.uninstall.before_uninstall"
# after_uninstall = "go1_pulse.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "go1_pulse.utils.before_app_install"
# after_app_install = "go1_pulse.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "go1_pulse.utils.before_app_uninstall"
# after_app_uninstall = "go1_pulse.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "go1_pulse.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }
override_doctype_class = {
    "Sales Invoice": "go1_pulse.override_class_method.SalesInvoiceOR",
}
# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }


doc_events = {
        "Sales Order": {
                "on_submit": [  "go1_pulse.api.create_common_project" ],
                "on_cancel": [  "go1_pulse.api.check_common_project_mapper_status" ],
                "validate": [
                                "go1_pulse.api.check_billing_percentage", 
                                "go1_pulse.api.gen_billing_methods", 
                                "go1_pulse.api.validate_service_date", 
                                "go1_pulse.api.check_project_budget"
                        ],
                                
                "on_update_after_submit":  ["go1_pulse.api.update_common_project",
                                            "go1_pulse.api.update_common_project_mapper",
                                            "go1_pulse.api.check_billing_percentage",
                        ],
                "before_update_after_submit":[
                                        "go1_pulse.api.update_so_tag",
                                        "go1_pulse.api.generic_so_update_validation",
                                        "go1_pulse.api.so_update_approval",
                        ]
        },
        "Common Project Mapper": {
                "before_save": "go1_pulse.api.make_journal_entry",
        },
        "Timesheet": {
                "on_update": "go1_pulse.timesheet.timesheet_update",
        },
        "Project":{
          "on_update":"go1_pulse.api.update_project_users",
        },
        "Sales Invoice": {
                "on_submit": ["go1_pulse.api.update_billing_status",
                              "go1_pulse.api.update_sales_return",
                                "go1_pulse.api.update_is_billed_in_cpm"],
                "on_cancel": "go1_pulse.api.update_billing_status"
        },
     
        "Employee": {
            "on_update": "go1_pulse.timesheet.update_role",
        },
        "Attendance": {
            "on_submit": "go1_pulse.timesheet.check_attendance",
        },
        "Journal Entry": {
            "autoname":"go1_pulse.api.update_jv_naming_series",
            "on_submit": ["go1_pulse.api.update_employee_expense","go1_pulse.api.update_poc_revenue"],
            "on_cancel": ["go1_pulse.api.update_employee_expense","go1_pulse.api.update_poc_revenue"]
            
        },
        "Workflow Action" : {
            "validate" : "go1_pulse.api.add_user"
        },
}
after_migrate=[
	"go1_pulse.api.create_new_custom_fields"
        # "revenue.update_custom_fields.update_asset_fields"
]
# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"go1_pulse.tasks.all"
# 	],
# 	"daily": [
# 		"go1_pulse.tasks.daily"
# 	],
# 	"hourly": [
# 		"go1_pulse.tasks.hourly"
# 	],
# 	"weekly": [
# 		"go1_pulse.tasks.weekly"
# 	],
# 	"monthly": [
# 		"go1_pulse.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "go1_pulse.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "go1_pulse.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "go1_pulse.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["go1_pulse.utils.before_request"]
# after_request = ["go1_pulse.utils.after_request"]

# Job Events
# ----------
# before_job = ["go1_pulse.utils.before_job"]
# after_job = ["go1_pulse.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"go1_pulse.auth.validate"
# ]
