frappe.ui.form.on('Address', {
    custom_state_code: function(frm) {
        const raw = frm.doc.custom_state_code || ''
        const value = raw.includes(':') ? raw.split(':').pop().trim() : raw.trim()
        frm.set_value('state', value)
    }
});
