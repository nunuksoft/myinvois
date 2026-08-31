"""THIS MODULE IS FOR MERGE AND CONSOLIDATE INVOICES"""

import xml.etree.ElementTree as ET
import re
import frappe
from frappe import _
import datetime


NOT_APPLICABLE = "NA"

# LHDN e-Invoice Specific Guideline - Appendix 1 (list of general TIN) and
# Appendix 2 (Buyer's details in consolidated e-Invoice).
GENERAL_PUBLIC_TIN = "EI00000000010"
GENERAL_PUBLIC_NAME = "General Public"
FOREIGN_BUYER_TIN = "EI00000000020"
GOVERNMENT_BUYER_TIN = "EI00000000040"

# Values of the Customer field "e-Invoice Buyer Type".
BUYER_TYPE_STANDARD = "Standard"
BUYER_TYPE_FOREIGN = "Foreign Buyer"
BUYER_TYPE_GOVERNMENT = "Government / Exempt"

# Appendix 1 - general TIN submitted in place of the buyer's own TIN. Only
# "General Public" also blanks out the rest of the buyer block (Appendix 2);
# the other two keep the buyer's real name, address and contact details.
BUYER_TYPE_GENERAL_TIN = {
    GENERAL_PUBLIC_NAME: GENERAL_PUBLIC_TIN,
    BUYER_TYPE_FOREIGN: FOREIGN_BUYER_TIN,
    BUYER_TYPE_GOVERNMENT: GOVERNMENT_BUYER_TIN,
}
# MyInvois state code 17 = "Not Applicable".
STATE_CODE_NOT_APPLICABLE = "17"

# Reporting-only doctype that carries a consolidated e-Invoice to LHDN.
CONSOLIDATED_DOCTYPE = "Consolidated e-Invoice"


def buyer_general_tin(customer_doc):
    """Appendix 1 general TIN for this customer, or None to use their own.

    Returned for the buyer types that LHDN lets a Supplier submit without the
    buyer's real TIN. The buyer's other details are untouched - see
    is_consolidated_buyer() for the one type that replaces them too.
    """
    buyer_type = (customer_doc.get("custom_einvoice_buyer_type") or "").strip()
    if not buyer_type or buyer_type.lower() == BUYER_TYPE_STANDARD.lower():
        return None
    for label, tin in BUYER_TYPE_GENERAL_TIN.items():
        if buyer_type.lower() == label.lower():
            return tin
    return None


def is_consolidated_buyer(sales_invoice_doc, customer_doc=None):
    """True when the Buyer block must follow Appendix 2 (General Public).

    True in three cases:

    1. The invoice carries the "Is Consolidated Invoice" flag set by
       merge_sales_invoices().
    2. The Customer has "e-Invoice Buyer Type" set to "General Public". The
       invoice keeps that customer in the ledger - only the buyer block sent
       to LHDN is replaced - so identified customers who never request an
       individual e-Invoice can be billed normally.
    3. The Customer *is* the General Public walk-in account. The name check is
       case-insensitive and ignores a trailing parenthetical, so
       "General Public" and "General Public (E-Invoice)" both match, while an
       unrelated name such as "General Public Services Sdn Bhd" does not.
    """
    if sales_invoice_doc.get("custom_is_consolidated_invoice"):
        return True
    if customer_doc is None:
        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)
    buyer_type = (customer_doc.get("custom_einvoice_buyer_type") or "").strip()
    if buyer_type.lower() == GENERAL_PUBLIC_NAME.lower():
        return True
    for value in (customer_doc.get("customer_name"), customer_doc.get("name")):
        if not value:
            continue
        base = re.split(r"[(\[]", str(value))[0].strip().lower()
        if base == GENERAL_PUBLIC_NAME.lower():
            return True
    return False


def get_general_public_customer():
    """Return the Customer record used as the General Public buyer.

    merge_sales_invoices() used to hard-code the docname "General Public",
    which breaks whenever the account is named differently (for example
    "General Public (E-Invoice)"). Resolve it by name instead and fail with a
    clear message when it has not been created yet.
    """
    for customer in frappe.get_all("Customer", fields=["name", "customer_name"]):
        if is_consolidated_buyer(frappe._dict(), frappe._dict(customer)):
            return customer["name"]
    frappe.throw(
        _(
            "No General Public customer found. Create a Customer named "
            "'General Public' with TIN {0} before consolidating invoices."
        ).format(GENERAL_PUBLIC_TIN)
    )


