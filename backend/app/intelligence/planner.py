from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel, Field

from app.intelligence.component_registry import (
    get_component_definition,
    is_supported_component,
    supported_components,
)


# ============================================================
# MODELS
# ============================================================


class UIComponent(BaseModel):
    """
    Semantic ZenUI component.

    The planner decides WHAT the interface contains.

    The OpenUI generator decides HOW the component is
    represented in OpenUI Lang.
    """

    id: str
    type: str

    props: dict[str, Any] = Field(
        default_factory=dict
    )


class UIPlan(BaseModel):
    """
    Declarative UI plan consumed by OpenUIGenerator.
    """

    root_components: list[str] = Field(
        default_factory=list
    )

    components: list[UIComponent] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# PLANNER
# ============================================================


class UIPlanner:
    """
    Dynamic ZenUI UI Planner.

    Architecture:

        User request
             ↓
        Intent Analyzer
             ↓
        Context Analyzer
             ↓
        Resource / Tool data
             ↓
        UIPlanner
             ↓
        UIPlan
             ↓
        OpenUIGenerator
             ↓
        OpenUI Renderer

    IMPORTANT:

    This class contains NO business-specific records.

    It must not contain logic such as:

        if "purchase order" ...
        if "sales" ...
        if "weather" ...

    Business data comes from resource/tool execution.

    Semantic meaning comes from IntentAnalyzer.

    Component availability comes from component_registry.

    Therefore the planner remains reusable for arbitrary
    domains and resources.
    """

    # ========================================================
    # PUBLIC API
    # ========================================================

    def create_plan(
        self,
        intent: Any,
        resource_data: dict[str, Any] | None = None,
        user_prompt: str = "",
        conversation_history: list[Any] | None = None,
        previous_ui_plan: dict[str, Any] | None = None,
        context: Any = None,
    ) -> UIPlan:

        resource_data = (
            resource_data
            if isinstance(
                resource_data,
                dict,
            )
            else {}
        )

        conversation_history = (
            conversation_history
            if isinstance(
                conversation_history,
                list,
            )
            else []
        )

        intent_data = self._normalize_intent(
            intent
        )

        text = self._get_text(
            user_prompt,
            intent_data,
        )

        normalized_text = (
            text.lower()
        )

        requested_components = (
            self._get_requested_components(
                intent_data
            )
        )

        requested_components = (
            self._normalize_components(
                requested_components
            )
        )

        # ----------------------------------------------------
        # Dynamic component inference
        # ----------------------------------------------------

        requested_components = (
            self._infer_components(
                text=normalized_text,
                intent=intent_data,
                resource_data=resource_data,
                requested_components=requested_components,
            )
        )

        print()
        print(
            "========== ZENUI UI PLANNER =========="
        )

        print(
            "USER:",
            text,
        )

        print(
            "RESOURCE DATA:",
            bool(resource_data),
        )

        print(
            "REQUESTED COMPONENTS:",
            requested_components,
        )

        # ====================================================
        # REFINEMENT
        # ====================================================

        if previous_ui_plan:

            refined = self._refine_previous_plan(
                previous_ui_plan=previous_ui_plan,
                text=normalized_text,
                resource_data=resource_data,
                context=context,
            )

            if refined is not None:

                refined.metadata.update(
                    {
                        "planner": "dynamic",
                        "refined": True,
                    }
                )

                return refined

        # ====================================================
        # BUILD COMPONENTS
        # ====================================================

        components: list[UIComponent] = []

        root_ids: list[str] = []

        used_ids: set[str] = set()

        # ----------------------------------------------------
        # Heading
        # ----------------------------------------------------

        if "heading" in requested_components:

            heading = UIComponent(
                id=self._unique_id(
                    "heading",
                    used_ids,
                ),
                type="heading",
                props={
                    "text": self._title_from_request(
                        text=text,
                        intent=intent_data,
                    ),
                },
            )

            self._append_component(
                components,
                root_ids,
                heading,
                used_ids,
            )

        # ----------------------------------------------------
        # Description / text
        # ----------------------------------------------------

        if "text" in requested_components:

            description = UIComponent(
                id=self._unique_id(
                    "description",
                    used_ids,
                ),
                type="text",
                props={
                    "text": self._description_from_request(
                        text=text,
                        intent=intent_data,
                        resource_data=resource_data,
                    ),
                },
            )

            self._append_component(
                components,
                root_ids,
                description,
                used_ids,
            )

        # ----------------------------------------------------
        # KPI
        # ----------------------------------------------------

        if "kpi" in requested_components:

            for component in self._build_kpis(
                resource_data
            ):

                self._append_component(
                    components,
                    root_ids,
                    component,
                    used_ids,
                )

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        if "table" in requested_components:

            table = self._build_table(
                resource_data
            )

            if table:

                self._append_component(
                    components,
                    root_ids,
                    table,
                    used_ids,
                )

        # ----------------------------------------------------
        # LINE CHART
        # ----------------------------------------------------

        if "line_chart" in requested_components:

            chart = self._build_chart(
                resource_data,
                chart_type="line_chart",
            )

            if chart:

                self._append_component(
                    components,
                    root_ids,
                    chart,
                    used_ids,
                )

        # ----------------------------------------------------
        # BAR CHART
        # ----------------------------------------------------

        if "bar_chart" in requested_components:

            chart = self._build_chart(
                resource_data,
                chart_type="bar_chart",
            )

            if chart:

                self._append_component(
                    components,
                    root_ids,
                    chart,
                    used_ids,
                )

        # ----------------------------------------------------
        # PIE CHART
        # ----------------------------------------------------

        if "pie_chart" in requested_components:

            chart = self._build_chart(
                resource_data,
                chart_type="pie_chart",
            )

            if chart:

                self._append_component(
                    components,
                    root_ids,
                    chart,
                    used_ids,
                )

        # ----------------------------------------------------
        # FORM
        # ----------------------------------------------------

        if "form" in requested_components:

            form_components = self._build_form(
                intent=intent_data,
                resource_data=resource_data,
            )

            for component in form_components:

                self._append_component(
                    components,
                    root_ids,
                    component,
                    used_ids,
                )

        # ----------------------------------------------------
        # Generic components
        #
        # These do not invent business data.
        # They preserve semantic UI requests.
        # ----------------------------------------------------

        generic_builders = {
            "card": self._build_card,
            "grid": self._build_grid,
            "stack": self._build_stack,
            "alert": self._build_alert,
            "progress": self._build_progress,
            "badge": self._build_badge,
            "tabs": self._build_tabs,
            "select": self._build_select,
            "input": self._build_input,
            "button": self._build_button,
        }

        for component_type in requested_components:

            builder = generic_builders.get(
                component_type
            )

            if builder is None:
                continue

            generated = builder(
                intent_data,
                resource_data,
                text,
            )

            if generated is None:
                continue

            generated_items = (
                generated
                if isinstance(
                    generated,
                    list,
                )
                else [generated]
            )

            for component in generated_items:

                self._append_component(
                    components,
                    root_ids,
                    component,
                    used_ids,
                )

        # ====================================================
        # NORMALIZED SOURCE DATA
        # ====================================================
        #
        # Sources are part of the generic normalized result
        # contract.  They are useful context for external results
        # and must survive into the UI plan when present.
        # ====================================================

        source_table = self._build_sources_table(
            resource_data
        )

        metadata = resource_data.get(
            "metadata"
        )

        if not isinstance(metadata, dict):
            metadata = {}

        external_summary = (
            bool(metadata.get("external", False))
            and str(
                intent_data.get(
                    "requested_output",
                    "",
                )
                or ""
            ).strip().lower()
            in {
                "information",
                "summary",
                "unknown",
                "",
            }
        )

        if source_table and not external_summary:

            self._append_component(
                components,
                root_ids,
                source_table,
                used_ids,
            )

        # ====================================================
        # DATA-AWARE FALLBACK
        # ====================================================
        #
        # If the request produced no renderable component,
        # a generic resource response should still be visible.
        #
        # This is not business-specific.
        # Any list-of-records resource can become a table.
        # ====================================================

        if (
            not components
            and self._find_rows(
                resource_data
            )
        ):

            table = self._build_table(
                resource_data
            )

            if table:

                self._append_component(
                    components,
                    root_ids,
                    table,
                    used_ids,
                )

        # ====================================================
        # EMPTY / UNKNOWN REQUEST
        # ====================================================

        if not components:

            fallback = UIComponent(
                id=self._unique_id(
                    "message",
                    used_ids,
                ),
                type="text",
                props={
                    "text": (
                        "No visual component was "
                        "requested or enough data was "
                        "available to generate one."
                    ),
                },
            )

            self._append_component(
                components,
                root_ids,
                fallback,
                used_ids,
            )

        # ====================================================
        # FINAL PLAN
        # ====================================================

        plan = UIPlan(
            root_components=root_ids,
            components=components,
            metadata={
                "planner": "dynamic",
                "intent": intent_data.get(
                    "intent"
                ),
                "domain": intent_data.get(
                    "domain"
                ),
                "operation": intent_data.get(
                    "operation"
                ),
                "requested_output": intent_data.get(
                    "requested_output"
                ),
                "components": [
                    component.type
                    for component in components
                ],
                "has_resource_data": bool(
                    resource_data
                ),
                "conversation": bool(
                    conversation_history
                ),
                "refined": False,
            },
        )

        print(
            "FINAL COMPONENTS:",
            [
                component.type
                for component in components
            ],
        )

        print(
            "ROOT COMPONENTS:",
            root_ids,
        )

        print(
            "========================================"
        )

        return plan

    # ========================================================
    # INTENT NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_intent(
        intent: Any,
    ) -> dict[str, Any]:

        if isinstance(
            intent,
            dict,
        ):

            return dict(intent)

        if hasattr(
            intent,
            "model_dump",
        ):

            try:

                value = intent.model_dump()

                if isinstance(
                    value,
                    dict,
                ):

                    return value

            except Exception:

                pass

        result: dict[str, Any] = {}

        for field in (
            "intent",
            "domain",
            "operation",
            "target",
            "entities",
            "metrics",
            "filters",
            "time_range",
            "location",
            "requested_output",
            "requested_components",
            "confidence",
            "raw_text",
        ):

            if hasattr(
                intent,
                field,
            ):

                result[field] = getattr(
                    intent,
                    field,
                )

        return result

    # ========================================================
    # TEXT
    # ========================================================

    @staticmethod
    def _get_text(
        user_prompt: str,
        intent: dict[str, Any],
    ) -> str:

        if user_prompt:
            return str(
                user_prompt
            ).strip()

        return str(
            intent.get(
                "raw_text",
                "",
            )
            or ""
        ).strip()

    # ========================================================
    # REQUESTED COMPONENTS
    # ========================================================

    @staticmethod
    def _get_requested_components(
        intent: dict[str, Any],
    ) -> list[str]:

        value = intent.get(
            "requested_components",
            [],
        )

        if not isinstance(
            value,
            list,
        ):

            return []

        return [
            str(item)
            for item in value
            if str(item).strip()
        ]

    # ========================================================
    # COMPONENT NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_components(
        components: list[str],
    ) -> list[str]:

        result: list[str] = []

        for component in components:

            normalized = (
                str(component)
                .strip()
                .lower()
            )

            if not normalized:
                continue

            if not is_supported_component(
                normalized
            ):
                continue

            if normalized not in result:
                result.append(
                    normalized
                )

        return result

    # ========================================================
    # DYNAMIC COMPONENT INFERENCE
    # ========================================================

    def _infer_components(
        self,
        text: str,
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        requested_components: list[str],
    ) -> list[str]:

        result = list(
            requested_components
        )

        output = str(
            intent.get(
                "requested_output",
                "",
            )
            or ""
        ).strip().lower()

        operation = str(
            intent.get(
                "operation",
                "",
            )
            or ""
        ).strip().lower()

        # ----------------------------------------------------
        # Output semantics
        # ----------------------------------------------------

        output_mapping = {
            "information": ["text"],
            "summary": ["heading", "text"],
            "list": ["heading", "table"],
            "table": ["heading", "table"],
            "detail": ["heading", "card"],
            "profile": ["heading", "card"],
            "dashboard": [
                "heading",
                "kpi",
                "line_chart",
                "table",
            ],
            "chart": ["heading", "line_chart"],
            "comparison": [
                "heading",
                "table",
            ],
            "form": [
                "heading",
                "form",
            ],
            "calendar": ["heading"],
            "timeline": ["heading"],
            "map": ["heading"],
        }

        for component in output_mapping.get(
            output,
            [],
        ):

            self._add_supported(
                result,
                component,
            )

        # ----------------------------------------------------
        # Operation semantics
        # ----------------------------------------------------

        if operation in {
            "create",
            "add",
            "update",
            "modify",
        }:

            self._add_supported(
                result,
                "form",
            )

        # ----------------------------------------------------
        # Explicit chart language
        # ----------------------------------------------------

        chart_words = {
            "line_chart": (
                "line chart",
                "line graph",
                "trend chart",
            ),
            "bar_chart": (
                "bar chart",
                "bar graph",
                "column chart",
            ),
            "pie_chart": (
                "pie chart",
                "donut chart",
                "distribution chart",
            ),
        }

        for component_type, phrases in chart_words.items():

            if any(
                phrase in text
                for phrase in phrases
            ):

                self._add_supported(
                    result,
                    component_type,
                )

        # ----------------------------------------------------
        # Generic table language
        # ----------------------------------------------------

        if any(
            phrase in text
            for phrase in (
                "table",
                "tabular",
                "list",
                "records",
                "rows",
            )
        ):

            self._add_supported(
                result,
                "table",
            )

        # ----------------------------------------------------
        # KPI language
        # ----------------------------------------------------

        if any(
            phrase in text
            for phrase in (
                "kpi",
                "kpis",
                "metric",
                "metrics",
                "key performance",
                "total",
                "count",
                "how many",
            )
        ):

            self._add_supported(
                result,
                "kpi",
            )

        # ----------------------------------------------------
        # Dashboard semantics
        #
        # A dashboard is a layout request, not a business
        # domain. It is therefore safe to infer the structure.
        # ----------------------------------------------------

        if (
            "dashboard" in text
            and not result
        ):

            for component in (
                "heading",
                "kpi",
                "line_chart",
                "table",
            ):

                self._add_supported(
                    result,
                    component,
                )

        # ----------------------------------------------------
        # Normalized-result semantics
        # ----------------------------------------------------
        #
        # ResultNormalizer exposes a domain-neutral contract:
        # summary, metrics, metric_cards, records, sources, etc.
        #
        # The planner must use that contract directly.  In
        # particular, an external result must never collapse into
        # a generic placeholder merely because its data is not a
        # row collection.
        # ----------------------------------------------------

        summary = str(
            resource_data.get(
                "summary",
                "",
            )
            or ""
        ).strip()

        metrics = resource_data.get(
            "metrics"
        )

        metric_cards = resource_data.get(
            "metric_cards"
        )

        sources = resource_data.get(
            "sources"
        )

        metadata = resource_data.get(
            "metadata"
        )

        if not isinstance(metadata, dict):
            metadata = {}

        rows = self._find_rows(
            resource_data
        )

        if summary:

            self._add_supported(
                result,
                "heading",
            )

            self._add_supported(
                result,
                "text",
            )

        if isinstance(metrics, dict) and metrics:

            self._add_supported(
                result,
                "kpi",
            )

        elif isinstance(metric_cards, list) and metric_cards:

            self._add_supported(
                result,
                "kpi",
            )

        if rows:

            external_summary = (
                bool(
                    metadata.get(
                        "external",
                        False,
                    )
                )
                and output in {
                    "information",
                    "summary",
                    "unknown",
                    "",
                }
            )

            if external_summary:
                rows = []

        if rows:

            self._add_supported(
                result,
                "heading",
            )

            self._add_supported(
                result,
                "table",
            )

        # Sources are rendered as a second generic table when they
        # exist.  The actual source rows are built from the
        # normalized contract in create_plan(), so no domain or
        # provider-specific component is required.
        if (
            isinstance(sources, list)
            and sources
            and not (
                metadata.get(
                    "external",
                    False,
                )
                and output in {
                    "information",
                    "summary",
                    "unknown",
                    "",
                }
            )
        ):

            self._add_supported(
                result,
                "heading",
            )

        # ----------------------------------------------------
        # Ensure valid components only
        # ----------------------------------------------------

        return self._normalize_components(
            result
        )

    # ========================================================
    # ADD SUPPORTED COMPONENT
    # ========================================================

    @staticmethod
    def _add_supported(
        components: list[str],
        component_type: str,
    ) -> None:

        if not is_supported_component(
            component_type
        ):

            return

        if component_type not in components:

            components.append(
                component_type
            )

    # ========================================================
    # COMPONENT APPEND
    # ========================================================

    @staticmethod
    def _append_component(
        components: list[UIComponent],
        root_ids: list[str],
        component: UIComponent,
        used_ids: set[str],
    ) -> None:

        if component.id in used_ids:
            return

        if not is_supported_component(
            component.type
        ):

            return

        components.append(
            component
        )

        root_ids.append(
            component.id
        )

        used_ids.add(
            component.id
        )

    # ========================================================
    # UNIQUE ID
    # ========================================================

    @staticmethod
    def _unique_id(
        base: str,
        used_ids: set[str],
    ) -> str:

        normalized = (
            str(base)
            .strip()
            .lower()
            .replace(
                " ",
                "_",
            )
        )

        if normalized not in used_ids:
            return normalized

        index = 2

        while (
            f"{normalized}_{index}"
            in used_ids
        ):

            index += 1

        return (
            f"{normalized}_{index}"
        )

    # ========================================================
    # TITLE
    # ========================================================

    @staticmethod
    def _title_from_request(
        text: str,
        intent: dict[str, Any],
    ) -> str:

        target = str(
            intent.get(
                "target",
                "",
            )
            or ""
        ).strip()

        if target:

            return (
                target
                .replace(
                    "_",
                    " ",
                )
                .strip()
                .title()
            )

        cleaned = (
            text.strip()
            .rstrip("?")
            .rstrip(".")
        )

        if not cleaned:
            return "ZenUI"

        return cleaned[:1].upper() + cleaned[1:]

    # ========================================================
    # DESCRIPTION
    # ========================================================

    @staticmethod
    def _description_from_request(
        text: str,
        intent: dict[str, Any],
        resource_data: dict[str, Any],
    ) -> str:

        # The normalized result's summary is the authoritative
        # content for informational/external responses.  Do not
        # replace real returned content with a generic placeholder.
        summary = resource_data.get(
            "summary"
        )

        metadata = resource_data.get(
            "metadata",
        )

        sources = resource_data.get(
            "sources",
        )

        is_external = (
            isinstance(metadata, dict)
            and metadata.get("external")
        )

        intent_name = str(
            intent.get("intent", "")
            or ""
        ).strip().lower()

        if intent_name == "greeting":
            return (
                "Hello. I am ZenUI. Describe an enterprise "
                "task and I will generate an interactive interface."
            )

        if intent_name == "capability_query":
            return (
                "ZenUI turns natural-language requests into "
                "dynamic enterprise interfaces, including data "
                "tables, metrics, charts, and forms."
            )

        if (
            (isinstance(summary, str) and summary.strip())
            or (is_external and isinstance(sources, list) and sources)
        ):
            description = (
                summary.strip()
                if isinstance(summary, str) and summary.strip()
                else "Relevant information was found."
            )

            if (
                is_external
                and isinstance(sources, list)
                and sources
            ):
                source_lines = []

                for source in sources:

                    if not isinstance(source, dict):
                        continue

                    title = str(
                        source.get("title")
                        or source.get("url")
                        or "Source"
                    ).strip()

                    url = str(
                        source.get("url")
                        or ""
                    ).strip()

                    if url:
                        source_lines.append(
                            f"- {title}: {url}"
                        )

                if source_lines:
                    description += (
                        "\n\nSources:\n"
                        + "\n".join(source_lines)
                    )

            return description

        metadata = resource_data.get(
            "metadata",
        )

        if isinstance(metadata, dict) and metadata.get("empty"):
            return (
                "No relevant information was found. "
                "Try a more specific question."
            )

        output = str(
            intent.get(
                "requested_output",
                "",
            )
            or ""
        ).strip()

        if output:

            return (
                f"Generated {output} interface "
                "from your request."
            )

        if text:

            return (
                "Interface generated from your request."
            )

        return (
            "ZenUI generated interface."
        )

    # ========================================================
    # FIND ROWS
    # ========================================================

    @staticmethod
    def _find_rows(
        resource_data: dict[str, Any],
    ) -> list[dict[str, Any]]:

        if not isinstance(
            resource_data,
            dict,
        ):

            return []

        # ----------------------------------------------------
        # The normalized ZenUI contract explicitly identifies
        # records. Prefer that collection so other contract
        # collections such as metric_cards and sources are not
        # accidentally rendered as business records.
        # ----------------------------------------------------

        explicit_records = resource_data.get(
            "records"
        )

        if isinstance(
            explicit_records,
            list,
        ):

            records = [
                item
                for item in explicit_records
                if isinstance(
                    item,
                    dict,
                )
            ]

            if records:
                return records

        # ----------------------------------------------------
        # Compatibility path for raw/un-normalized structured
        # data. Contract-owned collections are excluded because
        # they have their own semantic representation.
        # ----------------------------------------------------

        reserved_collections = {
            "records",
            "sources",
            "metric_cards",
            "collections",
        }

        candidates: list[list[dict[str, Any]]] = []

        for key, value in resource_data.items():

            if str(key) in reserved_collections:
                continue

            if not isinstance(
                value,
                list,
            ):

                continue

            rows = [
                item
                for item in value
                if isinstance(
                    item,
                    dict,
                )
            ]

            if rows:
                candidates.append(
                    rows
                )

        if not candidates:
            return []

        return max(
            candidates,
            key=len,
        )

    # ========================================================
    # NUMERIC KEY
    # ========================================================

    @staticmethod
    def _find_numeric_key(
        rows: list[dict[str, Any]],
        keys: list[str] | None = None,
    ) -> str | None:

        if not rows:
            return None

        candidate_keys = (
            keys
            if keys is not None
            else list(
                rows[0].keys()
            )
        )

        for key in candidate_keys:

            values = [
                row.get(key)
                for row in rows
            ]

            numeric_count = sum(
                1
                for value in values
                if UIPlanner._is_number(
                    value
                )
            )

            if numeric_count == len(
                values
            ):

                return str(key)

        return None

    # ========================================================
    # NUMBER
    # ========================================================

    @staticmethod
    def _number(
        value: Any,
    ) -> float:

        if isinstance(
            value,
            bool,
        ):

            return float(
                int(value)
            )

        if isinstance(
            value,
            (int, float),
        ):

            return float(value)

        if isinstance(
            value,
            str,
        ):

            cleaned = (
                value
                .strip()
                .replace(
                    ",",
                    "",
                )
                .replace(
                    "$",
                    "",
                )
                .replace(
                    "₹",
                    "",
                )
                .replace(
                    "€",
                    "",
                )
                .replace(
                    "£",
                    "",
                )
            )

            try:

                return float(
                    cleaned
                )

            except ValueError:

                return 0.0

        return 0.0

    # ========================================================
    # IS NUMBER
    # ========================================================

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

        if isinstance(
            value,
            str,
        ):

            try:

                UIPlanner._number(
                    value
                )

                cleaned = (
                    value
                    .strip()
                    .replace(
                        ",",
                        "",
                    )
                    .replace(
                        "$",
                        "",
                    )
                    .replace(
                        "₹",
                        "",
                    )
                    .replace(
                        "€",
                        "",
                    )
                    .replace(
                        "£",
                        "",
                    )
                )

                float(cleaned)

                return True

            except ValueError:

                return False

        return False

    # ========================================================
    # CURRENCY
    # ========================================================

    @staticmethod
    def _currency(
        value: Any,
    ) -> str:

        number = UIPlanner._number(
            value
        )

        if number.is_integer():

            return (
                f"{number:,.0f}"
            )

        return (
            f"{number:,.2f}"
        )

    # ========================================================
    # KPI BUILDER
    # ========================================================

    @staticmethod
    def _build_kpis(
        resource_data: dict[str, Any],
    ) -> list[UIComponent]:

        result: list[
            UIComponent
        ] = []

        # ----------------------------------------------------
        # Explicit generic metrics object.
        #
        # We do not assume names such as total_amount,
        # approved, pending, etc.
        # Every metric supplied by the resource layer can
        # become a KPI.
        # ----------------------------------------------------

        metrics = resource_data.get(
            "metrics"
        )

        metric_cards = resource_data.get(
            "metric_cards"
        )

        if isinstance(metric_cards, list) and metric_cards:

            for index, card in enumerate(
                metric_cards,
                start=1,
            ):

                if not isinstance(card, dict):
                    continue

                label = str(
                    card.get(
                        "label",
                        "Metric",
                    )
                    or "Metric"
                ).strip()

                value = card.get(
                    "value",
                    "",
                )

                if isinstance(value, (dict, list)):
                    continue

                result.append(
                    UIComponent(
                        id=f"metric_{index}",
                        type="kpi",
                        props={
                            "label": label,
                            "value": str(value),
                        },
                    )
                )

        if result:
            return result

        if isinstance(
            metrics,
            dict,
        ):

            for index, (
                key,
                value,
            ) in enumerate(
                metrics.items(),
                start=1,
            ):

                if isinstance(
                    value,
                    (dict, list),
                ):

                    continue

                label = (
                    str(key)
                    .replace(
                        "_",
                        " ",
                    )
                    .strip()
                    .title()
                )

                display_value = (
                    UIPlanner._currency(
                        value
                    )
                    if UIPlanner._is_number(
                        value
                    )
                    else str(value)
                )

                result.append(
                    UIComponent(
                        id=(
                            f"metric_{index}"
                        ),
                        type="kpi",
                        props={
                            "label": label,
                            "value": display_value,
                        },
                    )
                )

        if result:
            return result

        # ----------------------------------------------------
        # Derive useful generic metrics from rows.
        # ----------------------------------------------------

        rows = UIPlanner._find_rows(
            resource_data
        )

        if not rows:
            return []

        numeric_key = (
            UIPlanner._find_numeric_key(
                rows
            )
        )

        if not numeric_key:
            return [
                UIComponent(
                    id="record_count",
                    type="kpi",
                    props={
                        "label": "Records",
                        "value": str(
                            len(rows)
                        ),
                    },
                )
            ]

        values = [
            UIPlanner._number(
                row.get(
                    numeric_key
                )
            )
            for row in rows
        ]

        total = sum(values)

        average = (
            total / len(values)
            if values
            else 0
        )

        label = (
            str(numeric_key)
            .replace(
                "_",
                " ",
            )
            .strip()
            .title()
        )

        return [
            UIComponent(
                id="record_count",
                type="kpi",
                props={
                    "label": "Records",
                    "value": str(
                        len(rows)
                    ),
                },
            ),
            UIComponent(
                id="derived_total",
                type="kpi",
                props={
                    "label": (
                        f"Total {label}"
                    ),
                    "value": UIPlanner._currency(
                        total
                    ),
                },
            ),
            UIComponent(
                id="derived_average",
                type="kpi",
                props={
                    "label": (
                        f"Average {label}"
                    ),
                    "value": UIPlanner._currency(
                        average
                    ),
                },
            ),
        ]

    # ========================================================
    # TABLE
    # ========================================================

    @staticmethod
    def _build_table(
        resource_data: dict[str, Any],
    ) -> UIComponent | None:

        rows = UIPlanner._find_rows(
            resource_data
        )

        if not rows:

            return UIComponent(
                id="data_table",
                type="table",
                props={
                    "columns": [],
                    "rows": [],
                    "empty_state": (
                        "No records available."
                    ),
                },
            )

        # ----------------------------------------------------
        # Collect the union of all keys.
        #
        # This prevents data disappearing merely because
        # later records have additional fields.
        # ----------------------------------------------------

        keys: list[str] = []

        for row in rows:

            for key in row.keys():

                key_string = str(key)

                if key_string not in keys:

                    keys.append(
                        key_string
                    )

        columns = [
            {
                "key": key,
                "label": (
                    key
                    .replace(
                        "_",
                        " ",
                    )
                    .strip()
                    .title()
                ),
            }
            for key in keys
        ]

        normalized_rows = [
            {
                key: row.get(
                    key
                )
                for key in keys
            }
            for row in rows
        ]

        return UIComponent(
            id="data_table",
            type="table",
            props={
                "columns": columns,
                "rows": normalized_rows,
            },
        )

    # ========================================================
    # SOURCE TABLE
    # ========================================================

    @staticmethod
    def _build_sources_table(
        resource_data: dict[str, Any],
    ) -> UIComponent | None:

        sources = resource_data.get(
            "sources"
        )

        if not isinstance(
            sources,
            list,
        ):
            return None

        rows: list[dict[str, Any]] = []

        for source in sources:

            if not isinstance(source, dict):
                continue

            url = str(
                source.get(
                    "url",
                    "",
                )
                or ""
            ).strip()

            if not url:
                continue

            title = str(
                source.get(
                    "title",
                    url,
                )
                or url
            ).strip()

            rows.append(
                {
                    "title": title or url,
                    "url": url,
                }
            )

        if not rows:
            return None

        return UIComponent(
            id="sources_table",
            type="table",
            props={
                "columns": [
                    {
                        "key": "title",
                        "label": "Source",
                    },
                    {
                        "key": "url",
                        "label": "URL",
                    },
                ],
                "rows": rows,
            },
        )

    # ========================================================
    # CHART
    # ========================================================

    @classmethod
    def _build_chart(
        cls,
        resource_data: dict[str, Any],
        chart_type: str,
    ) -> UIComponent | None:

        rows = cls._find_rows(
            resource_data
        )

        if not rows:
            return None

        keys = list(
            rows[0].keys()
        )

        if len(keys) < 2:
            return None

        numeric_key = cls._find_numeric_key(
            rows,
            keys[1:],
        )

        if not numeric_key:
            return None

        # Prefer the first non-numeric field as category axis.
        label_key: str | None = None

        for key in keys:

            if key == numeric_key:
                continue

            if not all(
                cls._is_number(
                    row.get(key)
                )
                for row in rows
            ):

                label_key = key
                break

        if label_key is None:

            label_key = keys[0]

        labels = [
            str(
                row.get(
                    label_key,
                    "",
                )
            )
            for row in rows
        ]

        values = [
            cls._number(
                row.get(
                    numeric_key,
                    0,
                )
            )
            for row in rows
        ]

        metric_name = (
            str(numeric_key)
            .replace(
                "_",
                " ",
            )
            .strip()
            .title()
        )

        label_name = (
            str(label_key)
            .replace(
                "_",
                " ",
            )
            .strip()
            .title()
        )

        if chart_type == "pie_chart":

            props = {
                "title": (
                    f"{metric_name} by "
                    f"{label_name}"
                ),
                "labels": labels,
                "values": values,
            }

        else:

            props = {
                "title": (
                    f"{metric_name} by "
                    f"{label_name}"
                ),
                "labels": labels,
                "series": [
                    {
                        "name": metric_name,
                        "values": values,
                    }
                ],
            }

        return UIComponent(
            id=chart_type,
            type=chart_type,
            props=props,
        )

    # ========================================================
    # FORM
    # ========================================================

    @staticmethod
    def _build_form(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
    ) -> list[UIComponent]:

        fields: list[
            UIComponent
        ] = []

        # ----------------------------------------------------
        # If resource metadata describes fields, use them.
        #
        # This is the preferred dynamic path.
        # ----------------------------------------------------

        schema_candidates = (
            resource_data.get(
                "form_schema"
            ),
            resource_data.get(
                "schema"
            ),
            resource_data.get(
                "fields"
            ),
        )

        schema = next(
            (
                candidate
                for candidate
                in schema_candidates
                if isinstance(
                    candidate,
                    list,
                )
            ),
            None,
        )

        if schema:

            for index, field in enumerate(
                schema,
                start=1,
            ):

                if not isinstance(
                    field,
                    dict,
                ):

                    continue

                name = str(
                    field.get(
                        "name",
                        f"field_{index}",
                    )
                )

                label = str(
                    field.get(
                        "label",
                        name
                        .replace(
                            "_",
                            " ",
                        )
                        .title(),
                    )
                )

                field_type = str(
                    field.get(
                        "type",
                        "input",
                    )
                )

                component_type = (
                    field_type
                    if is_supported_component(
                        field_type
                    )
                    else "input"
                )

                props = dict(
                    field
                )

                props.setdefault(
                    "name",
                    name,
                )

                props.setdefault(
                    "label",
                    label,
                )

                fields.append(
                    UIComponent(
                        id=name,
                        type=component_type,
                        props=props,
                    )
                )

        # ----------------------------------------------------
        # If no schema exists, infer fields from the first
        # resource record. This remains domain independent.
        # ----------------------------------------------------

        if not fields:

            rows = UIPlanner._find_rows(
                resource_data
            )

            if rows:

                for key, value in rows[0].items():

                    field_name = str(
                        key
                    )

                    if isinstance(
                        value,
                        bool,
                    ):

                        component_type = (
                            "select"
                            if is_supported_component(
                                "select"
                            )
                            else "input"
                        )

                    else:

                        component_type = "input"

                    fields.append(
                        UIComponent(
                            id=field_name,
                            type=component_type,
                            props={
                                "name": field_name,
                                "label": (
                                    field_name
                                    .replace(
                                        "_",
                                        " ",
                                    )
                                    .strip()
                                    .title()
                                ),
                                "placeholder": (
                                    f"Enter "
                                    f"{field_name}"
                                ),
                            },
                        )
                    )

        # ----------------------------------------------------
        # Generic form with no schema.
        # ----------------------------------------------------

        if not fields:

            target = str(
                intent.get(
                    "target",
                    "value",
                )
                or "value"
            )

            fields.append(
                UIComponent(
                    id="value",
                    type="input",
                    props={
                        "name": "value",
                        "label": (
                            target
                            .replace(
                                "_",
                                " ",
                            )
                            .strip()
                            .title()
                        ),
                        "placeholder": (
                            "Enter value"
                        ),
                    },
                )
            )

        result = [
            UIComponent(
                id="form",
                type="form",
                props={
                    "name": (
                        str(
                            intent.get(
                                "target",
                                "zenui_form",
                            )
                            or "zenui_form"
                        )
                        .strip()
                        .replace(
                            " ",
                            "_",
                        )
                    ),
                },
            )
        ]

        result.extend(
            fields
        )

        if is_supported_component(
            "button"
        ):

            result.append(
                UIComponent(
                    id="submit",
                    type="button",
                    props={
                        "label": (
                            "Submit"
                        ),
                        "action": {
                            "type": (
                                "continue_conversation"
                            ),
                            "humanFriendlyMessage": (
                                "Submit form"
                            ),
                        },
                    },
                )
            )

        return result

    # ========================================================
    # GENERIC CARD
    # ========================================================

    @staticmethod
    def _build_card(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        target = str(
            intent.get(
                "target",
                "",
            )
            or ""
        )

        return UIComponent(
            id="card",
            type="card",
            props={
                "title": (
                    target
                    .replace(
                        "_",
                        " ",
                    )
                    .title()
                    if target
                    else "Details"
                ),
                "content": (
                    text
                    if text
                    else "Details"
                ),
            },
        )

    # ========================================================
    # GENERIC GRID
    # ========================================================

    @staticmethod
    def _build_grid(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        return UIComponent(
            id="grid",
            type="grid",
            props={
                "columns": 1,
            },
        )

    # ========================================================
    # GENERIC STACK
    # ========================================================

    @staticmethod
    def _build_stack(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        return UIComponent(
            id="stack",
            type="stack",
            props={},
        )

    # ========================================================
    # ALERT
    # ========================================================

    @staticmethod
    def _build_alert(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        return UIComponent(
            id="alert",
            type="alert",
            props={
                "message": text
                or "Information",
            },
        )

    # ========================================================
    # PROGRESS
    # ========================================================

    @staticmethod
    def _build_progress(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        return UIComponent(
            id="progress",
            type="progress",
            props={
                "value": 0,
            },
        )

    # ========================================================
    # BADGE
    # ========================================================

    @staticmethod
    def _build_badge(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        return UIComponent(
            id="badge",
            type="badge",
            props={
                "text": (
                    str(
                        intent.get(
                            "operation",
                            "info",
                        )
                    )
                    .replace(
                        "_",
                        " ",
                    )
                    .title()
                ),
            },
        )

    # ========================================================
    # TABS
    # ========================================================

    @staticmethod
    def _build_tabs(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        return UIComponent(
            id="tabs",
            type="tabs",
            props={
                "items": [],
            },
        )

    # ========================================================
    # SELECT
    # ========================================================

    @staticmethod
    def _build_select(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        return UIComponent(
            id="select",
            type="select",
            props={
                "name": "selection",
                "label": "Select",
                "options": [],
            },
        )

    # ========================================================
    # INPUT
    # ========================================================

    @staticmethod
    def _build_input(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        target = str(
            intent.get(
                "target",
                "value",
            )
            or "value"
        )

        return UIComponent(
            id="input",
            type="input",
            props={
                "name": target,
                "label": (
                    target
                    .replace(
                        "_",
                        " ",
                    )
                    .strip()
                    .title()
                ),
                "placeholder": (
                    "Enter value"
                ),
            },
        )

    # ========================================================
    # BUTTON
    # ========================================================

    @staticmethod
    def _build_button(
        intent: dict[str, Any],
        resource_data: dict[str, Any],
        text: str,
    ) -> UIComponent:

        operation = str(
            intent.get(
                "operation",
                "submit",
            )
            or "submit"
        )

        return UIComponent(
            id="button",
            type="button",
            props={
                "label": (
                    operation
                    .replace(
                        "_",
                        " ",
                    )
                    .strip()
                    .title()
                ),
                "action": {
                    "type": (
                        "continue_conversation"
                    ),
                    "humanFriendlyMessage": (
                        operation
                    ),
                },
            },
        )

    # ========================================================
    # REFINEMENT
    # ========================================================

    @staticmethod
    def _refine_previous_plan(
        previous_ui_plan: dict[str, Any],
        text: str,
        resource_data: dict[str, Any],
        context: Any = None,
    ) -> UIPlan | None:

        try:

            plan = UIPlan.model_validate(
                deepcopy(
                    previous_ui_plan
                )
            )

        except Exception:

            return None

        if not plan.components:

            return None

        normalized = (
            text.strip().lower()
        )

        changed = False

        # ----------------------------------------------------
        # Remove column
        # ----------------------------------------------------

        remove_match = None

        patterns = (
            r"remove\s+(?:the\s+)?(.+?)\s+column",
            r"hide\s+(?:the\s+)?(.+?)\s+column",
            r"delete\s+(?:the\s+)?(.+?)\s+column",
        )

        import re

        for pattern in patterns:

            match = re.search(
                pattern,
                normalized,
            )

            if match:

                remove_match = (
                    match.group(1)
                    .strip()
                )

                break

        if remove_match:

            target = (
                remove_match
                .replace(
                    " ",
                    "_",
                )
            )

            for component in plan.components:

                if component.type != "table":
                    continue

                columns = component.props.get(
                    "columns",
                    [],
                )

                if not isinstance(
                    columns,
                    list,
                ):

                    continue

                new_columns = []

                for column in columns:

                    if not isinstance(
                        column,
                        dict,
                    ):

                        new_columns.append(
                            column
                        )

                        continue

                    key = str(
                        column.get(
                            "key",
                            "",
                        )
                    ).lower()

                    label = str(
                        column.get(
                            "label",
                            "",
                        )
                    ).lower()

                    if (
                        target in key
                        or target in label.replace(
                            " ",
                            "_",
                        )
                    ):

                        changed = True
                        continue

                    new_columns.append(
                        column
                    )

                if changed:

                    component.props[
                        "columns"
                    ] = new_columns

                    valid_keys = {
                        str(
                            column.get(
                                "key"
                            )
                        )
                        for column
                        in new_columns
                        if isinstance(
                            column,
                            dict,
                        )
                    }

                    rows = component.props.get(
                        "rows",
                        [],
                    )

                    if isinstance(
                        rows,
                        list,
                    ):

                        component.props[
                            "rows"
                        ] = [
                            {
                                key: row.get(
                                    key
                                )
                                for key
                                in valid_keys
                            }
                            for row
                            in rows
                            if isinstance(
                                row,
                                dict,
                            )
                        ]

        # ----------------------------------------------------
        # Add chart
        # ----------------------------------------------------

        if any(
            phrase in normalized
            for phrase in (
                "add line chart",
                "add a line chart",
                "show line chart",
                "show a line chart",
            )
        ):

            chart = UIPlanner._build_chart(
                resource_data,
                "line_chart",
            )

            if chart:

                if not any(
                    component.type
                    == "line_chart"
                    for component
                    in plan.components
                ):

                    plan.components.append(
                        chart
                    )

                    plan.root_components.append(
                        chart.id
                    )

                    changed = True

        if any(
            phrase in normalized
            for phrase in (
                "add bar chart",
                "add a bar chart",
                "show bar chart",
                "show a bar chart",
            )
        ):

            chart = UIPlanner._build_chart(
                resource_data,
                "bar_chart",
            )

            if chart:

                if not any(
                    component.type
                    == "bar_chart"
                    for component
                    in plan.components
                ):

                    plan.components.append(
                        chart
                    )

                    plan.root_components.append(
                        chart.id
                    )

                    changed = True

        if any(
            phrase in normalized
            for phrase in (
                "add pie chart",
                "add a pie chart",
                "show pie chart",
                "show a pie chart",
            )
        ):

            chart = UIPlanner._build_chart(
                resource_data,
                "pie_chart",
            )

            if chart:

                if not any(
                    component.type
                    == "pie_chart"
                    for component
                    in plan.components
                ):

                    plan.components.append(
                        chart
                    )

                    plan.root_components.append(
                        chart.id
                    )

                    changed = True

        # ----------------------------------------------------
        # Remove component
        # ----------------------------------------------------

        remove_component = None

        component_patterns = {
            "kpi": (
                "remove kpi",
                "remove kpis",
                "hide kpi",
                "hide kpis",
            ),
            "table": (
                "remove table",
                "hide table",
            ),
            "line_chart": (
                "remove line chart",
                "hide line chart",
            ),
            "bar_chart": (
                "remove bar chart",
                "hide bar chart",
            ),
            "pie_chart": (
                "remove pie chart",
                "hide pie chart",
            ),
            "description": (
                "remove description",
                "hide description",
            ),
        }

        for component_type, phrases in (
            component_patterns.items()
        ):

            if any(
                phrase in normalized
                for phrase in phrases
            ):

                remove_component = (
                    component_type
                )

                break

        if remove_component:

            before = len(
                plan.components
            )

            plan.components = [
                component
                for component
                in plan.components
                if component.type
                != remove_component
            ]

            if len(
                plan.components
            ) != before:

                changed = True

                valid_ids = {
                    component.id
                    for component
                    in plan.components
                }

                plan.root_components = [
                    component_id
                    for component_id
                    in plan.root_components
                    if component_id
                    in valid_ids
                ]

        # ----------------------------------------------------
        # Rebuild table with fresh resource data when the
        # user asks to refresh/update the displayed data.
        # ----------------------------------------------------

        if any(
            phrase in normalized
            for phrase in (
                "refresh",
                "reload",
                "update data",
                "refresh data",
            )
        ):

            refreshed_table = (
                UIPlanner._build_table(
                    resource_data
                )
            )

            if refreshed_table:

                for index, component in enumerate(
                    plan.components
                ):

                    if component.type == "table":

                        refreshed_table.id = (
                            component.id
                        )

                        plan.components[
                            index
                        ] = refreshed_table

                        changed = True

                        break

        if not changed:

            return None

        return plan


# ============================================================
# MODULE INSTANCE
# ============================================================


ui_planner = UIPlanner()