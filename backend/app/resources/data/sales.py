from __future__ import annotations

from typing import Any


SALES_DATA: list[dict[str, Any]] = [

    {
        "month": "March",
        "region": "South",
        "sales": 1200000,
    },

    {
        "month": "April",
        "region": "South",
        "sales": 1350000,
    },

    {
        "month": "May",
        "region": "South",
        "sales": 820000,
    },

    {
        "month": "June",
        "region": "South",
        "sales": 910000,
    },

    {
        "month": "July",
        "region": "South",
        "sales": 1080000,
    },

    {
        "month": "August",
        "region": "South",
        "sales": 1240000,
    },
]


def get_sales(
    time_range: str | None = None,
) -> list[dict[str, Any]]:

    if not time_range:

        return SALES_DATA.copy()

    normalized = (
        time_range
        .strip()
        .lower()
    )

    if normalized == "last_6_months":

        return SALES_DATA[-6:].copy()

    if normalized == "last_3_months":

        return SALES_DATA[-3:].copy()

    return SALES_DATA.copy()