def customer_data_consolidate(invoice, sales_invoice_doc):
    """Adds the Buyer data for a consolidated e-Invoice.

    Values follow LHDN e-Invoice Specific Guideline, Appendix 2
    (Buyer's details in consolidated e-Invoice):
        Buyer's Name .................... "General Public"
        Buyer's TIN ..................... "EI00000000010"
        Registration / ID / Passport .... "NA"
        Buyer's Address ................. "NA"
        Buyer's Contact Number .......... "NA"
        Buyer's SST Registration Number . "NA"
    """
    try:
        accounting_customer_party = ET.SubElement(
            invoice, "cac:AccountingCustomerParty"
        )
        cac_Party = ET.SubElement(accounting_customer_party, "cac:Party")

        # Appendix 2 (2) - Buyer's TIN is always the General Public TIN
        party_id_1 = ET.SubElement(cac_Party, "cac:PartyIdentification")
        prty_id = ET.SubElement(party_id_1, "cbc:ID", schemeID="TIN")
        prty_id.text = GENERAL_PUBLIC_TIN

        # Appendix 2 (3) - Registration / Identification / Passport Number
        party_identifn_2 = ET.SubElement(cac_Party, "cac:PartyIdentification")
        id_party2 = ET.SubElement(party_identifn_2, "cbc:ID", schemeID="BRN")
        id_party2.text = NOT_APPLICABLE

        # Appendix 2 (6) - SST Registration Number
        partyid_3 = ET.SubElement(cac_Party, "cac:PartyIdentification")
        value_id3 = ET.SubElement(partyid_3, "cbc:ID", schemeID="SST")
        value_id3.text = NOT_APPLICABLE

        partyid_4 = ET.SubElement(cac_Party, "cac:PartyIdentification")
        value_id4 = ET.SubElement(partyid_4, "cbc:ID", schemeID="TTX")
        value_id4.text = NOT_APPLICABLE

        # Appendix 2 (4) - Buyer's Address.
        # CityName, CountrySubentityCode, AddressLine and Country are all
        # mandatory [1..1] in the UBL schema, so "NA" is carried through them
        # and the state code is 17 ("Not Applicable"). PostalZone is [0..1]
        # and is omitted rather than filled with a non-numeric placeholder.
        posta_address = ET.SubElement(cac_Party, "cac:PostalAddress")
        name_city = ET.SubElement(posta_address, "cbc:CityName")
        name_city.text = NOT_APPLICABLE

        cntry_sub_cod = ET.SubElement(posta_address, "cbc:CountrySubentityCode")
        cntry_sub_cod.text = STATE_CODE_NOT_APPLICABLE

        add_cust_line1 = ET.SubElement(posta_address, "cac:AddressLine")
        add_line1 = ET.SubElement(add_cust_line1, "cbc:Line")
        add_line1.text = NOT_APPLICABLE

        cnty_customer = ET.SubElement(posta_address, "cac:Country")
        idntfn_code_val = ET.SubElement(
            cnty_customer,
            "cbc:IdentificationCode",
            listAgencyID="6",
            listID="ISO3166-1",
        )
        idntfn_code_val.text = "MYS"

        # Appendix 2 (1) - Buyer's Name
        party_legalentity = ET.SubElement(cac_Party, "cac:PartyLegalEntity")
        reg_name_val = ET.SubElement(party_legalentity, "cbc:RegistrationName")
        reg_name_val.text = GENERAL_PUBLIC_NAME

        # Appendix 2 (5) - Buyer's Contact Number
        cont_customer = ET.SubElement(cac_Party, "cac:Contact")
        tele_party = ET.SubElement(cont_customer, "cbc:Telephone")
        tele_party.text = NOT_APPLICABLE
        return invoice
    except Exception as e:
        frappe.throw(_(f"Error customer data: {str(e)}"))
        return None


