import frappe
from frappe import _
from frappe.model.document import Document

from lyfe_taxjar.lyfe_taxjar.utils import get_client


class LyfeTaxJarSettings(Document):
	def validate(self):
		if not self.taxjar_calculate_tax and (self.taxjar_create_transactions or self.is_sandbox):
			frappe.throw(
				_(
					"Before enabling <b>Create TaxJar Transaction</b> or <b>Sandbox Mode</b>, "
					"you must first enable <b>Enable Tax Calculation</b>."
				)
			)

	def on_update(self):
		from lyfe_taxjar.lyfe_taxjar.setup import make_custom_fields, add_permissions

		if self.taxjar_calculate_tax or self.taxjar_create_transactions or self.is_sandbox:
			make_custom_fields()
			add_permissions()

	@frappe.whitelist()
	def update_nexus_list(self):
		client = get_client()
		if not client:
			frappe.throw(_("Could not connect to TaxJar. Please check your API key."))

		nexus = client.nexus_regions()
		self.set("nexus", [])
		for address in nexus:
			self.append("nexus", frappe._dict(address))
		self.save()
		frappe.msgprint(_("Nexus list updated successfully."))
