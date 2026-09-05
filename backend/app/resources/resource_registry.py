from __future__ import annotations

from typing import Any, Callable

from app.resources.data.sales import get_sales
from app.resources.data.purchase_order import (
    get_purchase_orders,
)
from app.resources.data.employees import (
    get_employees,
)
from app.resources.data.customers import (
    get_customers,
)


# ============================================================
# RESOURCE FUNCTION
# ============================================================

ResourceFunction = Callable[
    ...,
    list[dict[str, Any]],
]


# ============================================================
# RESOURCE REGISTRY
# ============================================================

RESOURCE_REGISTRY: dict[
    str,
    ResourceFunction,
] = {
    "sales": get_sales,
    "purchase_orders": get_purchase_orders,
    "employees": get_employees,
    "customers": get_customers,
}


# ============================================================
# RESOURCE ALIASES
# ============================================================

RESOURCE_ALIASES: dict[
    str,
    str,
] = {
    "sale": "sales",
    "sales_data": "sales",

    "purchase_order": "purchase_orders",
    "purchase_orders": "purchase_orders",
    "po": "purchase_orders",

    "employee": "employees",
    "employees": "employees",

    "customer": "customers",
    "customers": "customers",
}


# ============================================================
# NORMALIZE RESOURCE
# ============================================================

def normalize_resource(
    resource_name: str,
) -> str:

    normalized = (
        resource_name or ""
    ).strip().lower()

    if not normalized:
        raise ValueError(
            "Resource name cannot be empty."
        )

    return RESOURCE_ALIASES.get(
        normalized,
        normalized,
    )


# ============================================================
# GET RESOURCE
# ============================================================

def get_resource(
    resource_name: str,
) -> ResourceFunction:

    normalized = normalize_resource(
        resource_name
    )

    if normalized not in RESOURCE_REGISTRY:

        raise ValueError(
            f"Unknown resource: {resource_name}"
        )

    return RESOURCE_REGISTRY[
        normalized
    ]


# ============================================================
# LIST RESOURCES
# ============================================================

def list_resources() -> list[str]:

    return list(
        RESOURCE_REGISTRY.keys()
    )