def delivery_data_consolidate(invoice, sales_invoice_doc):
    """Adds the Shipping Recipient data for a consolidated e-Invoice.

    Mirrors the Buyer block above - the shipping recipient of a consolidated
    e-Invoice is the same undisclosed General Public.
    """
    try:
        delivery = ET.SubElement(invoice, "cac:Delivery")
        delivery_party = ET.SubElement(delivery, "cac:DeliveryParty")

        party_id_tin = ET.SubElement(delivery_party, "cac:PartyIdentification")
        tin_id = ET.SubElement(party_id_tin, "cbc:ID", schemeID="TIN")
        tin_id.text = GENERAL_PUBLIC_TIN

        party_id_brn = ET.SubElement(delivery_party, "cac:PartyIdentification")
        brn_id = ET.SubElement(party_id_brn, "cbc:ID", schemeID="BRN")
        brn_id.text = NOT_APPLICABLE

        postal_address = ET.SubElement(delivery_party, "cac:PostalAddress")
        city_name = ET.SubElement(postal_address, "cbc:CityName")
        city_name.text = NOT_APPLICABLE

        country_subentity_code = ET.SubElement(
            postal_address, "cbc:CountrySubentityCode"
        )
        country_subentity_code.text = STATE_CODE_NOT_APPLICABLE

        address_line1 = ET.SubElement(
            ET.SubElement(postal_address, "cac:AddressLine"), "cbc:Line"
        )
        address_line1.text = NOT_APPLICABLE

        country = ET.SubElement(postal_address, "cac:Country")
        country_id_code = ET.SubElement(
            country,
            "cbc:IdentificationCode",
            listAgencyID="6",
            listID="ISO3166-1",
        )
        country_id_code.text = "MYS"

        party_legal_entity = ET.SubElement(delivery_party, "cac:PartyLegalEntity")
        registration_name = ET.SubElement(party_legal_entity, "cbc:RegistrationName")
        registration_name.text = GENERAL_PUBLIC_NAME
        return invoice
    except Exception as e:
        frappe.throw(_(f"Error in customer_data: {str(e)}"))
        return None


# @frappe.whitelist(allow_guest=True)
# def merge_sales_invoices(invoice_numbers):
#     """
#     Merge multiple Sales Invoices into a single consolidated invoice.
#     Excludes items where amount > 10,000.
#     Creates separate invoices for such items, preserving original customer and tax details.
#     """
#     if isinstance(invoice_numbers, str):
#         invoice_numbers = frappe.parse_json(invoice_numbers)

#     if not invoice_numbers or len(invoice_numbers) < 2:
#         frappe.throw(_("Please select at least two Sales Invoices to merge."))

#     sales_invoices = frappe.get_all(
#         "Sales Invoice",
#         filters={"name": ["in", invoice_numbers]},
#         fields=[
#             "name",
#             "customer",
#             "company",
#             "currency",
#             "conversion_rate",
#             "posting_date",
#             "due_date",
#             "customer_name",
#             "customer_group",
#             "territory",
#             "is_pos",
#             "debit_to",
#             "docstatus",
#         ],
#     )

#     if not sales_invoices:
#         frappe.throw(_("No valid Sales Invoices found."))

#     sales_invoices = frappe.get_all(
#         "Sales Invoice",
#         filters={
#             "name": ["in", invoice_numbers],
#             "custom_consolidate_invoice_number": ["is", "not set"],
#         },
#         fields=[
#             "name",
#             "customer",
#             "company",
#             "currency",
#             "conversion_rate",
#             "posting_date",
#             "due_date",
#             "customer_name",
#             "customer_group",
#             "territory",
#             "is_pos",
#             "debit_to",
#             "docstatus",
#         ],
#     )

#     already_merged = [
#         name
#         for name in invoice_numbers
#         if name not in [inv["name"] for inv in sales_invoices]
#     ]

#     if already_merged:
#         frappe.throw(
#             _(
#                 "The following invoices are already consolidated and cannot be merged again:"
#             )
#             + "<br>"
#             + "<br>".join(already_merged)
#         )
#     base_invoice = sales_invoices[0]

#     new_invoice = frappe.get_doc(
#         {
#             "doctype": "Sales Invoice",
#             "customer": "General Public",
#             "customer_name": "General Public",
#             "company": base_invoice["company"],
#             "currency": base_invoice["currency"],
#             "conversion_rate": base_invoice["conversion_rate"],
#             "posting_date": min([inv["posting_date"] for inv in sales_invoices]),
#             "due_date": max([inv["due_date"] for inv in sales_invoices]),
#             "customer_group": base_invoice["customer_group"],
#             "territory": base_invoice["territory"],
#             "is_pos": base_invoice["is_pos"],
#             "debit_to": base_invoice["debit_to"],
#             "is_return": 0,
#             "custom_is_submit_to_lhdn": 1,
#             "items": [],
#             "taxes": [],
#             "remarks": f"Merged from invoices: {', '.join(invoice_numbers)}",
#             "custom_submission_time": datetime.datetime.now(
#                 datetime.timezone.utc
#             ).strftime("%Y-%m-%dT%H:%M:%SZ"),
#         }
#     )

#     item_dict = {}
#     excluded_items_map = []

#     for inv in sales_invoices:
#         invoice_items = frappe.get_all(
#             "Sales Invoice Item",
#             filters={"parent": inv["name"]},
#             fields=[
#                 "item_code",
#                 "item_name",
#                 "description",
#                 "qty",
#                 "rate",
#                 "amount",
#                 "income_account",
#                 "cost_center",
#                 "custom_item_classification_codes",
#             ],
#         )
#         for item in invoice_items:
#             if item["amount"] > 10000:
#                 excluded_items_map.append({"invoice": inv, "item": item})
#                 continue

