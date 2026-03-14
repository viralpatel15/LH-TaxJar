import traceback

import frappe
import taxjar
from frappe import _
from frappe.contacts.doctype.address.address import get_company_address
from frappe.utils import cint, flt

SUPPORTED_COUNTRY_CODES = [
	"AT", "AU", "BE", "BG", "CA", "CY", "CZ", "DE", "DK", "EE",
	"ES", "FI", "FR", "GB", "GR", "HR", "HU", "IE", "IT", "LT",
	"LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK", "US",
]

SUPPORTED_STATE_CODES = [
	"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
	"GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
	"MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
	"NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
	"SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

SETTINGS_DOCTYPE = "Lyfe TaxJar Settings"


def get_client():
	settings = frappe.get_single(SETTINGS_DOCTYPE)

	if not settings.is_sandbox:
		api_key = settings.api_key and settings.get_password("api_key")
		api_url = taxjar.DEFAULT_API_URL
	else:
		api_key = settings.sandbox_api_key and settings.get_password("sandbox_api_key")
		api_url = taxjar.SANDBOX_API_URL

	if api_key and api_url:
		client = taxjar.Client(api_key=api_key, api_url=api_url)
		client.set_api_config("headers", {"x-api-version": "2022-01-24"})
		return client


def set_sales_tax(doc, method):
	TAX_ACCOUNT_HEAD = frappe.db.get_single_value(SETTINGS_DOCTYPE, "tax_account_head")
	TAXJAR_CALCULATE_TAX = frappe.db.get_single_value(SETTINGS_DOCTYPE, "taxjar_calculate_tax")

	if not TAXJAR_CALCULATE_TAX:
		return

	if not _is_us_company(doc):
		return

	if not doc.items:
		return

	if check_sales_tax_exemption(doc):
		return

	tax_dict = get_tax_data(doc)

	if not tax_dict:
		# Remove existing tax rows if address is no longer taxable
		setattr(doc, "taxes", [tax for tax in doc.taxes if tax.account_head != TAX_ACCOUNT_HEAD])
		return

	check_for_nexus(doc, tax_dict)

	tax_data = validate_tax_request(tax_dict)
	if tax_data is None:
		return

	if not tax_data.amount_to_collect:
		setattr(doc, "taxes", [tax for tax in doc.taxes if tax.account_head != TAX_ACCOUNT_HEAD])
	elif tax_data.amount_to_collect > 0:
		for tax in doc.taxes:
			if tax.account_head == TAX_ACCOUNT_HEAD:
				tax.tax_amount = tax_data.amount_to_collect
				doc.run_method("calculate_taxes_and_totals")
				break
		else:
			doc.append(
				"taxes",
				{
					"charge_type": "Actual",
					"description": "Sales Tax",
					"account_head": TAX_ACCOUNT_HEAD,
					"tax_amount": tax_data.amount_to_collect,
				},
			)

		if hasattr(tax_data, "breakdown") and tax_data.breakdown and hasattr(tax_data.breakdown, "line_items"):
			for item in tax_data.breakdown.line_items:
				idx = cint(item.id) - 1
				if 0 <= idx < len(doc.items):
					doc.get("items")[idx].tax_collectable = item.tax_collectable
					doc.get("items")[idx].taxable_amount = item.taxable_amount

		doc.run_method("calculate_taxes_and_totals")


def create_transaction(doc, method):
	"""Create an order transaction in TaxJar on Sales Invoice submit."""
	if not frappe.db.get_single_value(SETTINGS_DOCTYPE, "taxjar_create_transactions"):
		return

	client = get_client()
	if not client:
		return

	TAX_ACCOUNT_HEAD = frappe.db.get_single_value(SETTINGS_DOCTYPE, "tax_account_head")
	sales_tax = sum(tax.tax_amount for tax in doc.taxes if tax.account_head == TAX_ACCOUNT_HEAD)

	if not sales_tax:
		return

	tax_dict = get_tax_data(doc)
	if not tax_dict:
		return

	tax_dict["transaction_id"] = doc.name
	tax_dict["transaction_date"] = frappe.utils.today()
	tax_dict["sales_tax"] = sales_tax
	tax_dict["amount"] = doc.total + tax_dict["shipping"]

	try:
		if doc.is_return:
			client.create_refund(tax_dict)
		else:
			client.create_order(tax_dict)
	except taxjar.exceptions.TaxJarResponseError as err:
		frappe.throw(_(sanitize_error_response(err)))
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Lyfe TaxJar: create_transaction failed")


def delete_transaction(doc, method):
	"""Delete an existing TaxJar order transaction on Sales Invoice cancel."""
	if not frappe.db.get_single_value(SETTINGS_DOCTYPE, "taxjar_create_transactions"):
		return

	client = get_client()
	if not client:
		return

	try:
		client.delete_order(doc.name)
	except taxjar.exceptions.TaxJarResponseError as err:
		frappe.log_error(str(err), "Lyfe TaxJar: delete_transaction failed")


def get_tax_data(doc):
	SHIP_ACCOUNT_HEAD = frappe.db.get_single_value(SETTINGS_DOCTYPE, "shipping_account_head")

	from_address = get_company_address_details(doc)
	from_country_code = frappe.db.get_value("Country", from_address.country, "code").upper()
	from_shipping_state = from_address.get("state")

	to_address = get_shipping_address_details(doc)
	if not to_address:
		return None
	to_country_code = frappe.db.get_value("Country", to_address.country, "code").upper()
	to_shipping_state = to_address.get("state")

	if to_country_code not in SUPPORTED_COUNTRY_CODES:
		return None

	shipping = sum(tax.tax_amount for tax in doc.taxes if tax.account_head == SHIP_ACCOUNT_HEAD)
	line_items = [get_line_item_dict(item, doc.docstatus) for item in doc.items]

	if from_shipping_state not in SUPPORTED_STATE_CODES:
		from_shipping_state = get_state_code(from_address, "Company")

	if to_shipping_state not in SUPPORTED_STATE_CODES:
		to_shipping_state = get_state_code(to_address, "Shipping")

	return {
		"from_country": from_country_code,
		"from_zip": from_address.pincode,
		"from_state": from_shipping_state,
		"from_city": from_address.city,
		"from_street": from_address.address_line1,
		"to_country": to_country_code,
		"to_zip": to_address.pincode,
		"to_city": to_address.city,
		"to_street": to_address.address_line1,
		"to_state": to_shipping_state,
		"shipping": shipping,
		"amount": doc.net_total,
		"plugin": "erpnext",
		"line_items": line_items,
	}


def get_line_item_dict(item, docstatus):
	tax_dict = dict(
		id=item.get("idx"),
		quantity=item.get("qty"),
		unit_price=item.get("rate"),
		product_tax_code=item.get("product_tax_category"),
	)
	if docstatus == 1:
		tax_dict["sales_tax"] = item.get("tax_collectable")
	return tax_dict


def check_for_nexus(doc, tax_dict):
	TAX_ACCOUNT_HEAD = frappe.db.get_single_value(SETTINGS_DOCTYPE, "tax_account_head")

	nexus_exists = frappe.db.exists(
		"Lyfe TaxJar Nexus",
		{"parent": SETTINGS_DOCTYPE, "region_code": tax_dict.get("to_state")},
	)

	if not nexus_exists:
		for item in doc.get("items"):
			item.tax_collectable = flt(0)
			item.taxable_amount = flt(0)
		for tax in list(doc.taxes):
			if tax.account_head == TAX_ACCOUNT_HEAD:
				doc.taxes.remove(tax)


def check_sales_tax_exemption(doc):
	TAX_ACCOUNT_HEAD = frappe.db.get_single_value(SETTINGS_DOCTYPE, "tax_account_head")

	# Determine the customer identifier across Quotation / Sales Order / Sales Invoice
	customer = getattr(doc, "customer", None) or getattr(doc, "party_name", None)

	doc_exempt = hasattr(doc, "exempt_from_sales_tax") and doc.exempt_from_sales_tax
	customer_exempt = (
		customer
		and frappe.db.has_column("Customer", "exempt_from_sales_tax")
		and frappe.db.get_value("Customer", customer, "exempt_from_sales_tax")
	)

	if doc_exempt or customer_exempt:
		for tax in doc.taxes:
			if tax.account_head == TAX_ACCOUNT_HEAD:
				tax.tax_amount = 0
				break
		doc.run_method("calculate_taxes_and_totals")
		return True

	return False


def validate_tax_request(tax_dict):
	client = get_client()
	if not client:
		return None
	try:
		return client.tax_for_order(tax_dict)
	except taxjar.exceptions.TaxJarResponseError as err:
		frappe.throw(_(sanitize_error_response(err)))


def get_company_address_details(doc):
	from erpnext import get_default_company

	company = getattr(doc, "company", None) or get_default_company()
	company_address = get_company_address(company).company_address

	if not company_address:
		frappe.throw(_("Please set a default company address"))

	return frappe.get_doc("Address", company_address)


def get_shipping_address_details(doc):
	shipping_name = getattr(doc, "shipping_address_name", None)
	billing_name = getattr(doc, "customer_address", None)

	if shipping_name:
		return frappe.get_doc("Address", shipping_name)
	elif billing_name:
		return frappe.get_doc("Address", billing_name)
	else:
		return get_company_address_details(doc)


def get_state_code(address, location):
	if address is not None:
		state_code = get_iso_3166_2_state_code(address)
		if state_code not in SUPPORTED_STATE_CODES:
			frappe.throw(_("Please enter a valid State in the {0} Address").format(location))
	else:
		frappe.throw(_("Please enter a valid State in the {0} Address").format(location))
	return state_code


def get_iso_3166_2_state_code(address):
	import pycountry

	country_code = frappe.db.get_value("Country", address.get("country"), "code")
	state = address.get("state", "").upper().strip()

	error_message = _(
		"{0} is not a valid state! Check for typos or enter the ISO code for your state."
	).format(address.get("state"))

	if len(state) <= 3:
		address_state = (country_code + "-" + state).upper()
		states = [s.code for s in pycountry.subdivisions.get(country_code=country_code.upper())]
		if address_state in states:
			return state
		frappe.throw(_(error_message))
	else:
		try:
			lookup_state = pycountry.subdivisions.lookup(state)
		except LookupError:
			frappe.throw(_(error_message))
		else:
			return lookup_state.code.split("-")[1]


def sanitize_error_response(response):
	detail = response.full_response.get("detail", str(response))
	detail = detail.replace("_", " ")
	replacements = {
		"to zip": "Zipcode",
		"to city": "City",
		"to state": "State",
		"to country": "Country",
	}
	for k, v in replacements.items():
		detail = detail.replace(k, v)
	return detail


def _is_us_company(doc):
	"""Return True when the document's company is based in the United States."""
	company = getattr(doc, "company", None)
	if not company:
		from erpnext import get_default_company
		company = get_default_company()
	country = frappe.db.get_value("Company", company, "country")
	return country == "United States"
