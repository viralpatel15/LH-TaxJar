frappe.ui.form.on("Lyfe TaxJar Settings", {
	onload(frm) {
		// Filter account heads to the selected company
		["tax_account_head", "shipping_account_head"].forEach((field) => {
			frm.set_query(field, () => ({
				filters: {
					company: frm.doc.company || frappe.defaults.get_default("company"),
					is_group: 0,
				},
			}));
		});
	},

	is_sandbox(frm) {
		frm.toggle_reqd("sandbox_api_key", frm.doc.is_sandbox);
		frm.toggle_reqd("api_key", !frm.doc.is_sandbox);
	},

	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Update Nexus List"), () => {
				frappe.call({
					doc: frm.doc,
					method: "update_nexus_list",
					callback() {
						frm.reload_doc();
					},
				});
			});
		}
	},
});