#             item_key = (item["item_code"], item["rate"])
#             if item_key in item_dict:
#                 item_dict[item_key]["qty"] += item["qty"]
#                 item_dict[item_key]["amount"] += item["amount"]
#             else:
#                 new_item = item.copy()
#                 new_item["custom_item_classification_codes"] = (
#                     "004:Consolidated e-Invoice"
#                 )
#                 item_dict[item_key] = new_item

#     if not item_dict:
#         frappe.throw(
#             _(
#                 "All items were excluded because their amount exceeded 10,000. Consolidated invoice not created."
#             )
#         )

#     for item in item_dict.values():
#         new_invoice.append("items", item)

#     # Consolidate taxes from original invoices
#     tax_dict = {}
#     for inv in sales_invoices:
#         invoice_taxes = frappe.get_all(
#             "Sales Taxes and Charges",
#             filters={"parent": inv["name"]},
#             fields=["charge_type", "account_head", "description", "rate", "tax_amount"],
#         )
#         for tax in invoice_taxes:
#             tax_key = (tax["account_head"], tax["charge_type"])
#             if tax_key in tax_dict:
#                 tax_dict[tax_key]["tax_amount"] += tax["tax_amount"]
#             else:
#                 tax_dict[tax_key] = tax.copy()

#     for tax in tax_dict.values():
#         new_invoice.append("taxes", tax)

#     # Set item classification codes
#     for row in new_invoice.items:
#         row.custom_item_classification_codes = "004:Consolidated e-Invoice"

#     new_invoice.insert()

#     new_invoice.submit()

#     # Update original invoices
#     for inv in sales_invoices:
#         doc = frappe.get_doc("Sales Invoice", inv["name"])
#         doc.custom_consolidate_invoice_number = new_invoice.name
#         doc.save(ignore_permissions=True)

#     # Create separate invoices for excluded items
#     excluded_items_messages = []
#     for entry in excluded_items_map:
#         inv = entry["invoice"]
#         item = entry["item"]

#         original_taxes = frappe.get_all(
#             "Sales Taxes and Charges",
#             filters={"parent": inv["name"]},
#             fields=["charge_type", "account_head", "description", "rate", "tax_amount"],
#         )

#         new_single_invoice = frappe.get_doc(
#             {
#                 "doctype": "Sales Invoice",
#                 "customer": inv["customer"],
#                 "customer_name": inv["customer_name"],
#                 "company": inv["company"],
#                 "currency": inv["currency"],
#                 "conversion_rate": inv["conversion_rate"],
#                 "posting_date": inv["posting_date"],
#                 "due_date": inv["due_date"],
#                 "customer_group": inv["customer_group"],
#                 "territory": inv["territory"],
#                 "is_pos": inv["is_pos"],
#                 "debit_to": inv["debit_to"],
#                 "is_return": 0,
#                 "custom_is_submit_to_lhdn": 1,
#                 "items": [
#                     {
#                         "item_code": item["item_code"],
#                         "item_name": item["item_name"],
#                         "description": item["description"],
#                         "qty": item["qty"],
#                         "rate": item["rate"],
#                         "amount": item["amount"],
#                         "income_account": item["income_account"],
#                         "cost_center": item["cost_center"],
#                         "custom_item_classification_codes": item.get(
#                             "custom_item_classification_codes", ""
#                         ),
#                     }
#                 ],
#                 "remarks": f"Auto-created from item exceeding 10,000 in invoice {inv['name']}",
#                 "custom_submission_time": datetime.datetime.now(
#                     datetime.timezone.utc
#                 ).strftime("%Y-%m-%dT%H:%M:%SZ"),
#             }
#         )

#         for tax in original_taxes:
#             new_single_invoice.append(
#                 "taxes",
#                 {
#                     "charge_type": tax["charge_type"],
#                     "account_head": tax["account_head"],
#                     "description": tax["description"],
#                     "rate": tax["rate"],
#                     "tax_amount": tax["tax_amount"],
#                 },
#             )

#         new_single_invoice.insert()
#         new_single_invoice.submit()

#         excluded_items_messages.append(
#             f"{item['item_code']} (Amount: {item['amount']}) from Invoice: {inv['name']} "
#             f"moved to new invoice: {new_single_invoice.name}"
#         )

