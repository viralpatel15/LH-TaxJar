app_name = "lyfe_taxjar"
app_title = "Lyfe TaxJar"
app_publisher = "Lyfe Hardware"
app_description = "TaxJar integration for Lyfe Hardware"
app_email = "hello@lyfehardware.com"
app_license = "mit"

after_install = "lyfe_taxjar.lyfe_taxjar.setup.after_install"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "lyfe_taxjar",
# 		"logo": "/assets/lyfe_taxjar/logo.png",
# 		"title": "Lyfe TaxJar",
# 		"route": "/lyfe_taxjar",
# 		"has_permission": "lyfe_taxjar.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/lyfe_taxjar/css/lyfe_taxjar.css"
# app_include_js = "/assets/lyfe_taxjar/js/lyfe_taxjar.js"

# include js, css files in header of web template
# web_include_css = "/assets/lyfe_taxjar/css/lyfe_taxjar.css"
# web_include_js = "/assets/lyfe_taxjar/js/lyfe_taxjar.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "lyfe_taxjar/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "lyfe_taxjar/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "lyfe_taxjar.utils.jinja_methods",
# 	"filters": "lyfe_taxjar.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "lyfe_taxjar.install.before_install"
# after_install = "lyfe_taxjar.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "lyfe_taxjar.uninstall.before_uninstall"
# after_uninstall = "lyfe_taxjar.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "lyfe_taxjar.utils.before_app_install"
# after_app_install = "lyfe_taxjar.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "lyfe_taxjar.utils.before_app_uninstall"
# after_app_uninstall = "lyfe_taxjar.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "lyfe_taxjar.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_submit": "lyfe_taxjar.lyfe_taxjar.utils.create_transaction",
		"on_cancel": "lyfe_taxjar.lyfe_taxjar.utils.delete_transaction",
	},
	("Quotation", "Sales Order", "Sales Invoice"): {
		"validate": "lyfe_taxjar.lyfe_taxjar.utils.set_sales_tax",
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"lyfe_taxjar.tasks.all"
# 	],
# 	"daily": [
# 		"lyfe_taxjar.tasks.daily"
# 	],
# 	"hourly": [
# 		"lyfe_taxjar.tasks.hourly"
# 	],
# 	"weekly": [
# 		"lyfe_taxjar.tasks.weekly"
# 	],
# 	"monthly": [
# 		"lyfe_taxjar.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "lyfe_taxjar.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "lyfe_taxjar.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "lyfe_taxjar.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["lyfe_taxjar.utils.before_request"]
# after_request = ["lyfe_taxjar.utils.after_request"]

# Job Events
# ----------
# before_job = ["lyfe_taxjar.utils.before_job"]
# after_job = ["lyfe_taxjar.utils.after_job"]

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
# 	"lyfe_taxjar.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

