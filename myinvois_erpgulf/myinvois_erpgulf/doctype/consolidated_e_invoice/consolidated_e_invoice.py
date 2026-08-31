# Copyright (c) 2026, ERPGulf and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from myinvois_erpgulf.myinvois_erpgulf.createxml import dec, money

from myinvois_erpgulf.myinvois_erpgulf.consolidate_invoice import (
    GENERAL_PUBLIC_NAME,
    is_consolidated_buyer,
)

DOCTYPE = "Consolidated e-Invoice"


def to_float(value):
    """Round an exact decimal to 2 places for storage in a Currency field."""
    return float(money(value))


class ConsolidatedeInvoice(Document):
    """A consolidated e-Invoice reported to LHDN.

    This is deliberately *not* an accounting document. The revenue on every
    line is already booked on the source Sales Invoice, so posting anything
    here would count it twice. Keeping it in its own doctype - rather than as a
    Sales Invoice that has to be prevented from reaching the ledger - means
    docstatus 1 can mean "reported to LHDN" and nothing else.
    """

    def validate(self):
        self.set_missing_values()
        self.calculate_totals()
        self.validate_buyer()

    def set_missing_values(self):
        if not self.currency:
            self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
        if not self.conversion_rate:
            self.conversion_rate = 1
        self.custom_is_consolidated_invoice = 1

    def calculate_totals(self):
        """Total the lines in Decimal, then store.

        These figures end up in a tax document, so the arithmetic is done on
        exact decimals rather than binary floats - summing floats drifts, and
        333.30 - 0 lands on 333.29999999999995.
        """
        rate = dec(self.conversion_rate or 1)
        # The XML builders read discount_amount with Document.get(key, default),
        # which returns None for a field that exists but was never set - a
        # Sales Invoice is always initialised to 0, so keep parity here.
        discount = dec(self.discount_amount)
        self.discount_amount = to_float(discount)

        total = dec(0)
        for row in self.items:
            row.discount_amount = to_float(dec(row.discount_amount))
            amount = dec(row.qty) * dec(row.rate)
            row.amount = to_float(amount)
            row.base_rate = to_float(dec(row.rate) * rate)
            row.base_amount = to_float(amount * rate)
            # The line builders take abs() of this directly, so it must never
            # be None. With no price list in play it equals the base rate.
            row.base_price_list_rate = row.base_price_list_rate or row.base_rate
            total += amount

        tax_total = sum((dec(t.tax_amount) for t in (self.taxes or [])), dec(0))
        grand_total = total - discount + tax_total

        self.total = to_float(total)
        self.net_total = self.total
        self.base_total = to_float(total * rate)
        self.grand_total = to_float(grand_total)
        self.base_grand_total = to_float(grand_total * rate)
        self.base_discount_amount = to_float(discount * rate)

    def validate_buyer(self):
        """The buyer must resolve to the Appendix 2 General Public block.

        LHDN only accepts the general TIN with BRN/NRIC "NA" on a consolidated
        document, so a buyer that would be sent with real details is refused
        here rather than rejected after submission.
        """
        if not self.customer:
            return
        customer_doc = frappe.get_doc("Customer", self.customer)
        # Pass an empty doc as the invoice: this doctype always carries the
        # consolidated flag, which would short-circuit the check and let any
        # customer through. Only the Customer record should decide here.
        if not is_consolidated_buyer(frappe._dict(), customer_doc):
            frappe.throw(
                _(
                    "Customer {0} is not a {1} buyer. Set its e-Invoice Buyer Type"
                    " to '{1}', or pick the {1} account - LHDN only accepts a"
                    " consolidated e-Invoice with the general public buyer details."
                ).format(self.customer, GENERAL_PUBLIC_NAME)
            )

    def on_submit(self):
        """Report to LHDN. No GL entries - this doctype has no ledger impact."""
        if not self.custom_is_submit_to_lhdn:
            return

        settings = frappe.get_doc("Company", self.company)
        if not settings.custom_enable_lhdn_invoice:
            frappe.throw(_("LHDN Invoice Submission is not enabled for {0}").format(self.company))

        from myinvois_erpgulf.myinvois_erpgulf.original import (
            submit_document,
            validate_before,
        )

        validate_before(self.name, doctype=DOCTYPE)
        submit_document(self.name, doctype=DOCTYPE)

    def on_cancel(self):
        """Cancelling here only withdraws the ERP record.

        LHDN has its own cancellation window and rules; a document already
        accepted there is not undone by cancelling this one.
        """
        if (self.custom_lhdn_status or "").strip().lower() == "valid":
            frappe.msgprint(
                _(
                    "{0} was accepted by LHDN. Cancelling here does not cancel it at"
                    " LHDN - do that in MyInvois within the allowed window, or issue"
                    " a credit note."
                ).format(self.name),
                indicator="orange",
                title=_("Not cancelled at LHDN"),
            )