#     # Show message with excluded items
#     if excluded_items_messages:
#         frappe.msgprint(
#             _(
#                 "The following items were excluded from the consolidated invoice because their amount exceeded 10,000. "
#                 "Individual invoices were created:"
#             )
#             + "<br>"
#             + "<br>".join(excluded_items_messages),
#             title=_("Excluded Items"),
#             indicator="orange",
#         )

#     return new_invoice.name


# @frappe.whitelist(allow_guest=True)
# def merge_sales_invoices(invoice_numbers):
#     """
#     Merge multiple Sales Invoices into a single consolidated invoice.
#     Excludes items where amount > 10,000.
#     Creates separate invoices for such items, preserving original customer and tax details.
#     """
#     import datetime

#     if isinstance(invoice_numbers, str):
#         invoice_numbers = frappe.parse_json(invoice_numbers)

#     if not invoice_numbers or len(invoice_numbers) < 2:
#         frappe.throw(_("Please select at least two Sales Invoices to merge."))

#     sales_invoices = frappe.get_all(
#         "Sales Invoice",
#         filters={"name": ["in", invoice_numbers]},
#         fields=[
#             "name",
#             "customer",
#             "company",
#             "currency",
#             "conversion_rate",
#             "posting_date",
#             "due_date",
#             "customer_name",
#             "customer_group",
#             "territory",
#             "is_pos",
#             "debit_to",
#             "docstatus",
#         ],
#     )

#     if not sales_invoices:
#         frappe.throw(_("No valid Sales Invoices found."))

#     sales_invoices = frappe.get_all(
#         "Sales Invoice",
#         filters={
#             "name": ["in", invoice_numbers],
#             "custom_consolidate_invoice_number": ["is", "not set"],
#         },
#         fields=[
#             "name",
#             "customer",
#             "company",
#             "currency",
#             "conversion_rate",
#             "posting_date",
#             "due_date",
#             "customer_name",
#             "customer_group",
#             "territory",
#             "is_pos",
#             "debit_to",
#             "docstatus",
#         ],
#     )

#     already_merged = [
#         name
#         for name in invoice_numbers
#         if name not in [inv["name"] for inv in sales_invoices]
#     ]

#     if already_merged:
#         frappe.throw(
#             _(
#                 "The following invoices are already consolidated and cannot be merged again:"
#             )
#             + "<br>"
#             + "<br>".join(already_merged)
#         )

#     base_invoice = sales_invoices[0]

#     new_invoice = frappe.get_doc(
#         {
#             "doctype": "Sales Invoice",
#             "customer": "General Public",
#             "customer_name": "General Public",
#             "company": base_invoice["company"],
#             "currency": base_invoice["currency"],
#             "conversion_rate": base_invoice["conversion_rate"],
#             "posting_date": min([inv["posting_date"] for inv in sales_invoices]),
#             "due_date": max([inv["due_date"] for inv in sales_invoices]),
#             "customer_group": base_invoice["customer_group"],
#             "territory": base_invoice["territory"],
#             "is_pos": base_invoice["is_pos"],
#             "debit_to": base_invoice["debit_to"],
#             "is_return": 0,
#             "custom_is_submit_to_lhdn": 1,
#             "custom_is_consolidated_invoice": 1,
#             "items": [],
#             "taxes": [],
#             "remarks": f"Merged from invoices: {', '.join(invoice_numbers)}",
#             "custom_submission_time": datetime.datetime.now(
#                 datetime.timezone.utc
#             ).strftime("%Y-%m-%dT%H:%M:%SZ"),
#         }
#     )

#     item_dict = {}
#     excluded_items_map = []

#     for inv in sales_invoices:
#         invoice_items = frappe.get_all(
#             "Sales Invoice Item",
#             filters={"parent": inv["name"]},
#             fields=[
#                 "item_code",
#                 "item_name",
#                 "description",
#                 "qty",
#                 "rate",
#                 "amount",
#                 "income_account",
#                 "cost_center",
#                 "custom_item_classification_codes",
#             ],
#         )
#         for item in invoice_items:
#             if item["amount"] > 10000:
#                 excluded_items_map.append({"invoice": inv, "item": item})
#                 continue

#             # Use invoice name in the key to avoid merging across invoices
#             item_key = (item["item_code"], item["rate"], inv["name"])

#             new_item = item.copy()
#             new_item["custom_item_classification_codes"] = "004:Consolidated e-Invoice"
#             new_item["custom_consolidated_invoice_refrence_copy"] = inv["name"]
#             item_dict[item_key] = new_item

#     if not item_dict:
#         frappe.throw(
#             _(
#                 "All items were excluded because their amount exceeded 10,000. Consolidated invoice not created."
#             )
#         )

#     for item in item_dict.values():
#         new_invoice.append("items", item)

