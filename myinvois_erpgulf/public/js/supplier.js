frappe.ui.form.on("Supplier", {
    refresh: function(frm) {
        make_searchable_dropdown(frm, 'custom_msic_code_');
    }
});
