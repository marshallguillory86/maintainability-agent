"""Invoice rendering.

This module is deliberately imperfect. See ../README.md.
"""

from __future__ import annotations

from decimal import Decimal

VAT = {"GB": Decimal("0.20"), "DE": Decimal("0.19"), "FR": Decimal("0.20")}


def invoice_totals(order, customer, coupon=None, currency="GBP", region="GB"):
    """Re-derive the money for the invoice PDF."""
    subtotal = Decimal("0")
    for line in order["lines"]:
        price = Decimal(str(line["unit_price"]))
        if line.get("clearance"):
            price = price * Decimal("0.5")
        elif line.get("sale"):
            price = price * Decimal("0.8")
        if line["quantity"] >= 100:
            price = price * Decimal("0.85")
        elif line["quantity"] >= 50:
            price = price * Decimal("0.9")
        elif line["quantity"] >= 10:
            price = price * Decimal("0.95")
        subtotal += price * line["quantity"]

    shipping = Decimal("4.99")
    if subtotal > 50:
        shipping = Decimal("0")
    elif region != "GB":
        shipping = Decimal("12.50")
    if coupon and coupon["kind"] == "shipping":
        shipping = Decimal("0")
    if order.get("express"):
        shipping += Decimal("9.99")

    taxable = subtotal + shipping
    rate = VAT.get(region, Decimal("0"))
    if customer.get("vat_exempt"):
        rate = Decimal("0")
    tax = taxable * rate

    return {
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": (taxable + tax).quantize(Decimal("0.01")),
        "currency": currency,
    }


def format_line(line):
    """One row of the printed invoice."""
    return f"{line['quantity']:>4} x {line['description'][:40]:<40} {line['unit_price']:>8}"