#     # Consolidate taxes from original invoices
#     tax_dict = {}
#     for inv in sales_invoices:
#         invoice_taxes = frappe.get_all(
#             "Sales Taxes and Charges",
#             filters={"parent": inv["name"]},
#             fields=["charge_type", "account_head", "description", "rate", "tax_amount"],
#         )
#         for tax in invoice_taxes:
#             tax_key = (tax["account_head"], tax["charge_type"])
#             if tax_key in tax_dict:
#                 tax_dict[tax_key]["tax_amount"] += tax["tax_amount"]
#             else:
#                 tax_dict[tax_key] = tax.copy()

#     for tax in tax_dict.values():
#         new_invoice.append("taxes", tax)

#     # Set classification codes explicitly again
#     for row in new_invoice.items:
#         row.custom_item_classification_codes = "004:Consolidated e-Invoice"

#     new_invoice.insert()
#     if new_invoice.get("custom_is_consolidated_invoice"):
#         new_invoice.db_set("status", "Consolidated")
#         new_invoice.db_set("outstanding_amount", 0.0)
#     new_invoice.flags.ignore_accounting_impact = True
#     new_invoice.submit()
#     if new_invoice.get("custom_is_consolidated_invoice"):
#         new_invoice.db_set("status", "Consolidated")
#         new_invoice.db_set("outstanding_amount", 0.0)

#     # Update original invoices with reference to the new one
#     for inv in sales_invoices:
#         doc = frappe.get_doc("Sales Invoice", inv["name"])
#         doc.custom_consolidate_invoice_number = new_invoice.name
#         doc.save(ignore_permissions=True)

#     # Create separate invoices for excluded items
#     excluded_items_messages = []
#     for entry in excluded_items_map:
#         inv = entry["invoice"]
#         item = entry["item"]

#         original_taxes = frappe.get_all(
#             "Sales Taxes and Charges",
#             filters={"parent": inv["name"]},
#             fields=["charge_type", "account_head", "description", "rate", "tax_amount"],
#         )

#         new_single_invoice = frappe.get_doc(
#             {
#                 "doctype": "Sales Invoice",
#                 "customer": inv["customer"],
#                 "customer_name": inv["customer_name"],
#                 "company": inv["company"],
#                 "currency": inv["currency"],
#                 "conversion_rate": inv["conversion_rate"],
#                 "posting_date": inv["posting_date"],
#                 "due_date": inv["due_date"],
#                 "customer_group": inv["customer_group"],
#                 "territory": inv["territory"],
#                 "is_pos": inv["is_pos"],
#                 "debit_to": inv["debit_to"],
#                 "is_return": 0,
#                 # "custom_is_consolidated_invoice":1,
#                 "custom_is_submit_to_lhdn": 1,
#                 "items": [
#                     {
#                         "item_code": item["item_code"],
#                         "item_name": item["item_name"],
#                         "description": item["description"],
#                         "qty": item["qty"],
#                         "rate": item["rate"],
#                         "amount": item["amount"],
#                         "income_account": item["income_account"],
#                         "cost_center": item["cost_center"],
#                         "custom_item_classification_codes": item.get(
#                             "custom_item_classification_codes", ""
#                         ),
#                         "consolidated_invoice_reference": inv["name"],
#                     }
#                 ],
#                 "remarks": f"Auto-created from item exceeding 10,000 in invoice {inv['name']}",
#                 "custom_submission_time": datetime.datetime.now(
#                     datetime.timezone.utc
#                 ).strftime("%Y-%m-%dT%H:%M:%SZ"),
#             }
#         )

#         for tax in original_taxes:
#             new_single_invoice.append(
#                 "taxes",
#                 {
#                     "charge_type": tax["charge_type"],
#                     "account_head": tax["account_head"],
#                     "description": tax["description"],
#                     "rate": tax["rate"],
#                     "tax_amount": tax["tax_amount"],
#                 },
#             )

#         new_single_invoice.insert()
#         new_single_invoice.submit()

#         excluded_items_messages.append(
#             f"{item['item_code']} (Amount: {item['amount']}) from Invoice: {inv['name']} "
#             f"moved to new invoice: {new_single_invoice.name}"
#         )

#     if excluded_items_messages:
#         frappe.msgprint(
#             _(
#                 "The following items were excluded from the consolidated invoice because their amount exceeded 10,000. "
#                 "Individual invoices were created:"
#             )
#             + "<br>"
#             + "<br>".join(excluded_items_messages),
#             title=_("Excluded Items"),
#             indicator="orange",
#         )

#     return new_invoice.name



