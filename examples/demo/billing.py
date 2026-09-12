"""Pricing for a small order system.

This module is deliberately imperfect. See ../README.md.
"""

from __future__ import annotations

from decimal import Decimal

TIERS = {"free": 0, "basic": 5, "pro": 15, "enterprise": 40}
VAT = {"GB": Decimal("0.20"), "DE": Decimal("0.19"), "FR": Decimal("0.20")}


def apply_pricing(order, customer, coupon=None, currency="GBP", region="GB"):
    """Work out what an order costs, all in one place."""
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

    tier = customer.get("tier", "free")
    if tier == "enterprise":
        subtotal = subtotal * Decimal("0.8")
    elif tier == "pro":
        subtotal = subtotal * Decimal("0.9")
    elif tier == "basic":
        subtotal = subtotal * Decimal("0.95")

    if coupon:
        if coupon["kind"] == "percent":
            if coupon["value"] > 50 and tier not in ("pro", "enterprise"):
                discount = subtotal * Decimal("0.5")
            else:
                discount = subtotal * (Decimal(str(coupon["value"])) / 100)
        elif coupon["kind"] == "fixed":
            discount = min(Decimal(str(coupon["value"])), subtotal)
        elif coupon["kind"] == "shipping":
            discount = Decimal("0")
        else:
            discount = Decimal("0")
        if coupon.get("minimum") and subtotal < Decimal(str(coupon["minimum"])):
            discount = Decimal("0")
        subtotal -= discount

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

    total = taxable + tax
    if currency == "USD":
        total = total * Decimal("1.27")
    elif currency == "EUR":
        total = total * Decimal("1.17")

    if total < 0:
        total = Decimal("0")
    return {
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": total.quantize(Decimal("0.01")),
        "currency": currency,
    }


def monthly_fee(customer):
    """The recurring charge for a customer's tier."""
    return Decimal(str(TIERS.get(customer.get("tier", "free"), 0)))
