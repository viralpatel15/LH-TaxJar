"""
Patch: create_tax_account_head
Creates two accounts in the Chart of Accounts for every company:

  1. Sales Tax Payable       → Duties and Taxes (Liability)
  2. Shipping Income         → Direct Income    (Income)

Both are then set as the Tax Account Head and Shipping Account Head in
Lyfe TaxJar Settings, but only when those fields are currently blank.
"""

import frappe


TAX_ACCOUNT_NAME = "Sales Tax Payable"
TAX_PARENT_CANDIDATES = [
	"Duties and Taxes",
	"Tax Assets",
	"Current Liabilities",
]

SHIPPING_ACCOUNT_NAME = "Shipping Income"
SHIPPING_PARENT_CANDIDATES = [
	"Direct Income",
	"Indirect Income",
	"Income",
]


def execute():
	companies = frappe.get_all("Company", fields=["name", "abbr", "default_currency"])

	for company in companies:
		tax_account = _ensure_account(
			company,
			account_name=TAX_ACCOUNT_NAME,
			account_type="Tax",
			root_type="Liability",
			parent_candidates=TAX_PARENT_CANDIDATES,
		)

		shipping_account = _ensure_account(
			company,
			account_name=SHIPPING_ACCOUNT_NAME,
			account_type="Income Account",
			root_type="Income",
			parent_candidates=SHIPPING_PARENT_CANDIDATES,
		)

		_maybe_update_settings(tax_account, shipping_account)


def _ensure_account(company, account_name, account_type, root_type, parent_candidates):
	"""
	Return the full account name (with abbreviation) for the company.
	Creates the account if it does not yet exist.
	"""
	full_name = f"{account_name} - {company.abbr}"

	if frappe.db.exists("Account", full_name):
		return full_name

	parent = _find_parent_account(company.abbr, parent_candidates, root_type)
	if not parent:
		frappe.log_error(
			f"Lyfe TaxJar: could not find a suitable parent account ({root_type}) "
			f"for company '{company.name}'. Skipped creating '{full_name}'.",
			"create_tax_account_head",
		)
		return None

	account = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": account_name,
			"account_type": account_type,
			"root_type": root_type,
			"is_group": 0,
			"company": company.name,
			"parent_account": parent,
			"account_currency": company.default_currency or "USD",
		}
	)
	account.insert(ignore_permissions=True)
	frappe.db.commit()

	return account.name


def _find_parent_account(abbr, candidates, root_type):
	"""Return the first matching group account for the given company abbreviation."""
	# Try exact name match first
	for candidate in candidates:
		name = f"{candidate} - {abbr}"
		if frappe.db.exists("Account", {"name": name, "is_group": 1}):
			return name

	# Fallback: search by account_name fragment within the correct root_type
	for candidate in candidates:
		result = frappe.db.get_value(
			"Account",
			{"account_name": candidate, "is_group": 1, "root_type": root_type},
			"name",
		)
		if result:
			return result

	return None


def _maybe_update_settings(tax_account, shipping_account):
	"""Set account heads in Lyfe TaxJar Settings only when the fields are currently blank."""
	if not frappe.db.exists("DocType", "Lyfe TaxJar Settings"):
		return

	updates = {}

	if tax_account and not frappe.db.get_single_value("Lyfe TaxJar Settings", "tax_account_head"):
		updates["tax_account_head"] = tax_account

	if shipping_account and not frappe.db.get_single_value("Lyfe TaxJar Settings", "shipping_account_head"):
		updates["shipping_account_head"] = shipping_account

	for field, value in updates.items():
		frappe.db.set_single_value("Lyfe TaxJar Settings", field, value)

	if updates:
		frappe.db.commit()
