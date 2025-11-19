

frappe.ui.form.on('Item', {
    refresh: function(frm) {
        make_searchable_dropdown(frm, 'custom_item_classification_code');
    }
});

