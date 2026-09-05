from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from app.intelligence.ui_modification import (
    UIModification,
)


class UIPlanModifier:
    """
    Applies a single targeted conversational modification
    to an existing ZenUI UIPlan.

    IMPORTANT:

    This class NEVER mutates the caller's original plan.

    It always works on a deep copy.

    If the requested operation cannot be applied safely,
    it returns None.
    """

    # ========================================================
    # PUBLIC
    # ========================================================

    def modify(
        self,
        ui_plan: dict[str, Any],
        modification: UIModification,
        resource_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:

        if not modification.is_modification:
            return None

        if not isinstance(ui_plan, dict):
            return None

        plan = deepcopy(ui_plan)

        resource_data = (
            resource_data
            if isinstance(resource_data, dict)
            else {}
        )

        changed = False

        action = (
            modification.action
            or ""
        ).strip().lower()

        # ====================================================
        # REMOVE COLUMN
        # ====================================================

        if action == "remove_column":

            changed = self._remove_column(
                plan,
                modification.target,
            )

        elif action == "rename_column":

            changed = self._rename_column(
                plan,
                modification.target,
                modification.value,
            )

        elif action == "update_title":

            changed = self._update_title(
                plan,
                modification.value,
            )

        # ====================================================
        # ADD COLUMN
        # ====================================================

        elif action == "add_column":

            changed = self._add_column(
                plan,
                modification.target,
            )

        # ====================================================
        # FILTER TABLE
        # ====================================================

        elif action == "filter_table":

            changed = self._filter_tables(
                plan,
                modification.value,
            )

        elif action == "sort_table":

            changed = self._sort_tables(
                plan,
                modification.target,
                modification.value,
            )

        # ====================================================
        # ADD CHART
        # ====================================================

        elif action == "add_chart":

            changed = self._add_chart(
                plan,
                modification.target,
            )

        # ====================================================
        # REMOVE CHART
        # ====================================================

        elif action == "remove_chart":

            changed = self._remove_chart(
                plan,
                modification.target,
            )

        # ====================================================
        # REPLACE CHART
        # ====================================================

        elif action == "replace_chart":

            changed = self._replace_chart(
                plan,
                old_type=modification.value,
                new_type=modification.target,
            )

        # ====================================================
        # KPI
        # ====================================================

        elif action == "add_kpis":

            changed = self._add_kpis(
                plan,
                resource_data,
            )

        # ====================================================
        # CRUD
        # ====================================================

        elif action == "add_crud":

            changed = self._add_crud_actions(
                plan,
                actions={
                    "create",
                    "edit",
                    "delete",
                },
            )

        elif action == "add_crud_actions":

            requested = {
                item.strip().lower()
                for item in str(
                    modification.value or ""
                ).split(",")
                if item.strip()
            }

            changed = self._add_crud_actions(
                plan,
                actions=requested,
            )

        # ====================================================
        # FORM
        # ====================================================

        elif action == "add_form":

            changed = self._add_generic_form(
                plan
            )

        # ====================================================
        # UNKNOWN
        # ====================================================

        else:

            return None

        if not changed:
            return None

        self._ensure_integrity(
            plan
        )

        plan.setdefault(
            "metadata",
            {},
        ).update(
            {
                "refined": True,
                "modification": action,
            }
        )

        return plan

    # ========================================================
    # REMOVE COLUMN
    # ========================================================

    def _remove_column(
        self,
        plan: dict[str, Any],
        target: str | None,
    ) -> bool:

        target_normalized = self._normalize(
            target
        )

        if not target_normalized:
            return False

        changed = False

        for component in self._components(
            plan
        ):

            if component.get(
                "type"
            ) != "table":
                continue

            props = component.setdefault(
                "props",
                {},
            )

            columns = props.get(
                "columns",
                [],
            )

            if not isinstance(
                columns,
                list,
            ):
                continue

            remove_keys: set[str] = set()

            for column in columns:

                if not isinstance(
                    column,
                    dict,
                ):
                    continue

                key = self._normalize(
                    column.get(
                        "key"
                    )
                )

                label = self._normalize(
                    column.get(
                        "label"
                    )
                )

                if (
                    key == target_normalized
                    or label == target_normalized
                    or target_normalized in key
                    or target_normalized in label
                ):

                    if key:
                        remove_keys.add(
                            key
                        )

            if not remove_keys:
                continue

            props["columns"] = [
                column
                for column in columns
                if self._normalize(
                    column.get("key")
                )
                not in remove_keys
            ]

            rows = props.get(
                "rows",
                [],
            )

            if isinstance(
                rows,
                list,
            ):

                for row in rows:

                    if not isinstance(
                        row,
                        dict,
                    ):
                        continue

                    for key in list(
                        row.keys()
                    ):

                        if (
                            self._normalize(key)
                            in remove_keys
                        ):
                            row.pop(
                                key,
                                None,
                            )

            changed = True

        return changed

    # ========================================================
    # ADD COLUMN
    # ========================================================

    def _rename_column(
        self,
        plan: dict[str, Any],
        old_target: str | None,
        new_target: str | None,
    ) -> bool:

        old_normalized = self._normalize(old_target)
        new_label = str(new_target or "").strip()

        if not old_normalized or not new_label:
            return False

        new_key = self._safe_key(new_label)
        changed = False

        for component in self._components(plan):

            if component.get("type") != "table":
                continue

            props = component.setdefault("props", {})
            columns = props.get("columns", [])

            if not isinstance(columns, list):
                continue

            for column in columns:

                if not isinstance(column, dict):
                    continue

                key = self._normalize(column.get("key"))
                label = self._normalize(column.get("label"))

                if old_normalized not in {key, label}:
                    continue

                old_key = str(column.get("key", ""))
                column["key"] = new_key
                column["label"] = new_label.title()

                rows = props.get("rows", [])

                if isinstance(rows, list):
                    for row in rows:
                        if isinstance(row, dict) and old_key in row:
                            row[new_key] = row.pop(old_key)

                changed = True

        return changed

    def _update_title(
        self,
        plan: dict[str, Any],
        value: str | None,
    ) -> bool:

        title = str(value or "").strip()

        if not title:
            return False

        for component in self._components(plan):
            if component.get("type") == "heading":
                component.setdefault("props", {})["text"] = title
                return True

        return False

    def _add_column(
        self,
        plan: dict[str, Any],
        target: str | None,
    ) -> bool:

        label = str(
            target or ""
        ).strip()

        if not label:
            return False

        key = self._safe_key(
            label
        )

        changed = False

        for component in self._components(
            plan
        ):

            if component.get(
                "type"
            ) != "table":
                continue

            props = component.setdefault(
                "props",
                {},
            )

            columns = props.setdefault(
                "columns",
                [],
            )

            if not isinstance(
                columns,
                list,
            ):
                continue

            existing_keys = {
                self._safe_key(
                    str(
                        column.get(
                            "key",
                            "",
                        )
                    )
                )
                for column in columns
                if isinstance(
                    column,
                    dict,
                )
            }

            if key in existing_keys:
                continue

            columns.append(
                {
                    "key": key,
                    "label": label.title(),
                }
            )

            rows = props.setdefault(
                "rows",
                [],
            )

            if isinstance(
                rows,
                list,
            ):

                for row in rows:

                    if isinstance(
                        row,
                        dict,
                    ):

                        row.setdefault(
                            key,
                            "",
                        )

            changed = True

        return changed

    # ========================================================
    # FILTER
    # ========================================================

    def _filter_tables(
        self,
        plan: dict[str, Any],
        value: str | None,
    ) -> bool:

        target = self._normalize(
            value
        )

        if not target:
            return False

        changed = False

        for component in self._components(
            plan
        ):

            if component.get(
                "type"
            ) != "table":
                continue

            props = component.setdefault(
                "props",
                {},
            )

            rows = props.get(
                "rows",
                [],
            )

            if not isinstance(
                rows,
                list,
            ):
                continue

            filtered_rows = []

            for row in rows:

                if not isinstance(
                    row,
                    dict,
                ):
                    continue

                normalized_values = [
                    self._normalize(value)
                    for value in row.values()
                ]
                target_words = {
                    word
                    for word in target.split()
                    if word not in {
                        "order",
                        "orders",
                        "record",
                        "records",
                        "row",
                        "rows",
                    }
                }

                if any(
                    target == value
                    or target in value
                    or target_words.intersection(set(value.split()))
                    for value in normalized_values
                ):

                    filtered_rows.append(
                        row
                    )

            if filtered_rows != rows:

                props["rows"] = (
                    filtered_rows
                )

                changed = True

        return changed

    def _sort_tables(
        self,
        plan: dict[str, Any],
        target: str | None,
        direction: str | None,
    ) -> bool:

        target_normalized = self._normalize(target)

        if not target_normalized:
            return False

        descending = str(direction or "").lower() in {
            "highest",
            "descending",
            "desc",
        }
        changed = False

        for component in self._components(plan):

            if component.get("type") != "table":
                continue

            props = component.setdefault("props", {})
            rows = props.get("rows", [])

            if not isinstance(rows, list) or len(rows) < 2:
                continue

            key = None
            for column in props.get("columns", []):
                if not isinstance(column, dict):
                    continue
                if target_normalized in {
                    self._normalize(column.get("key")),
                    self._normalize(column.get("label")),
                }:
                    key = str(column.get("key"))
                    break

            if key is None:
                key = target_normalized.replace(" ", "_")

            before = list(rows)

            rows.sort(
                key=lambda row: self._number(row.get(key, 0)),
                reverse=descending,
            )

            if rows != before:
                changed = True

        return changed

    # ========================================================
    # ADD CHART
    # ========================================================

    def _add_chart(
        self,
        plan: dict[str, Any],
        chart_type: str | None,
    ) -> bool:

        chart_type = str(
            chart_type or ""
        ).strip().lower()

        if chart_type not in {
            "line_chart",
            "bar_chart",
            "pie_chart",
        }:
            return False

        components = self._components(
            plan
        )

        if any(
            component.get("type")
            == chart_type
            for component in components
        ):
            return False

        table = self._find_table(
            plan
        )

        if table is None:
            return False

        chart = self._build_chart(
            chart_type,
            table,
        )

        if chart is None:
            return False

        components.append(
            chart
        )

        self._append_root(
            plan,
            chart["id"],
        )

        return True

    # ========================================================
    # REMOVE CHART
    # ========================================================

    def _remove_chart(
        self,
        plan: dict[str, Any],
        chart_type: str | None,
    ) -> bool:

        chart_type = self._resolve_chart_type(
            plan,
            chart_type,
        )

        if chart_type not in {
            "line_chart",
            "bar_chart",
            "pie_chart",
        }:
            return False

        components = self._components(
            plan
        )

        original_count = len(
            components
        )

        components[:] = [
            component
            for component in components
            if component.get(
                "type"
            ) != chart_type
        ]

        if len(components) == original_count:
            return False

        root = plan.setdefault(
            "root_components",
            [],
        )

        root[:] = [
            item
            for item in root
            if item != chart_type
        ]

        return True

    # ========================================================
    # REPLACE CHART
    # ========================================================

    def _replace_chart(
        self,
        plan: dict[str, Any],
        old_type: str | None,
        new_type: str | None,
    ) -> bool:

        old_type = self._resolve_chart_type(
            plan,
            old_type,
        )

        new_type = str(
            new_type or ""
        ).strip().lower()

        if new_type == "bar":
            new_type = "bar_chart"
        elif new_type == "line":
            new_type = "line_chart"
        elif new_type == "pie":
            new_type = "pie_chart"

        if old_type not in {
            "line_chart",
            "bar_chart",
            "pie_chart",
        }:
            return False

        if new_type not in {
            "line_chart",
            "bar_chart",
            "pie_chart",
        }:
            return False

        changed = False

        for component in self._components(
            plan
        ):

            if component.get(
                "type"
            ) != old_type:
                continue

            component["type"] = new_type
            component["id"] = new_type

            changed = True

        if not changed:
            return False

        root = plan.setdefault(
            "root_components",
            [],
        )

        root[:] = [
            new_type
            if item == old_type
            else item
            for item in root
        ]

        return True

    # ========================================================
    # KPI
    # ========================================================

    def _add_kpis(
        self,
        plan: dict[str, Any],
        resource_data: dict[str, Any],
    ) -> bool:

        rows = self._find_rows(
            resource_data
        )

        if not rows:
            rows = self._rows_from_plan(
                plan
            )

        if not rows:
            return False

        numeric_key = self._find_numeric_key(
            rows
        )

        if not numeric_key:
            return False

        values = [
            self._number(
                row.get(
                    numeric_key
                )
            )
            for row in rows
        ]

        total = sum(
            values
        )

        average = (
            total / len(values)
            if values
            else 0
        )

        latest = (
            values[-1]
            if values
            else 0
        )

        existing_ids = {
            str(
                component.get(
                    "id",
                    "",
                )
            )
            for component
            in self._components(plan)
        }

        additions = [
            (
                "derived_total_kpi",
                f"Total {self._humanize(numeric_key)}",
                self._format_number(total),
            ),
            (
                "derived_latest_kpi",
                f"Latest {self._humanize(numeric_key)}",
                self._format_number(latest),
            ),
            (
                "derived_average_kpi",
                f"Average {self._humanize(numeric_key)}",
                self._format_number(average),
            ),
        ]

        changed = False

        for component_id, label, value in additions:

            if component_id in existing_ids:
                continue

            self._components(plan).append(
                {
                    "id": component_id,
                    "type": "kpi",
                    "props": {
                        "label": label,
                        "value": value,
                    },
                }
            )

            self._append_root(
                plan,
                component_id,
            )

            changed = True

        return changed

    # ========================================================
    # CRUD
    # ========================================================

    def _add_crud_actions(
        self,
        plan: dict[str, Any],
        actions: set[str],
    ) -> bool:

        if not actions:
            return False

        table = self._find_table(
            plan
        )

        if table is None:
            return False

        existing_ids = {
            str(
                component.get(
                    "id",
                    "",
                )
            )
            for component
            in self._components(plan)
        }

        definitions = {
            "create": {
                "id": "create_record_button",
                "label": "Create",
                "variant": "primary",
                "message": "Create a new record",
            },
            "edit": {
                "id": "edit_record_button",
                "label": "Edit",
                "variant": "secondary",
                "message": "Edit the selected record",
            },
            "delete": {
                "id": "delete_record_button",
                "label": "Delete",
                "variant": "secondary",
                "message": "Delete the selected record",
            },
        }

        changed = False

        for action in (
            "create",
            "edit",
            "delete",
        ):

            if action not in actions:
                continue

            definition = definitions[
                action
            ]

            if definition["id"] in existing_ids:
                continue

            self._components(plan).append(
                {
                    "id": definition["id"],
                    "type": "button",
                    "props": {
                        "label": definition["label"],
                        "variant": definition["variant"],
                        "size": "medium",
                        "action_message": definition["message"],
                    },
                }
            )

            self._append_root(
                plan,
                definition["id"],
            )

            changed = True

        return changed

    # ========================================================
    # GENERIC FORM
    # ========================================================

    def _add_generic_form(
        self,
        plan: dict[str, Any],
    ) -> bool:

        existing_types = {
            component.get(
                "type"
            )
            for component
            in self._components(plan)
        }

        if "form" in existing_types:
            return False

        components = self._components(
            plan
        )

        components.extend(
            [
                {
                    "id": "crud_form",
                    "type": "form",
                    "props": {
                        "name": "zenui_crud_form",
                    },
                },
                {
                    "id": "crud_name",
                    "type": "input",
                    "props": {
                        "name": "name",
                        "label": "Name",
                        "placeholder": "Enter name",
                        "input_type": "text",
                    },
                },
                {
                    "id": "crud_submit",
                    "type": "button",
                    "props": {
                        "label": "Save",
                        "variant": "primary",
                        "size": "medium",
                        "action_message": "Save the record",
                    },
                },
            ]
        )

        for component_id in (
            "crud_form",
            "crud_name",
            "crud_submit",
        ):

            self._append_root(
                plan,
                component_id,
            )

        return True

    # ========================================================
    # CHART BUILDER
    # ========================================================

    def _build_chart(
        self,
        chart_type: str,
        table: dict[str, Any],
    ) -> dict[str, Any] | None:

        props = table.get(
            "props",
            {}
        )

        rows = props.get(
            "rows",
            []
        )

        if not rows:
            return None

        label_key = self._find_label_key(
            rows
        )

        numeric_key = self._find_numeric_key(
            rows
        )

        if not label_key or not numeric_key:
            return None

        labels = []
        values = []

        grouped: dict[str, float] = {}

        for row in rows:

            label = str(
                row.get(
                    label_key,
                    "",
                )
            ).strip()

            if not label:
                continue

            number = self._number(
                row.get(
                    numeric_key,
                    0,
                )
            )

            grouped[label] = (
                grouped.get(
                    label,
                    0.0,
                )
                + number
            )

        if not grouped:
            return None

        labels = list(
            grouped.keys()
        )

        values = list(
            grouped.values()
        )

        return {
            "id": chart_type,
            "type": chart_type,
            "props": {
                "title": self._humanize(
                    numeric_key
                ),
                "labels": labels,
                "series": [
                    {
                        "name": self._humanize(
                            numeric_key
                        ),
                        "values": values,
                    }
                ],
            },
        }

    # ========================================================
    # PLAN HELPERS
    # ========================================================

    @classmethod
    def _resolve_chart_type(
        cls,
        plan: dict[str, Any],
        chart_type: str | None,
    ) -> str:

        normalized = str(
            chart_type or ""
        ).strip().lower()

        if normalized in {
            "bar",
            "line",
            "pie",
        }:
            normalized = f"{normalized}_chart"

        if normalized in {
            "bar_chart",
            "line_chart",
            "pie_chart",
        }:
            return normalized

        components = cls._components(plan)

        for component in reversed(components):
            component_type = str(
                component.get("type", "")
            ).strip().lower()

            if component_type in {
                "bar_chart",
                "line_chart",
                "pie_chart",
            }:
                return component_type

        return normalized

    @staticmethod
    def _components(
        plan: dict[str, Any],
    ) -> list[dict[str, Any]]:

        components = plan.setdefault(
            "components",
            [],
        )

        if not isinstance(
            components,
            list,
        ):

            components = []

            plan["components"] = (
                components
            )

        return components

    @staticmethod
    def _append_root(
        plan: dict[str, Any],
        component_id: str,
    ) -> None:

        root = plan.setdefault(
            "root_components",
            [],
        )

        if not isinstance(
            root,
            list,
        ):

            root = []

            plan["root_components"] = (
                root
            )

        if component_id not in root:
            root.append(
                component_id
            )

    @staticmethod
    def _find_table(
        plan: dict[str, Any],
    ) -> dict[str, Any] | None:

        for component in plan.get(
            "components",
            [],
        ):

            if (
                isinstance(
                    component,
                    dict,
                )
                and component.get(
                    "type"
                ) == "table"
            ):

                return component

        return None

    @staticmethod
    def _find_rows(
        resource_data: dict[str, Any],
    ) -> list[dict[str, Any]]:

        preferred = (
            "rows",
            "records",
            "data",
            "items",
        )

        for key in preferred:

            value = resource_data.get(
                key
            )

            if (
                isinstance(value, list)
                and (
                    not value
                    or isinstance(
                        value[0],
                        dict,
                    )
                )
            ):

                return [
                    row
                    for row in value
                    if isinstance(
                        row,
                        dict,
                    )
                ]

        for value in resource_data.values():

            if (
                isinstance(
                    value,
                    list,
                )
                and value
                and isinstance(
                    value[0],
                    dict,
                )
            ):

                return [
                    row
                    for row in value
                    if isinstance(
                        row,
                        dict,
                    )
                ]

        return []

    @classmethod
    def _rows_from_plan(
        cls,
        plan: dict[str, Any],
    ) -> list[dict[str, Any]]:

        table = cls._find_table(
            plan
        )

        if not table:
            return []

        rows = table.get(
            "props",
            {},
        ).get(
            "rows",
            [],
        )

        return [
            row
            for row in rows
            if isinstance(
                row,
                dict,
            )
        ]

    @classmethod
    def _find_label_key(
        cls,
        rows: list[dict[str, Any]],
    ) -> str | None:

        if not rows:
            return None

        keys = list(
            rows[0].keys()
        )

        preferred = (
            "date",
            "month",
            "year",
            "category",
            "status",
            "name",
            "department",
            "region",
        )

        normalized = {
            cls._normalize(key): key
            for key in keys
        }

        for candidate in preferred:

            if candidate in normalized:
                return normalized[
                    candidate
                ]

        return (
            keys[0]
            if keys
            else None
        )

    @classmethod
    def _find_numeric_key(
        cls,
        rows: list[dict[str, Any]],
    ) -> str | None:

        if not rows:
            return None

        keys = list(
            rows[0].keys()
        )

        for key in keys:

            if all(
                cls._is_number(
                    row.get(key)
                )
                for row in rows
                if isinstance(
                    row,
                    dict,
                )
            ):

                if any(
                    cls._is_number(
                        row.get(key)
                    )
                    for row in rows
                ):

                    return key

        return None

    @staticmethod
    def _is_number(
        value: Any,
    ) -> bool:

        if isinstance(
            value,
            bool,
        ):
            return False

        if isinstance(
            value,
            (int, float),
        ):
            return True

        try:
            float(
                str(value)
                .replace(
                    ",",
                    "",
                )
                .replace(
                    "₹",
                    "",
                )
                .replace(
                    "$",
                    "",
                )
                .strip()
            )

            return True

        except Exception:
            return False

    @staticmethod
    def _number(
        value: Any,
    ) -> float:

        try:

            return float(
                str(value)
                .replace(
                    ",",
                    "",
                )
                .replace(
                    "₹",
                    "",
                )
                .replace(
                    "$",
                    "",
                )
                .strip()
            )

        except Exception:

            return 0.0

    @staticmethod
    def _format_number(
        value: float,
    ) -> str:

        if value.is_integer():
            return f"{int(value):,}"

        return f"{value:,.2f}"

    @staticmethod
    def _humanize(
        value: Any,
    ) -> str:

        return (
            str(value or "")
            .replace(
                "_",
                " ",
            )
            .strip()
            .title()
        )

    @staticmethod
    def _normalize(
        value: Any,
    ) -> str:

        return (
            str(value or "")
            .strip()
            .lower()
            .replace(
                "_",
                " ",
            )
        )

    @staticmethod
    def _safe_key(
        value: str,
    ) -> str:

        return re.sub(
            r"[^a-z0-9]+",
            "_",
            str(value).strip().lower(),
        ).strip("_")

    @classmethod
    def _ensure_integrity(
        cls,
        plan: dict[str, Any],
    ) -> None:

        components = cls._components(
            plan
        )

        valid_ids = {
            str(
                component.get(
                    "id"
                )
            )
            for component in components
            if component.get(
                "id"
            )
        }

        root = plan.setdefault(
            "root_components",
            [],
        )

        root[:] = [
            component_id
            for component_id in root
            if component_id in valid_ids
        ]

        # Make sure every root reference is unique.
        seen: set[str] = set()

        root[:] = [
            component_id
            for component_id in root
            if not (
                component_id in seen
                or seen.add(
                    component_id
                )
            )
        ]