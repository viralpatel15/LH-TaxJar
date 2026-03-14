import json
import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property


def after_install():
	seed_product_tax_categories()
	make_custom_fields()
	add_permissions()
	from lyfe_taxjar.lyfe_taxjar.patches.create_tax_account_head import execute as create_tax_account_head
	create_tax_account_head()


def seed_product_tax_categories():
	"""Load TaxJar product tax categories from the bundled JSON."""
	data_file = os.path.join(
		os.path.dirname(__file__),
		"doctype",
		"product_tax_category",
		"product_tax_category_data.json",
	)
	with open(data_file) as f:
		categories = json.load(f).get("categories", [])

	for cat in categories:
		if not frappe.db.exists("Product Tax Category", {"product_tax_code": cat.get("product_tax_code")}):
			doc = frappe.new_doc("Product Tax Category")
			doc.product_tax_code = cat.get("product_tax_code")
			doc.category_name = cat.get("name")
			doc.description = cat.get("description")
			doc.db_insert()


def make_custom_fields(update=True):
	"""Add product_tax_category, tax_collectable, and taxable_amount to item child tables."""
	item_link_field = dict(
		fieldname="product_tax_category",
		fieldtype="Link",
		insert_after="description",
		options="Product Tax Category",
		label="Product Tax Category",
		fetch_from="item_code.product_tax_category",
	)

	custom_fields = {
		"Sales Invoice Item": [
			item_link_field,
			dict(
				fieldname="tax_collectable",
				fieldtype="Currency",
				insert_after="net_amount",
				label="Tax Collectable",
				read_only=1,
				options="currency",
			),
			dict(
				fieldname="taxable_amount",
				fieldtype="Currency",
				insert_after="tax_collectable",
				label="Taxable Amount",
				read_only=1,
				options="currency",
			),
		],
		"Sales Order Item": [
			item_link_field,
			dict(
				fieldname="tax_collectable",
				fieldtype="Currency",
				insert_after="net_amount",
				label="Tax Collectable",
				read_only=1,
				options="currency",
			),
			dict(
				fieldname="taxable_amount",
				fieldtype="Currency",
				insert_after="tax_collectable",
				label="Taxable Amount",
				read_only=1,
				options="currency",
			),
		],
		"Quotation Item": [
			item_link_field,
			dict(
				fieldname="tax_collectable",
				fieldtype="Currency",
				insert_after="net_amount",
				label="Tax Collectable",
				read_only=1,
				options="currency",
			),
			dict(
				fieldname="taxable_amount",
				fieldtype="Currency",
				insert_after="tax_collectable",
				label="Taxable Amount",
				read_only=1,
				options="currency",
			),
		],
		"Item": [
			dict(
				fieldname="product_tax_category",
				fieldtype="Link",
				insert_after="item_group",
				options="Product Tax Category",
				label="Product Tax Category",
			)
		],
	}
	create_custom_fields(custom_fields, update=update)


def add_permissions():
	"""Grant read/write access to Product Tax Category for relevant roles."""
	if not frappe.db.exists("DocType", "Product Tax Category"):
		return

	doctype = "Product Tax Category"
	for role in ("Accounts Manager", "Accounts User", "System Manager", "Item Manager", "Stock Manager"):
		add_permission(doctype, role, 0)
		update_permission_property(doctype, role, 0, "write", 1)
		update_permission_property(doctype, role, 0, "create", 1)
