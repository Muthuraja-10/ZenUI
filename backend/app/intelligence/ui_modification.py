from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ============================================================
# UI MODIFICATION
# ============================================================


@dataclass(slots=True)
class UIModification:
    """
    Structured description of a requested UI modification.

    This object describes WHAT the user wants changed.

    It does not modify the UI plan itself.
    """

    is_modification: bool = False

    action: Optional[str] = None

    target: Optional[str] = None

    value: Optional[str] = None


# ============================================================
# DETECTOR
# ============================================================


class UIModificationDetector:
    """
    Detect explicit conversational UI modifications.

    Responsibility:

        user request
             ↓
        modification description

    This class does NOT:
        - execute CRUD operations
        - access databases
        - generate OpenUI
        - modify UI plans
        - decide business data

    Those responsibilities belong to other layers.

    The detector is intentionally synchronous because it is also
    used as a deterministic safety layer by the backend tests and
    orchestration pipeline.
    """

    # --------------------------------------------------------
    # Normalization
    # --------------------------------------------------------

    @staticmethod
    def _normalize(prompt: str | None) -> str:

        if not prompt:
            return ""

        return re.sub(
            r"\s+",
            " ",
            prompt.strip().lower(),
        )

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def _contains_any(
        text: str,
        phrases: tuple[str, ...],
    ) -> bool:

        return any(
            phrase in text
            for phrase in phrases
        )

    @staticmethod
    def _contains_add_request(
        text: str,
        targets: tuple[str, ...],
    ) -> bool:

        add_words = (
            "add",
            "show",
            "display",
            "include",
            "insert",
            "enable",
        )

        return (
            any(
                word in text
                for word in add_words
            )
            and any(
                target in text
                for target in targets
            )
        )

    @staticmethod
    def _contains_remove_request(
        text: str,
        targets: tuple[str, ...],
    ) -> bool:

        remove_words = (
            "remove",
            "delete",
            "hide",
            "disable",
        )

        return (
            any(
                word in text
                for word in remove_words
            )
            and any(
                target in text
                for target in targets
            )
        )

    # ========================================================
    # PUBLIC
    # ========================================================

    def detect(
        self,
        prompt: str,
    ) -> UIModification:

        text = self._normalize(prompt)

        if not text:
            return UIModification()

        # ====================================================
        # COLUMN REMOVE
        # ====================================================

        match = re.search(
            r"""
            \b
            (?:remove|delete|hide)
            \s+
            (?:the\s+)?
            (?P<target>[\w\s-]+?)
            \s+
            column
            \b
            """,
            text,
            flags=re.IGNORECASE | re.VERBOSE,
        )

        if match:

            return UIModification(
                is_modification=True,
                action="remove_column",
                target=match.group(
                    "target"
                ).strip(),
            )

        # ====================================================
        # COLUMN ADD
        # ====================================================

        match = re.search(
            r"""
            \b
            (?:add|show|display|include)
            \s+
            (?:the\s+)?
            (?P<target>[\w\s-]+?)
            \s+
            column
            \b
            """,
            text,
            flags=re.IGNORECASE | re.VERBOSE,
        )

        if match:

            return UIModification(
                is_modification=True,
                action="add_column",
                target=match.group(
                    "target"
                ).strip(),
            )

        # ====================================================
        # COLUMN RENAME
        # ====================================================

        match = re.search(
            r"\b(?:rename|change)\s+(?:the\s+)?(?P<old>[\w\s-]+?)\s+column\s+to\s+(?P<new>[\w\s-]+)\s*$",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return UIModification(
                is_modification=True,
                action="rename_column",
                target=match.group("old").strip(),
                value=match.group("new").strip(),
            )

        # ====================================================
        # TITLE UPDATE
        # ====================================================

        match = re.search(
            r"\b(?:change|rename|update)\s+(?:the\s+)?title\s+to\s+(?P<value>.+?)\s*$",
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return UIModification(
                is_modification=True,
                action="update_title",
                value=match.group("value").strip(),
            )

        # ====================================================
        # FILTER
        # ====================================================

        match = re.search(
            r"""
            ^
            (?:
                only
                |
                show\s+only
                |
                display\s+only
                |
                filter\s+(?:by|to)?
                |
                filter\s+the\s+table\s+(?:by|to)?
            )
            \s*
            (?P<value>.+?)
            \s*$
            """,
            text,
            flags=re.IGNORECASE | re.VERBOSE,
        )

        if match:

            value = match.group(
                "value"
            ).strip()

            if value:

                return UIModification(
                    is_modification=True,
                    action="filter_table",
                    value=value,
                )

        # ====================================================
        # SHORT FILTER
        # ====================================================

        if text.startswith("only "):

            value = text[
                len("only "):
            ].strip()

            if value:

                return UIModification(
                    is_modification=True,
                    action="filter_table",
                    value=value,
                )

        # ====================================================
        # CHART TYPES
        # ====================================================

        chart_aliases = {
            "pie_chart": (
                "pie chart",
                "pie graph",
                "donut chart",
                "donut graph",
            ),
            "bar_chart": (
                "bar chart",
                "bar graph",
            ),
            "line_chart": (
                "line chart",
                "line graph",
            ),
        }

        # ====================================================
        # CHART REPLACEMENT
        # ====================================================

        replacement_pairs = (
            (
                "line_chart",
                "bar_chart",
            ),
            (
                "bar_chart",
                "line_chart",
            ),
            (
                "pie_chart",
                "bar_chart",
            ),
            (
                "pie_chart",
                "line_chart",
            ),
            (
                "bar_chart",
                "pie_chart",
            ),
            (
                "line_chart",
                "pie_chart",
            ),
        )

        replacement_words = (
            "change",
            "replace",
            "switch",
            "convert",
        )

        if any(
            word in text
            for word in replacement_words
        ):

            for source_type, target_type in replacement_pairs:

                source_aliases = chart_aliases[
                    source_type
                ]

                target_aliases = chart_aliases[
                    target_type
                ]

                if (
                    any(
                        alias in text
                        for alias in source_aliases
                    )
                    and any(
                        alias in text
                        for alias in target_aliases
                    )
                ):

                    return UIModification(
                        is_modification=True,
                        action="replace_chart",
                        target=target_type,
                        value=source_type,
                    )

        # Conversational chart references resolve against the
        # current UI plan in UIPlanModifier.
        match = re.search(
            r"\b(?:change|replace|switch|convert)\s+(?:it|that chart|the chart)\s+to\s+(?:a\s+)?(?P<target>bar|line|pie)(?:\s+chart)?\b",
            text,
        )

        if match:
            return UIModification(
                is_modification=True,
                action="replace_chart",
                target=f"{match.group('target')}_chart",
            )

        # ====================================================
        # CHART ADD
        # ====================================================

        for chart_type, aliases in chart_aliases.items():

            if self._contains_add_request(
                text,
                aliases,
            ):

                return UIModification(
                    is_modification=True,
                    action="add_chart",
                    target=chart_type,
                )

        # ====================================================
        # CHART REMOVE
        # ====================================================

        for chart_type, aliases in chart_aliases.items():

            if self._contains_remove_request(
                text,
                aliases,
            ):

                return UIModification(
                    is_modification=True,
                    action="remove_chart",
                    target=chart_type,
                )

        if re.search(
            r"\b(?:remove|delete|hide)\s+(?:it|that chart|the chart)\b",
            text,
        ):
            return UIModification(
                is_modification=True,
                action="remove_chart",
            )

        # ====================================================
        # SORT
        # ====================================================

        match = re.search(
            r"\b(?:sort|order)\s+(?:by\s+)?(?P<target>[\w\s-]+?)(?:\s+(?P<direction>highest|lowest|descending|ascending|desc|asc)\s+first)?\s*$",
            text,
        )

        if match:
            direction = match.group("direction") or "ascending"
            return UIModification(
                is_modification=True,
                action="sort_table",
                target=match.group("target").strip(),
                value=direction,
            )

        # ====================================================
        # KPI
        # ====================================================

        kpi_aliases = (
            "kpi",
            "kpis",
            "metric",
            "metrics",
            "summary card",
            "summary cards",
        )

        if self._contains_add_request(
            text,
            kpi_aliases,
        ):

            return UIModification(
                is_modification=True,
                action="add_component",
                target="kpi",
            )

        if self._contains_remove_request(
            text,
            kpi_aliases,
        ):

            return UIModification(
                is_modification=True,
                action="remove_component",
                target="kpi",
            )

        # ====================================================
        # GENERIC COMPONENT ADD
        # ====================================================

        component_aliases = {
            "table": (
                "table",
            ),
            "form": (
                "form",
            ),
            "calendar": (
                "calendar",
            ),
            "timeline": (
                "timeline",
            ),
            "map": (
                "map",
            ),
            "tabs": (
                "tabs",
            ),
            "progress": (
                "progress",
                "progress indicator",
            ),
        }

        for component_type, aliases in component_aliases.items():

            if self._contains_add_request(
                text,
                aliases,
            ):

                return UIModification(
                    is_modification=True,
                    action="add_component",
                    target=component_type,
                )

            if self._contains_remove_request(
                text,
                aliases,
            ):

                return UIModification(
                    is_modification=True,
                    action="remove_component",
                    target=component_type,
                )

        # ====================================================
        # CRUD / ACTION REQUEST
        # ====================================================

        crud_aliases = (
            "crud",
            "edit and delete",
            "edit and add",
            "create and edit",
            "create edit delete",
            "add edit delete",
            "enable editing",
            "enable crud",
            "actions",
        )

        if self._contains_any(
            text,
            crud_aliases,
        ):

            return UIModification(
                is_modification=True,
                action="enable_actions",
            )

        # ====================================================
        # REFRESH
        # ====================================================

        if self._contains_any(
            text,
            (
                "refresh",
                "reload",
                "refresh the data",
                "reload the data",
            ),
        ):

            return UIModification(
                is_modification=True,
                action="refresh",
            )

        # ====================================================
        # NO MODIFICATION
        # ====================================================

        return UIModification()