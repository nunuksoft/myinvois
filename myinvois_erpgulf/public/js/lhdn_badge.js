// LHDN status badge.
//
// Shows where a document stands with LHDN without opening the response JSON.
// Rendered as a native Frappe indicator rather than a positioned image: it
// inherits the theme, survives light/dark and narrow viewports, and needs no
// image assets or extra HTML field on the doctype.

const LHDN_BADGE = {
    Valid:       { label: __("LHDN Valid"),       color: "green"  },
    Invalid:     { label: __("LHDN Invalid"),     color: "red"    },
    Cancelled:   { label: __("LHDN Cancelled"),   color: "darkgrey" },
    Failed:      { label: __("LHDN Failed"),      color: "orange" },
    Submitted:   { label: __("LHDN Submitted"),   color: "blue"   },
    "In Progress": { label: __("LHDN In Progress"), color: "blue" },
};

function lhdn_apply_badge(frm) {
    // Consolidated outranks the raw status: the document is a reporting
    // artefact, and that is the more useful thing to see at a glance.
    if (cint(frm.doc.custom_is_consolidated_invoice)) {
        frm.page.set_indicator(__("Consolidated e-Invoice"), "purple");
        return;
    }

    const status = (frm.doc.custom_lhdn_status || "").trim();
    if (!status) return;   // never submitted - leave the docstatus indicator alone

    const badge = LHDN_BADGE[status] || { label: `LHDN ${status}`, color: "gray" };
    frm.page.set_indicator(badge.label, badge.color);

    // Invalid is the only state that needs the user to act, so surface why.
    if (status === "Invalid" || status === "Failed") {
        const reason = lhdn_failure_reason(frm.doc.custom_submit_response);
        if (reason) {
            frm.dashboard.clear_headline();
            frm.dashboard.set_headline_alert(
                `<b>${__("LHDN rejected this document")}:</b> ${frappe.utils.escape_html(reason)}`,
                "red"
            );
        }
    }
}

function lhdn_failure_reason(response) {
    // The response shape differs between a submission-level rejection and a
    // validation failure, so try the documented paths and fall back to silence
    // rather than dumping raw JSON at the user.
    if (!response) return "";
    let parsed;
    try {
        parsed = JSON.parse(response);
    } catch (e) {
        return "";
    }
    const details = parsed?.error?.details;
    if (Array.isArray(details) && details.length) {
        return details.map((d) => d.message).filter(Boolean).join("; ");
    }
    const rejected = parsed?.rejectedDocuments;
    if (Array.isArray(rejected) && rejected.length) {
        return rejected.map((d) => d.error?.message || d.error).filter(Boolean).join("; ");
    }
    return parsed?.error?.message || "";
}

for (const dt of ["Sales Invoice", "Purchase Invoice", "Consolidated e-Invoice"]) {
    frappe.ui.form.on(dt, {
        refresh(frm) {
            try {
                lhdn_apply_badge(frm);
            } catch (e) {
                console.error("[myinvois] badge render failed", e);
            }
        },
    });
}
