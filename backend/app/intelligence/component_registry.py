from __future__ import annotations

from typing import Any


# ============================================================
# ZENUI COMPONENT REGISTRY
# ============================================================
#
# This is ZenUI's internal component vocabulary.
#
# IMPORTANT:
#
# ZenUI components are NOT OpenUI components.
#
# Example:
#
#     ZenUI "kpi"
#          ↓
#     OpenUI "StatCard"
#
#     ZenUI "line_chart"
#          ↓
#     OpenUI "LineChart"
#
# This keeps our architecture independent from the renderer.
# ============================================================


COMPONENT_REGISTRY: dict[str, dict[str, Any]] = {

    # ========================================================
    # CONTENT
    # ========================================================

    "text": {
        "category": "content",
        "description": "Normal text content",
    },

    "heading": {
        "category": "content",
        "description": "Section or page heading",
    },

    "card": {
        "category": "content",
        "description": "Visual content card",
    },

    # ========================================================
    # DATA
    # ========================================================

    "kpi": {
        "category": "data",
        "description": "Key performance indicator or metric",
    },

    "table": {
        "category": "data",
        "description": "Tabular data",
    },

    # ========================================================
    # CHARTS
    # ========================================================

    "bar_chart": {
        "category": "chart",
        "description": "Bar chart for category comparison",
    },

    "line_chart": {
        "category": "chart",
        "description": "Line chart for trends over time",
    },

    "pie_chart": {
        "category": "chart",
        "description": "Pie or donut chart for proportions",
    },

    # ========================================================
    # FORMS
    # ========================================================

    "form": {
        "category": "form",
        "description": "Form container",
    },

    "input": {
        "category": "form",
        "description": "Text or numeric input",
    },

    "select": {
        "category": "form",
        "description": "Selection input",
    },

    "button": {
        "category": "form",
        "description": "Action button",
    },

    # ========================================================
    # UI
    # ========================================================

    "badge": {
        "category": "ui",
        "description": "Small status/category badge",
    },

    "tabs": {
        "category": "ui",
        "description": "Tabbed interface",
    },

    "grid": {
        "category": "layout",
        "description": "Grid layout",
    },

    "stack": {
        "category": "layout",
        "description": "Stack layout",
    },

    "alert": {
        "category": "ui",
        "description": "Alert or notification",
    },

    "progress": {
        "category": "ui",
        "description": "Progress indicator",
    },
}


def is_supported_component(
    component_type: str,
) -> bool:

    return (
        str(component_type or "").strip().lower()
        in COMPONENT_REGISTRY
    )


def get_component_definition(
    component_type: str,
) -> dict[str, Any]:

    return COMPONENT_REGISTRY.get(
        str(component_type or "").strip().lower(),
        {},
    )


def supported_components() -> list[str]:

    return list(
        COMPONENT_REGISTRY.keys()
    )


def component_categories() -> dict[str, list[str]]:

    result: dict[str, list[str]] = {}

    for name, definition in COMPONENT_REGISTRY.items():

        category = definition.get(
            "category",
            "other",
        )

        result.setdefault(
            category,
            [],
        ).append(name)

    return result