from __future__ import annotations

from typing import Any


# ============================================================
# PURCHASE ORDER DATA
# ============================================================

PURCHASE_ORDERS: list[dict[str, Any]] = [
    {
        "po_number": "PO-1001",
        "vendor": "ABC Suppliers",
        "category": "Raw Materials",
        "amount": 125000,
        "status": "Approved",
        "date": "2026-08-18",
        "delivery_date": "2026-08-28",
        "department": "Production",
    },
    {
        "po_number": "PO-1002",
        "vendor": "XYZ Industries",
        "category": "Electronics",
        "amount": 85000,
        "status": "Pending",
        "date": "2026-08-19",
        "delivery_date": "2026-08-30",
        "department": "IT",
    },
    {
        "po_number": "PO-1003",
        "vendor": "Global Tech",
        "category": "IT Equipment",
        "amount": 210000,
        "status": "Approved",
        "date": "2026-08-20",
        "delivery_date": "2026-09-02",
        "department": "IT",
    },
    {
        "po_number": "PO-1004",
        "vendor": "Prime Logistics",
        "category": "Logistics",
        "amount": 72000,
        "status": "Pending",
        "date": "2026-08-20",
        "delivery_date": "2026-08-27",
        "department": "Operations",
    },
    {
        "po_number": "PO-1005",
        "vendor": "ABC Suppliers",
        "category": "Packaging",
        "amount": 54000,
        "status": "Approved",
        "date": "2026-08-21",
        "delivery_date": "2026-08-29",
        "department": "Production",
    },
    {
        "po_number": "PO-1006",
        "vendor": "Metro Office",
        "category": "Office Supplies",
        "amount": 32000,
        "status": "Rejected",
        "date": "2026-08-21",
        "delivery_date": "2026-08-26",
        "department": "Administration",
    },
    {
        "po_number": "PO-1007",
        "vendor": "Global Tech",
        "category": "Software",
        "amount": 145000,
        "status": "Pending",
        "date": "2026-08-22",
        "delivery_date": "2026-09-05",
        "department": "IT",
    },
]


# ============================================================
# GET PURCHASE ORDERS
# ============================================================

def get_purchase_orders(
    status: str | None = None,
) -> list[dict[str, Any]]:

    # --------------------------------------------------------
    # Return everything
    # --------------------------------------------------------

    if not status:

        return [
            order.copy()
            for order in PURCHASE_ORDERS
        ]

    # --------------------------------------------------------
    # Filter by status
    # --------------------------------------------------------

    normalized_status = (
        status.strip().lower()
    )

    return [
        order.copy()
        for order in PURCHASE_ORDERS
        if str(
            order.get("status", "")
        ).strip().lower()
        == normalized_status
    ]