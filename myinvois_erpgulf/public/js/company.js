frappe.ui.form.on('Company', {
    custom_company_registration_for_self_einvoicing: function(frm) {
        const type = (frm.doc.custom_company_registration_for_self_einvoicing || '').trim().toLowerCase();
        console.log("Normalized dropdown value:", type);

        if (type === 'brn') {
            frm.set_df_property('custom_company__registrationicpassport_number', 'label', 'Business Registration Number');
        } else if (type === 'nric') {
            frm.set_df_property('custom_company__registrationicpassport_number', 'label', 'NRIC Number');
        } else if (type === 'passport') {
            frm.set_df_property('custom_company__registrationicpassport_number', 'label', 'Passport Number');
        } else if (type === 'army') {
            frm.set_df_property('custom_company__registrationicpassport_number', 'label', 'Army ID Number');
        } else {
            frm.set_df_property('custom_company__registrationicpassport_number', 'label', 'Company Registration/IC/Passport Number');
        }

        frm.refresh_field('custom_company__registrationicpassport_number');
    },

    // Your custom method triggered somewhere else — 
    // you can call this from a custom button or another event
    custom_search_company_tin: function(frm) {
        frappe.call({
            method: "myinvois_erpgulf.myinvois_erpgulf.search_taxpayer.search_company_tin",
            args: {
                company_name: frm.doc.name
            },
            freeze: true,
            freeze_message: __("Searching for TIN..."),
            callback: function(r) {
                if (!r.exc) {
                    if (r.message?.taxpayerTIN) {
                        frappe.msgprint(__('TIN Fetched Successfully: ') + r.message.taxpayerTIN);
                    } else {
                        frappe.msgprint(__('TIN lookup completed, but TIN was not found.'));
                    }
                    frm.reload_doc();  // Refresh the document to reflect any updates
                } else {
                    frappe.msgprint(__('Something went wrong while fetching TIN.'));
                }
            }
        });
    }
});

frappe.ui.form.on("Company", {
    refresh: function(frm) {
        // Optional actions on refresh
        make_searchable_dropdown(frm, 'custom_msic_code_');
    },
    custom_taxpayer_login: function(frm) {
        frappe.call({
            method: "myinvois_erpgulf.myinvois_erpgulf.taxpayerlogin.get_access_token",
            args: {
                doc: frm.doc.name  // Send just the company name string
            },
            callback: function(r) {
                if (!r.exc) {
                    frappe.msgprint("Access token fetched successfully!");
                    frm.reload_doc();  // Reload to show updated token
                } else {
                    frappe.msgprint("Failed to fetch access token.");
                }
            },
            error: function(err) {
                frappe.msgprint("Error: " + err.message);
            }
        });
    }
});
