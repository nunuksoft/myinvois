"""Repair LHDN general TINs and fill in missing item classification codes.

Two independent data problems, both of which produce documents LHDN rejects:

1. create_general_tin_customers seeded the Appendix 1 general TINs with one
   digit too many ("EI000000000010" instead of "EI00000000010"). LHDN does not
   recognise those, so any invoice using one is rejected. That patch has been
   corrected, but it already ran on existing sites and Frappe does not re-run a
   logged patch - so the bad values have to be repaired here.

2. Item.custom_item_classification_code was created without a default, leaving
   items with no LHDN classification. The field now defaults to "022:Others";
   this backfills the items created before that.
"""

import frappe

# Appendix 1 - List of General TIN (e-Invoice Specific Guideline).
GENERAL_TIN_FIXES = {
    "EI000000000010": "EI00000000010",  # General Public
    "EI000000000020": "EI00000000020",  # Foreign Buyer / Shipping Recipient
    "EI000000000030": "EI00000000030",  # Foreign Supplier
    "EI000000000040": "EI00000000040",  # Government / exempt institution
}

DEFAULT_ITEM_CLASSIFICATION = "022:Others"


def execute():
    _fix_general_tins()
    _backfill_item_classification()
    _tag_general_public_customer()
    frappe.db.commit()


def _fix_general_tins():
    """Replace the malformed general TINs wherever they were seeded."""
    for doctype in ("Customer", "Supplier"):
        if not frappe.db.has_column(doctype, "custom_customer_tin_number"):
            continue
        for bad, good in GENERAL_TIN_FIXES.items():
            names = frappe.get_all(
                doctype, filters={"custom_customer_tin_number": bad}, pluck="name"
            )
            for name in names:
                frappe.db.set_value(
                    doctype, name, "custom_customer_tin_number", good,
                    update_modified=False,
                )
                print(f"  {doctype} {name}: {bad} -> {good}")


def _backfill_item_classification():
    """Give items with no LHDN classification the catch-all code.

    "022:Others" is the code LHDN provides for anything not covered by a
    specific category, and it is what the field now defaults to, so this only
    makes the existing rows match what a newly created item would get. Items
    that already carry a code are left alone.
    """
    if not frappe.db.has_column("Item", "custom_item_classification_code"):
        return
    names = frappe.get_all(
        "Item",
        filters={"custom_item_classification_code": ["in", [None, ""]]},
        pluck="name",
    )
    for name in names:
        frappe.db.set_value(
            "Item", name, "custom_item_classification_code",
            DEFAULT_ITEM_CLASSIFICATION, update_modified=False,
        )
    print(f"  Item: set {DEFAULT_ITEM_CLASSIFICATION} on {len(names)} items")


def _tag_general_public_customer():
    """Point the seeded General Public account at the General Public buyer type.

    Without it the account only resolves by name, which breaks as soon as
    someone renames it.
    """
    if not frappe.db.has_column("Customer", "custom_einvoice_buyer_type"):
        return
    names = frappe.get_all(
        "Customer",
        filters={"custom_customer_tin_number": GENERAL_TIN_FIXES["EI000000000010"]},
        pluck="name",
    )
    for name in names:
        if frappe.db.get_value("Customer", name, "custom_einvoice_buyer_type") == "General Public":
            continue
        frappe.db.set_value(
            "Customer", name, "custom_einvoice_buyer_type", "General Public",
            update_modified=False,
        )
        print(f"  Customer {name}: buyer type -> General Public")
