from __future__ import annotations

import json
import keyword
import re
from typing import Any


class OpenUIGenerator:
    """
    Compile a validated ZenUI UIPlan into OpenUI Lang.

    Architecture:

        UIPlan
          ↓
        dependency resolution
          ↓
        deterministic declarations
          ↓
        root declaration

    IMPORTANT:

    This class does NOT decide what UI should exist.

    Intelligence / Planner decides the UIPlan.

    This class only compiles that plan into OpenUI.
    """

    # ============================================================
    # PUBLIC API
    # ============================================================

    def generate(self, plan: Any) -> str:
        components = self._get_components(plan)

        if not components:
            return (
                'empty_state = '
                'TextContent("No interface generated", "default")\n\n'
                'root = Stack([empty_state])'
            )

        lookup = self._build_lookup(components)

        if not lookup:
            return (
                'empty_state = '
                'TextContent("No interface generated", "default")\n\n'
                'root = Stack([empty_state])'
            )

        roots = self._get_root_components(plan, lookup)

        if not roots:
            roots = list(lookup.keys())

        ordered_ids: list[str] = []
        visited: set[str] = set()

        for root_id in roots:
            self._collect_dependencies(
                root_id,
                lookup,
                visited,
                ordered_ids,
            )

        # Defensive inclusion of disconnected components.
        for component_id in lookup:
            if component_id not in visited:
                self._collect_dependencies(
                    component_id,
                    lookup,
                    visited,
                    ordered_ids,
                )

        declarations: list[str] = []

        for component_id in ordered_ids:
            component = lookup.get(component_id)

            if component is None:
                continue

            declaration = self._generate_component(
                component_id,
                component,
                lookup,
            )

            if declaration.strip():
                declarations.append(declaration)

        valid_roots = [
            root_id
            for root_id in roots
            if root_id in lookup
        ]

        if not valid_roots:
            valid_roots = ordered_ids

        root_expression = (
            f"root = Stack([{', '.join(valid_roots)}])"
        )

        declarations.append(root_expression)

        return "\n\n".join(declarations)

    # ============================================================
    # PLAN EXTRACTION
    # ============================================================

    @staticmethod
    def _get_components(plan: Any) -> list[Any]:
        if isinstance(plan, dict):
            components = plan.get("components", [])
        else:
            components = getattr(plan, "components", [])

        return components if isinstance(components, list) else []

    def _build_lookup(
        self,
        components: list[Any],
    ) -> dict[str, Any]:

        lookup: dict[str, Any] = {}

        for component in components:
            raw_id = self._component_id(component)

            if not raw_id:
                continue

            component_id = self.safe_identifier(raw_id)

            if not component_id:
                continue

            lookup[component_id] = component

        return lookup

    def _get_root_components(
        self,
        plan: Any,
        lookup: dict[str, Any],
    ) -> list[str]:

        if isinstance(plan, dict):
            roots = plan.get("root_components", [])
        else:
            roots = getattr(plan, "root_components", [])

        if not isinstance(roots, list):
            return []

        result: list[str] = []

        for root in roots:

            if isinstance(root, dict):
                root = (
                    root.get("id")
                    or root.get("component_id")
                    or root.get("ref")
                )

            root_id = self.safe_identifier(root)

            if root_id and root_id in lookup:
                if root_id not in result:
                    result.append(root_id)

        return result

    # ============================================================
    # DEPENDENCY RESOLUTION
    # ============================================================

    def _collect_dependencies(
        self,
        component_id: str,
        lookup: dict[str, Any],
        visited: set[str],
        ordered_ids: list[str],
    ) -> None:

        component_id = self.safe_identifier(component_id)

        if not component_id:
            return

        if component_id in visited:
            return

        component = lookup.get(component_id)

        if component is None:
            return

        # Mark before recursion so malformed circular plans
        # cannot recurse forever.
        visited.add(component_id)

        dependencies = self._component_dependencies(
            component_id,
            component,
            lookup,
        )

        for dependency in dependencies:
            self._collect_dependencies(
                dependency,
                lookup,
                visited,
                ordered_ids,
            )

        ordered_ids.append(component_id)

    def _component_dependencies(
        self,
        component_id: str,
        component: Any,
        lookup: dict[str, Any],
    ) -> list[str]:

        component_type = self._component_type(component)
        props = self._component_props(component)

        dependencies: list[str] = []

        # Generic nested component references.
        for key in (
            "children",
            "child_components",
            "items",
            "content",
        ):
            dependencies.extend(
                self._extract_component_refs(
                    props.get(key),
                    lookup,
                )
            )

        # Form dependencies.
        if component_type == "form":

            dependencies.extend(
                self._extract_component_refs(
                    props.get("fields"),
                    lookup,
                )
            )

            dependencies.extend(
                self._extract_component_refs(
                    props.get("buttons"),
                    lookup,
                )
            )

        # Buttons dependencies.
        elif component_type == "buttons":

            dependencies.extend(
                self._extract_component_refs(
                    props.get(
                        "children",
                        props.get("buttons"),
                    ),
                    lookup,
                )
            )

        # Form control.
        elif component_type == "form_control":

            dependencies.extend(
                self._extract_component_refs(
                    props.get(
                        "control_id",
                        props.get("control"),
                    ),
                    lookup,
                )
            )

        # Container components.
        elif component_type in {
            "card",
            "stack",
            "grid",
            "tabs",
        }:

            for key in (
                "children",
                "items",
                "content",
                "tabs",
            ):
                dependencies.extend(
                    self._extract_component_refs(
                        props.get(key),
                        lookup,
                    )
                )

        # Stable de-duplication.
        result: list[str] = []

        for dependency in dependencies:

            dependency = self.safe_identifier(
                dependency
            )

            if not dependency:
                continue

            if dependency == component_id:
                continue

            if dependency not in lookup:
                continue

            if dependency not in result:
                result.append(dependency)

        return result

    # ============================================================
    # REFERENCE EXTRACTION
    # ============================================================

    def _extract_component_refs(
        self,
        value: Any,
        lookup: dict[str, Any],
    ) -> list[str]:

        if value is None:
            return []

        values = value if isinstance(value, list) else [value]

        result: list[str] = []

        for item in values:

            if isinstance(item, dict):
                reference = (
                    item.get("id")
                    or item.get("component_id")
                    or item.get("ref")
                )
            else:
                reference = item

            if reference is None:
                continue

            reference = self.safe_identifier(reference)

            if reference and reference in lookup:
                result.append(reference)

        return result

    # ============================================================
    # COMPONENT DISPATCH
    # ============================================================

    def _generate_component(
        self,
        component_id: str,
        component: Any,
        lookup: dict[str, Any],
    ) -> str:

        component_type = self._component_type(component)
        props = self._component_props(component)

        generators = {
            "text": self._generate_text,
            "heading": self._generate_heading,
            "card": self._generate_card,
            "kpi": self._generate_kpi,
            "table": self._generate_table,
            "line_chart": self._generate_line_chart,
            "bar_chart": self._generate_bar_chart,
            "pie_chart": self._generate_pie_chart,
            "form": self._generate_form,
            "form_control": self._generate_form_control,
            "input": self._generate_input,
            "select": self._generate_select,
            "button": self._generate_button,
            "buttons": self._generate_buttons,
            "badge": self._generate_badge,
            "tabs": self._generate_tabs,
            "alert": self._generate_alert,
            "progress": self._generate_progress,
            "stack": self._generate_stack,
            "grid": self._generate_grid,
        }

        generator = generators.get(component_type)

        if generator is None:
            return self._generate_text(
                component_id,
                {
                    "text": props.get(
                        "text",
                        component_id,
                    )
                },
            )

        return generator(
            component_id,
            props,
        )

    # ============================================================
    # TEXT
    # ============================================================

    def _generate_text(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        text = self.string(
            props.get("text", "")
        )

        size = self._text_size(
            props.get("size", "default")
        )

        return (
            f'{component_id} = '
            f'TextContent({text}, "{size}")'
        )

    # ============================================================
    # HEADING
    # ============================================================

    def _generate_heading(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        text = self.string(
            props.get(
                "text",
                component_id,
            )
        )

        return (
            f'{component_id} = '
            f'TextContent({text}, "large-heavy")'
        )

    # ============================================================
    # CARD
    # ============================================================

    def _generate_card(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        children = self._refs(
            props.get("children", [])
        )

        return (
            f"{component_id} = "
            f"Card([{', '.join(children)}])"
        )

    # ============================================================
    # KPI
    # ============================================================

    def _generate_kpi(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        label = str(
            props.get("label", "")
        )

        value = str(
            props.get("value", "")
        )

        # IMPORTANT:
        # Do not quote an already JSON-encoded value.
        content = self.string(
            f"{label}: {value}"
        )

        return (
            f'{component_id} = '
            f'TextContent({content}, "default")'
        )

    # ============================================================
    # TABLE
    # ============================================================

    def _generate_table(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        columns = props.get("columns", [])
        rows = props.get("rows", [])

        if not isinstance(columns, list):
            columns = []

        if not isinstance(rows, list):
            rows = []

        expressions: list[str] = []

        for column in columns:

            if not isinstance(column, dict):
                continue

            key = str(
                column.get("key", "")
            )

            if not key:
                continue

            label = str(
                column.get("label", key)
            )

            values = []

            for row in rows:
                if not isinstance(row, dict):
                    continue

                values.append(
                    str(row.get(key, ""))
                )

            expressions.append(
                "Col("
                f"{self.string(label)}, "
                f"{self._list_expression(values)}"
                ")"
            )

        return (
            f"{component_id} = "
            f"Table([{', '.join(expressions)}])"
        )

    # ============================================================
    # LINE CHART
    # ============================================================

    def _generate_line_chart(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        labels = props.get("labels", [])
        series = props.get("series", [])

        # Accept the legacy single-series shape at this boundary so
        # older persisted UI plans do not silently lose chart values.
        if not series and isinstance(props.get("values"), list):
            series = [
                {
                    "name": props.get("title", "Series"),
                    "values": props["values"],
                }
            ]

        if not isinstance(labels, list):
            labels = []

        if not isinstance(series, list):
            series = []

        series_expressions: list[str] = []

        for item in series:

            if not isinstance(item, dict):
                continue

            name = self.string(
                item.get("name", "Series")
            )

            values = item.get("values", [])

            series_expressions.append(
                "Series("
                f"{name}, "
                f"{self._list_number_expression(values)}"
                ")"
            )

        return (
            f"{component_id} = "
            f"LineChart("
            f"{self._list_expression(labels)}, "
            f"[{', '.join(series_expressions)}]"
            f")"
        )

    # ============================================================
    # BAR CHART
    # ============================================================

    def _generate_bar_chart(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        labels = props.get("labels", [])
        series = props.get("series", [])

        if not isinstance(labels, list):
            labels = []

        if not isinstance(series, list):
            series = []

        expressions: list[str] = []

        for item in series:

            if not isinstance(item, dict):
                continue

            expressions.append(
                "Series("
                f"{self.string(item.get('name', 'Series'))}, "
                f"{self._list_number_expression(item.get('values', []))}"
                ")"
            )

        return (
            f"{component_id} = "
            f"BarChart("
            f"{self._list_expression(labels)}, "
            f"[{', '.join(expressions)}]"
            f")"
        )

    # ============================================================
    # PIE CHART
    # ============================================================

    def _generate_pie_chart(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        labels = props.get("labels", [])
        values = props.get("values", [])

        if not isinstance(labels, list):
            labels = []

        if not isinstance(values, list):
            values = []

        return (
            f"{component_id} = "
            f"PieChart("
            f"{self._list_expression(labels)}, "
            f"{self._list_number_expression(values)}, "
            f'"donut"'
            f")"
        )

    # ============================================================
    # FORM
    # ============================================================

    def _generate_form(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        name = self.string(
            props.get(
                "name",
                component_id,
            )
        )

        fields = self._refs(
            props.get("fields", [])
        )

        buttons = self._refs(
            props.get("buttons", [])
        )

        # --------------------------------------------------------
        # CRITICAL:
        #
        # Never emit a fake / unresolved button reference.
        #
        # If the planner supplied a Buttons component, use it.
        #
        # Otherwise create a valid generic Buttons declaration
        # locally.
        #
        # This is framework-level recovery, NOT business logic.
        # --------------------------------------------------------

        if buttons:

            button_reference = buttons[0]

            return (
                f"{component_id} = "
                f"Form("
                f"{name}, "
                f"{button_reference}, "
                f"[{', '.join(fields)}]"
                f")"
            )

        default_buttons_id = (
            f"{component_id}_buttons"
        )

        default_button_id = (
            f"{component_id}_submit"
        )

        default_button = (
            f"{default_button_id} = "
            f'Button('
            f'"Submit", '
            f'Action([]), '
            f'"primary", '
            f'"normal", '
            f'"medium"'
            f')'
        )

        default_buttons = (
            f"{default_buttons_id} = "
            f"Buttons([{default_button_id}])"
        )

        form = (
            f"{component_id} = "
            f"Form("
            f"{name}, "
            f"{default_buttons_id}, "
            f"[{', '.join(fields)}]"
            f")"
        )

        return "\n\n".join(
            [
                default_button,
                default_buttons,
                form,
            ]
        )

    # ============================================================
    # FORM CONTROL
    # ============================================================

    def _generate_form_control(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        label = self.string(
            props.get(
                "label",
                component_id,
            )
        )

        control = self.safe_identifier(
            props.get(
                "control_id",
                props.get("control", ""),
            )
        )

        if not control:
            control = (
                f"{component_id}_input"
            )

        return (
            f"{component_id} = "
            f"FormControl("
            f"{label}, "
            f"{control}"
            f")"
        )

    # ============================================================
    # INPUT
    # ============================================================

    def _generate_input(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        name = self.string(
            props.get(
                "name",
                component_id,
            )
        )

        placeholder = self.string(
            props.get(
                "placeholder",
                "",
            )
        )

        input_type = self.string(
            props.get(
                "input_type",
                props.get("type", "text"),
            )
        )

        rules = props.get("rules", {})

        if not isinstance(rules, dict):
            rules = {}

        return (
            f"{component_id} = "
            f"Input("
            f"{name}, "
            f"{placeholder}, "
            f"{input_type}, "
            f"{self._dict_expression(rules)}"
            f")"
        )

    # ============================================================
    # SELECT
    # ============================================================

    def _generate_select(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        name = self.string(
            props.get(
                "name",
                component_id,
            )
        )

        options = props.get(
            "options",
            [],
        )

        if not isinstance(options, list):
            options = []

        return (
            f"{component_id} = "
            f"Select("
            f"{name}, "
            f"{self._list_expression(options)}"
            f")"
        )

    # ============================================================
    # BUTTON
    # ============================================================

    def _generate_button(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        label = self.string(
            props.get(
                "label",
                "Button",
            )
        )

        variant = str(
            props.get(
                "variant",
                "primary",
            )
        ).lower()

        size = str(
            props.get(
                "size",
                "medium",
            )
        ).lower()

        action_message = props.get(
            "action_message"
        )

        if action_message:

            action = (
                "Action(["
                "@ToAssistant("
                f"{self.string(action_message)}"
                ")])"
            )

        else:

            action = "Action([])"

        return (
            f"{component_id} = "
            f"Button("
            f"{label}, "
            f"{action}, "
            f'"{variant}", '
            f'"normal", '
            f'"{size}"'
            f")"
        )

    # ============================================================
    # BUTTONS
    # ============================================================

    def _generate_buttons(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        children = self._refs(
            props.get(
                "children",
                props.get("buttons", []),
            )
        )

        return (
            f"{component_id} = "
            f"Buttons("
            f"[{', '.join(children)}]"
            f")"
        )

    # ============================================================
    # BADGE
    # ============================================================

    def _generate_badge(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        text = self.string(
            props.get(
                "text",
                props.get(
                    "label",
                    "Status",
                ),
            )
        )

        return (
            f"{component_id} = "
            f"Tag("
            f"{text}, "
            f"null, "
            f'"md", '
            f'"neutral"'
            f")"
        )

    # ============================================================
    # TABS
    # ============================================================

    def _generate_tabs(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        children = self._refs(
            props.get("children", [])
        )

        return (
            f"{component_id} = "
            f"Stack([{', '.join(children)}])"
        )

    # ============================================================
    # ALERT
    # ============================================================

    def _generate_alert(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        message = self.string(
            props.get(
                "message",
                props.get("text", ""),
            )
        )

        return (
            f"{component_id} = "
            f'Callout("info", {message})'
        )

    # ============================================================
    # PROGRESS
    # ============================================================

    def _generate_progress(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        value = props.get("value", 0)

        return (
            f"{component_id} = "
            f"Progress("
            f"{self._number_expression(value)}"
            f")"
        )

    # ============================================================
    # STACK
    # ============================================================

    def _generate_stack(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        children = self._refs(
            props.get("children", [])
        )

        return (
            f"{component_id} = "
            f"Stack([{', '.join(children)}])"
        )

    # ============================================================
    # GRID
    # ============================================================

    def _generate_grid(
        self,
        component_id: str,
        props: dict[str, Any],
    ) -> str:

        children = self._refs(
            props.get("children", [])
        )

        return (
            f"{component_id} = "
            f"Grid([{', '.join(children)}])"
        )

    # ============================================================
    # REFERENCES
    # ============================================================

    def _refs(self, value: Any) -> list[str]:

        if value is None:
            return []

        values = (
            value
            if isinstance(value, list)
            else [value]
        )

        result: list[str] = []

        for item in values:

            if isinstance(item, dict):

                item = (
                    item.get("id")
                    or item.get("component_id")
                    or item.get("ref")
                )

            if not item:
                continue

            identifier = self.safe_identifier(item)

            if identifier:
                result.append(identifier)

        return result

    # ============================================================
    # EXPRESSIONS
    # ============================================================

    def _list_expression(
        self,
        values: Any,
    ) -> str:

        if not isinstance(values, list):
            values = []

        return (
            "["
            + ", ".join(
                self.string(value)
                for value in values
            )
            + "]"
        )

    def _list_number_expression(
        self,
        values: Any,
    ) -> str:

        if not isinstance(values, list):
            values = []

        return (
            "["
            + ", ".join(
                self._number_expression(value)
                for value in values
            )
            + "]"
        )

    @staticmethod
    def _number_expression(
        value: Any,
    ) -> str:

        try:
            number = float(value)

            if number.is_integer():
                return str(int(number))

            return str(number)

        except (TypeError, ValueError):
            return "0"

    @staticmethod
    def _dict_expression(
        value: dict[str, Any],
    ) -> str:

        return json.dumps(
            value,
            ensure_ascii=False,
        )

    # ============================================================
    # STRING / IDENTIFIER HELPERS
    # ============================================================

    @staticmethod
    def string(value: Any) -> str:
        return json.dumps(
            "" if value is None else str(value),
            ensure_ascii=False,
        )

    @staticmethod
    def safe_identifier(value: Any) -> str:

        text = str(value or "").strip().lower()

        if not text:
            return ""

        text = re.sub(
            r"[^a-zA-Z0-9_]+",
            "_",
            text,
        )

        text = re.sub(
            r"_+",
            "_",
            text,
        )

        text = text.strip("_")

        if not text:
            return ""

        if text[0].isdigit():
            text = f"component_{text}"

        if keyword.iskeyword(text):
            text = f"component_{text}"

        return text

    @staticmethod
    def _component_id(
        component: Any,
    ) -> str:

        if isinstance(component, dict):

            return str(
                component.get(
                    "id",
                    component.get(
                        "component_id",
                        "",
                    ),
                )
                or ""
            )

        return str(
            getattr(
                component,
                "id",
                "",
            )
            or ""
        )

    @staticmethod
    def _component_type(
        component: Any,
    ) -> str:

        if isinstance(component, dict):

            return str(
                component.get(
                    "type",
                    "",
                )
                or ""
            ).strip().lower()

        return str(
            getattr(
                component,
                "type",
                "",
            )
            or ""
        ).strip().lower()

    @staticmethod
    def _component_props(
        component: Any,
    ) -> dict[str, Any]:

        if isinstance(component, dict):
            props = component.get("props", {})
        else:
            props = getattr(
                component,
                "props",
                {},
            )

        return (
            props
            if isinstance(props, dict)
            else {}
        )

    @staticmethod
    def _text_size(value: Any) -> str:

        allowed = {
            "default",
            "small",
            "large",
            "large-heavy",
            "medium",
            "medium-heavy",
            "small-heavy",
        }

        value = str(
            value or "default"
        ).lower()

        return (
            value
            if value in allowed
            else "default"
        )