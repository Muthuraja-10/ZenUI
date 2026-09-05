from __future__ import annotations

from typing import Any


# ============================================================
# CUSTOMER DATA
# ============================================================

CUSTOMERS: list[dict[str, Any]] = [
    {
        "customer_id": "CUS-001",
        "name": "ABC Technologies",
        "segment": "Enterprise",
        "region": "South",
        "revenue": 850000,
        "status": "Active",
    },
    {
        "customer_id": "CUS-002",
        "name": "Bright Solutions",
        "segment": "SMB",
        "region": "North",
        "revenue": 320000,
        "status": "Active",
    },
    {
        "customer_id": "CUS-003",
        "name": "Nova Systems",
        "segment": "Startup",
        "region": "West",
        "revenue": 180000,
        "status": "Active",
    },
    {
        "customer_id": "CUS-004",
        "name": "Global Industries",
        "segment": "Enterprise",
        "region": "South",
        "revenue": 920000,
        "status": "Active",
    },
    {
        "customer_id": "CUS-005",
        "name": "NextGen Labs",
        "segment": "Startup",
        "region": "East",
        "revenue": 240000,
        "status": "Inactive",
    },
]


# ============================================================
# GET CUSTOMERS
# ============================================================

def get_customers(
    segment: str | None = None,
) -> list[dict[str, Any]]:

    if not segment:
        return CUSTOMERS.copy()

    normalized_segment = segment.strip().lower()

    return [
        customer
        for customer in CUSTOMERS
        if str(
            customer.get("segment", "")
        ).lower()
        == normalized_segment
    ]