@frappe.whitelist(allow_guest=False)
def merge_sales_invoices(invoice_numbers):
    """
    Merge multiple Sales Invoices into a single consolidated invoice.
    Excludes items where amount > 10,000.
    Creates separate invoices for such items, preserving original customer and tax details.
    """

    import datetime

    if isinstance(invoice_numbers, str):
        invoice_numbers = frappe.parse_json(invoice_numbers)

    if not invoice_numbers or len(invoice_numbers) < 2:
        frappe.throw(_("Please select at least two Sales Invoices to merge."))

    all_invoices = frappe.get_all(
        "Sales Invoice",
        filters={"name": ["in", invoice_numbers]},
        fields=[
            "name",
            "customer",
            "company",
            "currency",
            "conversion_rate",
            "posting_date",
            "due_date",
            "customer_name",
            "customer_group",
            "territory",
            "is_pos",
            "debit_to",
            "docstatus",
            "custom_consolidate_invoice_number",
        ],
    )

    if not all_invoices:
        frappe.throw(_("No valid Sales Invoices found."))

    not_submitted = [inv["name"] for inv in all_invoices if inv["docstatus"] != 1]
    if not_submitted:
        frappe.throw(
            _("Only submitted Sales Invoices can be merged:")
            + "<br>"
            + "<br>".join(not_submitted)
        )

    already_consolidated = [
        inv["name"]
        for inv in all_invoices
        if inv.get("custom_consolidate_invoice_number")
    ]
    if already_consolidated:
        frappe.throw(
            _(
                "The following invoices are already consolidated and cannot be merged again:"
            )
            + "<br>"
            + "<br>".join(already_consolidated)
        )

    sales_invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "name": ["in", invoice_numbers],
            "docstatus": 1,
            "custom_consolidate_invoice_number": ["is", "not set"],
        },
        fields=[
            "name",
            "customer",
            "company",
            "currency",
            "conversion_rate",
            "posting_date",
            "due_date",
            "customer_name",
            "customer_group",
            "territory",
            "is_pos",
            "debit_to",
            "docstatus",
        ],
    )

    base_invoice = sales_invoices[0]

    # Create the consolidated e-Invoice.
    #
    # This is a Consolidated e-Invoice, not a Sales Invoice: the revenue on
    # every line is already booked on the source invoices, so an accounting
    # document here would count it twice. Its own doctype has no ledger impact
    # at all, which lets docstatus 1 mean "reported to LHDN" and nothing else,
    # while staying visible to the LHDN reports and the form UI.
    general_public_customer = get_general_public_customer()
    new_invoice = frappe.get_doc(
        {
            "doctype": CONSOLIDATED_DOCTYPE,
            "customer": general_public_customer,
            "company": base_invoice["company"],
            "currency": base_invoice["currency"],
            "conversion_rate": base_invoice["conversion_rate"] or 1,
            "posting_date": min([inv["posting_date"] for inv in sales_invoices]),
            "due_date": max([inv["due_date"] for inv in sales_invoices]),
            "from_date": min([inv["posting_date"] for inv in sales_invoices]),
            "to_date": max([inv["posting_date"] for inv in sales_invoices]),
            "is_return": 0,
            "custom_is_submit_to_lhdn": 1,
            "custom_is_consolidated_invoice": 1,
            "items": [],
            "taxes": [],
            "custom_submission_time": datetime.datetime.now(
                datetime.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )

    item_dict = {}
    excluded_items_map = []

    for inv in sales_invoices:
        invoice_items = frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": inv["name"]},
            fields=[
                "item_code",
                "item_name",
                "description",
                "qty",
                "rate",
                "amount",
                "income_account",
                "cost_center",
                "custom_item_classification_codes",
            ],
        )
        for item in invoice_items:
            if item["amount"] > 10000:
                excluded_items_map.append({"invoice": inv, "item": item})
                continue

            # Keep items separate per invoice
            item_key = (item["item_code"], item["rate"], inv["name"])

            new_item = item.copy()
            new_item["custom_item_classification_codes"] = "004:Consolidated e-Invoice"
            new_item["custom_consolidated_invoice_refrence_copy"] = inv["name"]
            item_dict[item_key] = new_item

    if not item_dict:
        frappe.throw(
            _(
                "All items were excluded because their amount exceeded 10,000. Consolidated invoice not created."
            )
        )

    for item in item_dict.values():
        new_invoice.append("items", item)

    # Consolidate taxes
    tax_dict = {}
    for inv in sales_invoices:
        invoice_taxes = frappe.get_all(
            "Sales Taxes and Charges",
            filters={"parent": inv["name"]},
            fields=["charge_type", "account_head", "description", "rate", "tax_amount"],
        )
        for tax in invoice_taxes:
            tax_key = (tax["account_head"], tax["charge_type"])
            if tax_key in tax_dict:
                tax_dict[tax_key]["tax_amount"] += tax["tax_amount"]
            else:
                tax_dict[tax_key] = tax.copy()

    for tax in tax_dict.values():
        new_invoice.append("taxes", tax)

    # Classification code enforcement
    for row in new_invoice.items:
        row.custom_item_classification_codes = "004:Consolidated e-Invoice"

    new_invoice.insert()

    # Submitting the Consolidated e-Invoice reports it to LHDN via its own
    # on_submit. No GL entries are produced - it is not an accounting doctype.
    try:
        new_invoice.submit()
    except Exception as e:
        frappe.throw(_("Error submitting consolidated e-Invoice: {0}").format(str(e)))

    # Point each source invoice at the consolidated document. db_set is used
    # rather than save() so a submitted invoice can be stamped without amending
    # it - the field is no_copy metadata, not part of the accounting entry.
    for inv in sales_invoices:
        frappe.db.set_value(
            "Sales Invoice", inv["name"],
            "custom_consolidate_invoice_number", new_invoice.name,
            update_modified=False,
        )

    # Handle excluded items
    #
    # Lines over 10,000 cannot be consolidated, so each is reported to LHDN on
    # its own. These stay Sales Invoices because they keep the real buyer, but
    # they are left as drafts: the revenue is already booked on the source
    # invoice, so submitting them would post it a second time.
    from myinvois_erpgulf.myinvois_erpgulf.original import (
        submit_document,
        validate_before,
    )

    excluded_items_messages = []
    for entry in excluded_items_map:
        inv = entry["invoice"]
        item = entry["item"]

        original_taxes = frappe.get_all(
            "Sales Taxes and Charges",
            filters={"parent": inv["name"]},
            fields=["charge_type", "account_head", "description", "rate", "tax_amount"],
        )

        new_single_invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "customer": inv["customer"],
                "customer_name": inv["customer_name"],
                "company": inv["company"],
                "currency": inv["currency"],
                "conversion_rate": inv["conversion_rate"],
                "posting_date": inv["posting_date"],
                "due_date": inv["due_date"],
                "customer_group": inv["customer_group"],
                "territory": inv["territory"],
                "is_pos": inv["is_pos"],
                "debit_to": inv["debit_to"]
                or frappe.get_cached_value(
                    "Company", inv["company"], "default_receivable_account"
                ),
                "is_return": 0,
                "custom_is_submit_to_lhdn": 1,
                "items": [
                    {
                        "item_code": item["item_code"],
                        "item_name": item["item_name"],
                        "description": item["description"],
                        "qty": item["qty"],
                        "rate": item["rate"],
                        "amount": item["amount"],
                        "income_account": item["income_account"],
                        "cost_center": item["cost_center"],
                        "custom_item_classification_codes": item.get(
                            "custom_item_classification_codes", ""
                        ),
                        "consolidated_invoice_reference": inv["name"],
                    }
                ],
                "remarks": f"Auto-created from item exceeding 10,000 in invoice {inv['name']}",
                "custom_submission_time": datetime.datetime.now(
                    datetime.timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

        for tax in original_taxes:
            new_single_invoice.append(
                "taxes",
                {
                    "charge_type": tax["charge_type"],
                    "account_head": tax["account_head"],
                    "description": tax["description"],
                    "rate": tax["rate"],
                    "tax_amount": tax["tax_amount"],
                },
            )

        # Same reasoning as the consolidated invoice above: this document only
        # carries an over-10,000 line to LHDN, and that revenue is already
        # booked on the source invoice. Left as a draft so no second set of GL
        # entries is posted, and submitted to LHDN directly.
        new_single_invoice.insert()
        try:
            validate_before(new_single_invoice.name)
            submit_document(new_single_invoice.name)
        except Exception as e:
            frappe.throw(
                _("Error submitting e-Invoice for excluded item: {0}").format(str(e))
            )

        excluded_items_messages.append(
            f"{item['item_code']} (Amount: {item['amount']}) from Invoice: {inv['name']} "
            f"moved to new invoice: {new_single_invoice.name}"
        )

    if excluded_items_messages:
        frappe.msgprint(
            _(
                "The following items were excluded from the consolidated invoice because their amount exceeded 10,000. "
                "Individual invoices were created:"
            )
            + "<br>"
            + "<br>".join(excluded_items_messages),
            title=_("Excluded Items"),
            indicator="orange",
        )

    return new_invoice.name
