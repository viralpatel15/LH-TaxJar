# Lyfe TaxJar Integration

Automatic US sales tax calculation for **Quotation**, **Sales Order**, and **Sales Invoice** using the [TaxJar API](https://www.taxjar.com/).

---

## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [How It Works](#how-it-works)
5. [Per-Item Tax Categories](#per-item-tax-categories)
6. [Nexus Management](#nexus-management)
7. [Transaction Recording](#transaction-recording)
8. [Customer Tax Exemption](#customer-tax-exemption)
9. [Sandbox / Testing Mode](#sandbox--testing-mode)
10. [Troubleshooting](#troubleshooting)

---

## Requirements

| Requirement | Version |
|---|---|
| Frappe | v15 |
| ERPNext | v15 |
| Python | ≥ 3.10 |
| `taxjar` Python package | any (installed automatically) |
| TaxJar account | Free or paid plan |

The company's registered country in ERPNext must be set to **United States**. Tax calculation is skipped automatically for non-US companies.

---

## Installation

### 1. Get a TaxJar API Key

- Sign up at [app.taxjar.com](https://app.taxjar.com)
- Go to **Account → TaxJar API** to copy your **Live API Token**
- Optionally copy the **Sandbox API Token** for testing

### 2. Install the App

```bash
bench get-app lyfe_taxjar   # if fetching from remote
bench --site <your-site> install-app lyfe_taxjar
```

The installer automatically:
- Creates the **Lyfe TaxJar Settings** doctype
- Creates the **Product Tax Category** doctype and seeds it with 816 TaxJar categories
- Adds custom fields to `Item`, `Quotation Item`, `Sales Order Item`, and `Sales Invoice Item`

---

## Configuration

Navigate to **Lyfe TaxJar Settings** (search in the Frappe desk search bar).

### Fields

| Field | Required | Description |
|---|---|---|
| **Enable Tax Calculation** | — | Master switch. Must be ON for any tax to be calculated. |
| **Live API Key** | Yes | Your TaxJar production API token. |
| **Sandbox Mode** | — | Use sandbox API instead of live. See [Sandbox](#sandbox--testing-mode). |
| **Sandbox API Key** | If sandbox | Your TaxJar sandbox API token. |
| **Create TaxJar Transaction** | — | Records confirmed invoices in your TaxJar account for filing reports. Requires Enable Tax Calculation to be ON. |
| **Company** | — | The ERPNext company this configuration applies to. Leave blank to use the default company. |
| **Tax Account Head** | Yes | The GL account where sales tax will be posted (e.g. `Sales Tax Payable - LH`). |
| **Shipping Account Head** | Yes | The GL account used for shipping charges. Used to pass shipping cost to TaxJar for accurate tax. |
| **Nexus List** | Auto | Populated by **Update Nexus List** button. Tax is only calculated when shipping to a state in this list. |

### Step-by-Step Setup

**Step 1 — Enter your API key**

Paste your Live API Key into the **Live API Key** field.

**Step 2 — Set account heads**

- **Tax Account Head**: Open your Chart of Accounts and find (or create) a liability account for sales tax, e.g. `Sales Tax Payable - LH`. Select it here.
- **Shipping Account Head**: Select the income/expense account used for shipping line items in your tax templates.

**Step 3 — Enable tax calculation**

Check **Enable Tax Calculation**.

**Step 4 — Update your nexus list**

Click the **Update Nexus List** button. This calls TaxJar and fetches all states where you have nexus (a tax collection obligation). Tax will only be calculated for orders shipping to states in this list.

**Step 5 — Save**

Click **Save**. The app is now active.

---

## How It Works

Every time a **Quotation**, **Sales Order**, or **Sales Invoice** is saved (on `validate`), the app:

1. Checks that **Enable Tax Calculation** is ON and the company is US-based.
2. Reads the **ship-to address** from the document (`shipping_address_name` → `customer_address` → company address as fallback).
3. Reads the **ship-from address** from the default company address.
4. Checks that the destination state is in your **Nexus List**. If not, any existing sales tax row is removed and no tax is added.
5. Sends the order details (line items, amounts, shipping cost, addresses) to the TaxJar API.
6. Applies the returned `amount_to_collect` as an **Actual** tax charge row using the configured **Tax Account Head**.
7. Updates `tax_collectable` and `taxable_amount` on each line item for visibility.

Tax is recalculated every time the document is saved — so changing the shipping address, quantity, or price will automatically update the tax.

### Address Requirements

| Field | Where it comes from |
|---|---|
| Ship-from (origin) | Default company address |
| Ship-to (destination) | `Shipping Address` on the document, fallback to `Customer Address` |

Both addresses must have a valid **US state** and **ZIP code** for tax calculation to work. If the state is not a standard two-letter code (e.g. `FL`), the app will attempt to look it up via ISO 3166-2.

---

## Per-Item Tax Categories

TaxJar supports product-specific tax rules (e.g. clothing, software, food). You can assign a **Product Tax Category** to each item.

### Assign a category to an Item

1. Open any **Item** record.
2. Find the **Product Tax Category** field (added automatically by the app).
3. Select the appropriate category from the list of 816 TaxJar categories.

When an item is added to a Quotation / Sales Order / Sales Invoice, the category is auto-fetched from the Item record via the `product_tax_category` custom field.

### Common categories

| Category Name | Tax Code |
|---|---|
| General Tangible Personal Property | (blank / default) |
| Clothing | `20010` |
| Software as a Service (SaaS) | `30070` |
| Digital goods | `31000` |
| Food & grocery | `40030` |
| Medical devices | `51010` |

Leave the field blank to apply the default tax rate for the destination state.

---

## Nexus Management

**Nexus** is the legal obligation to collect sales tax in a state. You only need to collect tax where you have nexus.

### Update nexus list

In **Lyfe TaxJar Settings**, click **Update Nexus List**. This fetches your current nexus regions directly from TaxJar (based on your account configuration) and saves them to the settings record.

You can manage your nexus states in your [TaxJar dashboard](https://app.taxjar.com/nexus) and re-click **Update Nexus List** any time to sync.

If an order ships to a state **not** in your nexus list, no tax is added and any previously calculated tax row is removed.

---

## Transaction Recording

When **Create TaxJar Transaction** is enabled, the app will:

- **On Sales Invoice submit** → create a corresponding order record in TaxJar with the final tax amounts. This is used by TaxJar's AutoFile feature to prepare your tax returns.
- **On Sales Invoice cancel** → delete the order record from TaxJar.
- **On Sales Invoice submit (return / credit note)** → create a refund record in TaxJar.

> **Note:** Transaction recording only applies to Sales Invoice — not Quotation or Sales Order.

### Requirements for transaction recording

1. **Enable Tax Calculation** must be ON.
2. **Create TaxJar Transaction** must be ON.
3. The invoice must have a non-zero sales tax amount before submitting.

---

## Customer Tax Exemption

To mark a customer as exempt from sales tax:

1. Open the **Customer** record.
2. Check the **Exempt from Sales Tax** field (added by ERPNext's US regional setup).

When a document is saved for an exempt customer, any existing sales tax row is zeroed out and no new tax is calculated.

You can also check **Exempt from Sales Tax** directly on an individual Quotation, Sales Order, or Sales Invoice to override for a single document.

---

## Sandbox / Testing Mode

Use sandbox mode to test the integration without affecting your live TaxJar account.

1. Enter your **Sandbox API Key** (from [app.taxjar.com → Account → API Access](https://app.taxjar.com/account#api-access)).
2. Check **Sandbox Mode**.
3. Check **Enable Tax Calculation**.
4. Save.

In sandbox mode all API calls go to `https://api.sandbox.taxjar.com`. Transactions created in sandbox do not appear in your live reports.

> Sandbox mode cannot be enabled without **Enable Tax Calculation** being checked first.

---

## Troubleshooting

### Tax is not being calculated

| Check | How to verify |
|---|---|
| **Enable Tax Calculation** is ON | Open Lyfe TaxJar Settings |
| Company country is **United States** | Open Company record → Country field |
| Shipping address has a valid state and ZIP | Open the customer's address record |
| Destination state is in your nexus list | Check Nexus List table in settings; click Update Nexus List |
| API key is valid | Verify in your TaxJar account dashboard |

### "Please set a default company address" error

ERPNext requires a default address for your company. Go to **Company → Address and Contacts**, create an address, and mark it as the default.

### "Please enter a valid State in the Shipping Address" error

The state field in the shipping address is not a recognised ISO 3166-2 code. Use the standard two-letter US state code (e.g. `FL`, `TX`, `CA`).

### Tax is calculated but then disappears on save

The destination state is not in your nexus list. Click **Update Nexus List** in Lyfe TaxJar Settings to refresh from TaxJar, or add the state to your nexus in your TaxJar account first.

### Transactions not appearing in TaxJar

Verify **Create TaxJar Transaction** is enabled and the Sales Invoice has a non-zero sales tax amount before submitting.

---

## Support

- Email: support@lyfehardware.com
- Phone: +1 (833) 300-0997
- Website: [www.lyfehardware.com](https://www.lyfehardware.com)

---

## License

MIT
