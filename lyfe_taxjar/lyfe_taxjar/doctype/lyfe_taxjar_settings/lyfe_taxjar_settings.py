import requests
import taxjar
import taxjar.exceptions

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
		# Nexus regions are account-level data — always use the live API.
		# The TaxJar sandbox does not support the nexus/regions endpoint (returns 500).
		api_key = self.api_key and self.get_password("api_key")
		api_url = taxjar.DEFAULT_API_URL
		if not api_key:
			frappe.throw(_("Please enter your Live API key and save before updating the nexus list."))

		regions = self._fetch_nexus_regions(api_key, api_url)

		self.set("nexus", [])
		for region in regions:
			self.append(
				"nexus",
				{
					"region": region.get("name") or region.get("region", ""),
					"region_code": region.get("region_code", ""),
					"country": region.get("country") or region.get("country_name", ""),
					"country_code": region.get("country_code", ""),
				},
			)
		self.save()
		frappe.msgprint(_("{0} nexus region(s) updated successfully.").format(len(regions)))

	# ── private helpers ──────────────────────────────────────────────────────

	def _get_api_credentials(self):
		if self.is_sandbox:
			api_key = self.sandbox_api_key and self.get_password("sandbox_api_key")
			api_url = taxjar.SANDBOX_API_URL
		else:
			api_key = self.api_key and self.get_password("api_key")
			api_url = taxjar.DEFAULT_API_URL
		return api_key, api_url

	def _fetch_nexus_regions(self, api_key, api_url):
		"""
		Call GET /v2/nexus/regions directly via requests so we have full control
		over error handling — the TaxJar Python client has a bug where error responses
		that don't include a 'status' key cause an unhandled KeyError.
		"""
		url = f"{api_url.rstrip('/')}/{taxjar.API_VERSION}/nexus/regions"
		headers = {
			"Authorization": f"Bearer {api_key}",
		}

		try:
			response = requests.get(url, headers=headers, timeout=15)
		except requests.ConnectionError:
			frappe.throw(_("Could not reach TaxJar. Please check your internet connection."))
		except requests.Timeout:
			frappe.throw(_("TaxJar request timed out. Please try again."))

		if response.status_code == 200:
			try:
				return response.json().get("regions", [])
			except Exception:
				frappe.throw(_("TaxJar returned an invalid JSON response. Please try again."))

		# Non-200 — log raw response for debugging, then show a friendly error
		try:
			body = response.json()
		except Exception:
			body = {"raw": response.text[:500]}

		frappe.log_error(
			title="TaxJar nexus fetch failed",
			message=f"URL: {url}\nHTTP {response.status_code}\nResponse: {body}",
		)

		error_messages = {
			401: _("Invalid API key. Please check your TaxJar API key and try again."),
			403: _(
				"Access denied. Your TaxJar plan may not include nexus region access. "
				"Please upgrade your TaxJar account."
			),
			404: _("TaxJar nexus endpoint not found. Please contact Lyfe Hardware support."),
			429: _("Too many requests to TaxJar. Please wait a moment and try again."),
			500: _(
				"TaxJar returned a server error (500). This is usually a temporary issue. "
				"Please try again in a few minutes. A log has been recorded under Error Log."
			),
		}

		detail = body.get("detail") or body.get("message") or body.get("error") or str(body)
		msg = error_messages.get(
			response.status_code,
			_("TaxJar API error (HTTP {0}): {1}. A log has been recorded under Error Log.").format(
				response.status_code, detail
			),
		)
		frappe.throw(msg)
