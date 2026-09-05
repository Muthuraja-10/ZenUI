from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.llm.llm_service import LLMService


# ============================================================
# CONSTANTS
# ============================================================

ALLOWED_OPERATIONS = {
    "create",
    "read",
    "update",
    "delete",
    "add",
    "remove",
    "modify",
    "compare",
    "search",
    "filter",
    "count",
    "summarize",
    "analyze",
    "unknown",
}

ALLOWED_OUTPUTS = {
    "information",
    "form",
    "table",
    "chart",
    "dashboard",
    "profile",
    "detail",
    "list",
    "calendar",
    "timeline",
    "map",
    "comparison",
    "summary",
    "unknown",
}

ALLOWED_COMPONENTS = {
    "text",
    "heading",
    "card",
    "kpi",
    "table",
    "bar_chart",
    "line_chart",
    "pie_chart",
    "form",
    "input",
    "select",
    "button",
    "badge",
    "tabs",
    "grid",
    "stack",
    "alert",
    "progress",
}

# Canonical entity vocabulary.
#
# This is not a list of every possible enterprise entity.
# It is the normalization layer for entities that ZenUI
# currently knows how to route reliably.
ENTITY_ALIASES: dict[str, str] = {
    # Procurement
    "purchase order": "purchase_order",
    "purchase orders": "purchase_order",
    "po": "purchase_order",
    "pos": "purchase_order",

    "purchase requisition": "purchase_requisition",
    "purchase requisitions": "purchase_requisition",
    "pr": "purchase_requisition",
    "prs": "purchase_requisition",

    "supplier": "supplier",
    "suppliers": "supplier",
    "vendor": "supplier",
    "vendors": "supplier",

    # HR
    "employee": "employee",
    "employees": "employee",
    "staff": "employee",

    # Customer
    "customer": "customer",
    "customers": "customer",
    "client": "customer",
    "clients": "customer",

    # Sales
    "sale": "sale",
    "sales": "sale",
    "sales order": "sales_order",
    "sales orders": "sales_order",

    # Other
    "product": "product",
    "products": "product",
    "weather": "weather",
}

DOMAIN_BY_TARGET: dict[str, str] = {
    "purchase_order": "procurement",
    "purchase_requisition": "procurement",
    "supplier": "procurement",
    "sale": "sales",
    "sales_order": "sales",
    "employee": "hr",
    "customer": "customer",
    "product": "inventory",
    "weather": "weather",
}


# ============================================================
# RESULT
# ============================================================


class IntentResult(BaseModel):
    """
    Canonical semantic contract used by the entire ZenUI
    intelligence pipeline.

    Downstream layers should consume this contract rather
    than trying to reinterpret the user's natural language.
    """

    intent: str = "unknown"

    domain: str | None = None

    operation: str = "unknown"

    target: str | None = None

    entities: list[str] = Field(
        default_factory=list
    )

    metrics: list[str] = Field(
        default_factory=list
    )

    filters: list[Any] = Field(
        default_factory=list
    )

    time_range: str | None = None

    location: str | None = None

    requested_output: str = "unknown"

    requested_components: list[str] = Field(
        default_factory=list
    )

    confidence: float = 0.0


# ============================================================
# ANALYZER
# ============================================================


class IntentAnalyzer:
    """
    ZenUI semantic intent engine.

    Responsibility:

        natural language
             ↓
        semantic intent
             ↓
        canonical IntentResult

    The LLM is used for semantic understanding.

    Deterministic normalization and fallback are ALWAYS applied
    after the LLM result.

    Therefore:

        LLM available
            → semantic interpretation
            → canonicalization

        LLM unavailable
            → deterministic interpretation
            → canonicalization

    The rest of ZenUI never needs to care whether the LLM
    succeeded.
    """

    def __init__(self) -> None:
        self.llm = LLMService()

    # ========================================================
    # PUBLIC
    # ========================================================

    async def analyze(
        self,
        user_prompt: str,
    ) -> IntentResult:

        text = self._normalize_text(
            user_prompt
        )

        if not text:
            raise ValueError(
                "User prompt cannot be empty."
            )

        special_intent = self._special_intent(text)

        if special_intent is not None:
            return special_intent

        # ----------------------------------------------------
        # First attempt: LLM semantic analysis
        # ----------------------------------------------------

        try:

            prompt = self._build_prompt(
                text
            )

            data = await self.llm.generate_json(
                prompt,
                max_tokens=1800,
            )

            if isinstance(
                data,
                dict,
            ):

                return self._canonicalize(
                    data,
                    text,
                )

        except Exception as error:

            print(
                "\n========== INTENT ERROR =========="
            )

            print(error)

            print(
                "Using deterministic intent fallback."
            )

        # ----------------------------------------------------
        # Deterministic fallback
        # ----------------------------------------------------

        return self._deterministic_fallback(
            text
        )

    # ========================================================
    # NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_text(
        text: str | None,
    ) -> str:

        if not text:
            return ""

        return re.sub(
            r"\s+",
            " ",
            text.strip().lower(),
        )

    # ========================================================
    # CANONICALIZATION
    # ========================================================

    def _canonicalize(
        self,
        raw: dict[str, Any],
        user_prompt: str,
    ) -> IntentResult:

        target = self._canonical_target(
            raw.get("target")
        )

        # If the model did not give us a reliable target,
        # infer one from the actual request.
        if not target:
            target = self._infer_target(
                user_prompt
            )

        domain = self._clean_string(
            raw.get("domain")
        )

        # Target-derived domain wins over an inconsistent
        # LLM domain.
        if target in DOMAIN_BY_TARGET:
            domain = DOMAIN_BY_TARGET[
                target
            ]

        operation = self._canonical_operation(
            raw.get("operation"),
            user_prompt,
        )

        requested_output = (
            self._canonical_output(
                raw.get("requested_output")
            )
        )

        if requested_output == "unknown":
            requested_output = (
                self._infer_requested_output(
                    user_prompt,
                    operation,
                )
            )

        entities = self._canonical_entities(
            raw.get("entities"),
            target,
            user_prompt,
        )

        components = (
            self._canonical_components(
                raw.get(
                    "requested_components"
                ),
            )
        )

        if not components:
            components = (
                self._infer_components(
                    user_prompt=user_prompt,
                    operation=operation,
                    target=target,
                    requested_output=requested_output,
                )
            )

        confidence = self._confidence(
            raw.get("confidence")
        )

        # Deterministic fallback semantics should increase
        # confidence when the request is unambiguous.
        if (
            confidence <= 0.0
            and target
        ):
            confidence = 0.75

        intent_name = (
            self._clean_string(
                raw.get("intent")
            )
            or self._build_intent_name(
                operation=operation,
                target=target,
                user_prompt=user_prompt,
            )
        )

        return IntentResult(
            intent=intent_name,
            domain=domain,
            operation=operation,
            target=target,
            entities=entities,
            metrics=self._string_list(
                raw.get("metrics")
            ),
            filters=self._list_value(
                raw.get("filters")
            ),
            time_range=self._clean_string(
                raw.get("time_range")
            ),
            location=self._clean_string(
                raw.get("location")
            ),
            requested_output=requested_output,
            requested_components=components,
            confidence=confidence,
        )

    # ========================================================
    # OPERATION
    # ========================================================

    def _canonical_operation(
        self,
        value: Any,
        user_prompt: str,
    ) -> str:

        operation = self._clean_string(
            value
        ).lower()

        if operation in ALLOWED_OPERATIONS:
            return operation

        return self._infer_operation(
            user_prompt
        )

    # ========================================================
    # TARGET
    # ========================================================

    def _canonical_target(
        self,
        value: Any,
    ) -> str | None:

        if not isinstance(
            value,
            str,
        ):
            return None

        text = self._normalize_text(
            value
        )

        if not text:
            return None

        # Already canonical.
        if text in DOMAIN_BY_TARGET:
            return text

        return ENTITY_ALIASES.get(
            text
        )

    def _infer_target(
        self,
        user_prompt: str,
    ) -> str | None:

        text = self._normalize_text(
            user_prompt
        )

        # Longest phrases first.
        aliases = sorted(
            ENTITY_ALIASES.items(),
            key=lambda item: len(
                item[0]
            ),
            reverse=True,
        )

        for phrase, canonical in aliases:

            if self._contains_phrase(
                text,
                phrase,
            ):
                return canonical

        return None

    # ========================================================
    # DOMAIN
    # ========================================================

    def _infer_domain(
        self,
        target: str | None,
        user_prompt: str,
    ) -> str | None:

        if target in DOMAIN_BY_TARGET:
            return DOMAIN_BY_TARGET[
                target
            ]

        text = self._normalize_text(
            user_prompt
        )

        if any(
            word in text
            for word in (
                "sales",
                "revenue",
                "selling",
            )
        ):
            return "sales"

        if any(
            word in text
            for word in (
                "employee",
                "employees",
                "staff",
                "hr",
                "human resources",
            )
        ):
            return "hr"

        if any(
            word in text
            for word in (
                "customer",
                "customers",
                "client",
                "clients",
            )
        ):
            return "customer"

        if "weather" in text:
            return "weather"

        if any(
            word in text
            for word in (
                "product",
                "products",
                "inventory",
                "stock",
            )
        ):
            return "inventory"

        return None

    # ========================================================
    # OUTPUT
    # ========================================================

    def _canonical_output(
        self,
        value: Any,
    ) -> str:

        output = self._clean_string(
            value
        ).lower()

        if output in ALLOWED_OUTPUTS:
            return output

        return "unknown"

    def _infer_requested_output(
        self,
        user_prompt: str,
        operation: str,
    ) -> str:

        text = self._normalize_text(
            user_prompt
        )

        if any(
            phrase in text
            for phrase in (
                "bar chart",
                "bar graph",
            )
        ):
            return "chart"

        if any(
            phrase in text
            for phrase in (
                "line chart",
                "line graph",
            )
        ):
            return "chart"

        if any(
            phrase in text
            for phrase in (
                "pie chart",
                "pie graph",
            )
        ):
            return "chart"

        if any(
            word in text
            for word in (
                "dashboard",
                "executive view",
                "overview",
            )
        ):
            return "dashboard"

        if any(
            word in text
            for word in (
                "table",
                "tabular",
            )
        ):
            return "table"

        if any(
            word in text
            for word in (
                "list",
                "show",
                "display",
                "view",
                "give me",
            )
        ):
            return ""

        if operation in {
            "create",
            "update",
        }:
            return "form"

        if operation in {
            "summarize",
        }:
            return "summary"

        return "information"

    # ========================================================
    # COMPONENTS
    # ========================================================

    def _canonical_components(
        self,
        value: Any,
    ) -> list[str]:

        if not isinstance(
            value,
            list,
        ):
            return []

        result: list[str] = []

        for item in value:

            if not isinstance(
                item,
                str,
            ):
                continue

            component = (
                self._normalize_text(
                    item
                )
            )

            if component in ALLOWED_COMPONENTS:
                result.append(
                    component
                )

        return self._unique(
            result
        )

    def _infer_components(
        self,
        *,
        user_prompt: str,
        operation: str,
        target: str | None,
        requested_output: str,
    ) -> list[str]:

        text = self._normalize_text(
            user_prompt
        )

        components: list[str] = []

        # Explicit UI representation has priority.
        if "bar chart" in text:
            components.append(
                "bar_chart"
            )

        if "line chart" in text:
            components.append(
                "line_chart"
            )

        if "pie chart" in text:
            components.append(
                "pie_chart"
            )

        if requested_output == "table":
            components.append(
                "table"
            )

        if requested_output == "chart":
            if not any(
                component.endswith("_chart")
                for component in components
            ):
                components.append(
                    "bar_chart"
                )

        if requested_output == "dashboard":
            components.extend(
                [
                    "heading",
                    "grid",
                ]
            )

        if requested_output in {
            "list",
            "information",
            "summary",
        }:
            components.append(
                "text"
            )

        if operation in {
            "create",
            "update",
        }:
            components.extend(
                [
                    "form",
                    "input",
                    "button",
                ]
            )

        # A normal "show X" request with structured
        # enterprise data should naturally become a table.
        if (
            operation == "read"
            and target
            and not components
        ):
            components.extend(
                [
                    "heading",
                    "table",
                ]
            )

        return self._unique(
            components
        )

    # ========================================================
    # ENTITIES
    # ========================================================

    def _canonical_entities(
        self,
        value: Any,
        target: str | None,
        user_prompt: str,
    ) -> list[str]:

        result: list[str] = []

        if isinstance(
            value,
            list,
        ):

            for item in value:

                canonical = (
                    self._canonical_target(
                        item
                    )
                )

                if canonical:
                    result.append(
                        canonical
                    )

        if target:
            result.append(
                target
            )

        if not result:

            inferred = self._infer_target(
                user_prompt
            )

            if inferred:
                result.append(
                    inferred
                )

        return self._unique(
            result
        )

    # ========================================================
    # DETERMINISTIC FALLBACK
    # ========================================================

    @staticmethod
    def _special_intent(
        text: str,
    ) -> IntentResult | None:

        normalized = IntentAnalyzer._normalize_text(
            text
        )

        if re.fullmatch(
            r"(?:hi|hello|hey|good morning|good evening)[!.]?",
            normalized,
        ):
            return IntentResult(
                intent="greeting",
                operation="unknown",
                requested_output="information",
                requested_components=[
                    "heading",
                    "text",
                ],
                confidence=0.99,
            )

        if normalized in {
            "what can you do",
            "what can you do?",
            "how can you help me",
            "how can you help me?",
        }:
            return IntentResult(
                intent="capability_query",
                operation="unknown",
                requested_output="information",
                requested_components=[
                    "heading",
                    "text",
                ],
                confidence=0.99,
            )

        return None

    def _deterministic_fallback(
        self,
        user_prompt: str,
    ) -> IntentResult:

        text = self._normalize_text(
            user_prompt
        )

        special_intent = self._special_intent(text)

        if special_intent is not None:
            return special_intent

        target = self._infer_target(
            text
        )

        operation = self._infer_operation(
            text
        )

        domain = self._infer_domain(
            target,
            text,
        )

        requested_output = (
            self._infer_requested_output(
                text,
                operation,
            )
        )

        components = (
            self._infer_components(
                user_prompt=text,
                operation=operation,
                target=target,
                requested_output=requested_output,
            )
        )

        entities = (
            [target]
            if target
            else []
        )

        confidence = (
            0.96
            if target
            and operation != "unknown"
            else 0.70
            if target
            else 0.35
        )

        return IntentResult(
            intent=self._build_intent_name(
                operation=operation,
                target=target,
                user_prompt=text,
            ),
            domain=domain,
            operation=operation,
            target=target,
            entities=entities,
            metrics=[],
            filters=self._infer_filters(
                text
            ),
            time_range=self._infer_time_range(
                text
            ),
            location=None,
            requested_output=requested_output,
            requested_components=components,
            confidence=confidence,
        )

    # ========================================================
    # OPERATION INFERENCE
    # ========================================================

    def _infer_operation(
        self,
        text: str,
    ) -> str:

        text = self._normalize_text(
            text
        )

        # UI-specific modifications are deliberately
        # NOT classified here as generic business "add".
        #
        # "add a bar chart" is a UI modification and the
        # modification detector owns that decision.
        if any(
            phrase in text
            for phrase in (
                "add a bar chart",
                "add bar chart",
                "add a line chart",
                "add line chart",
                "add a pie chart",
                "add pie chart",
                "remove the bar chart",
                "remove bar chart",
                "remove the line chart",
                "remove line chart",
                "remove the pie chart",
                "remove pie chart",
            )
        ):
            return "modify"

        if any(
            phrase in text
            for phrase in (
                "how many",
                "count ",
                "number of",
            )
        ):
            return "count"

        if any(
            word in text
            for word in (
                "delete",
                "remove",
            )
        ):
            return "delete"

        if any(
            phrase in text
            for phrase in (
                "update ",
                "edit ",
                "change ",
                "modify ",
            )
        ):
            return "update"

        if any(
            phrase in text
            for phrase in (
                "create ",
                "new ",
                "create a ",
                "create an ",
            )
        ):
            return "create"

        # "add a new purchase order" is business creation,
        # not UI modification.
        if re.search(
            r"\badd\s+(?:a\s+|an\s+|the\s+)?"
            r"(?:new\s+)?"
            r"(purchase order|purchase requisition|supplier|"
            r"employee|customer|product|sales order)\b",
            text,
        ):
            return "create"

        if any(
            phrase in text
            for phrase in (
                "compare ",
                "compare the ",
                "comparison of",
            )
        ):
            return "compare"

        if any(
            phrase in text
            for phrase in (
                "summarize ",
                "summary of",
                "give me a summary",
            )
        ):
            return "summarize"

        if any(
            phrase in text
            for phrase in (
                "analyze ",
                "analysis of",
                "analyse ",
                "analyse",
            )
        ):
            return "analyze"

        if any(
            phrase in text
            for phrase in (
                "search ",
                "look up ",
                "find ",
                "latest ",
                "current ",
                "what is ",
                "who is ",
                "where is ",
                "when is ",
            )
        ):
            return "search"

        if any(
            word in text
            for word in (
                "show",
                "display",
                "list",
                "view",
                "give me",
                "fetch",
                "get",
            )
        ):
            return "read"

        if "filter" in text:
            return "filter"

        return "unknown"

    # ========================================================
    # FILTER / TIME INFERENCE
    # ========================================================

    def _infer_filters(
        self,
        text: str,
    ) -> list[str]:

        filters: list[str] = []

        known_filters = (
            "pending",
            "approved",
            "rejected",
            "active",
            "inactive",
            "completed",
            "cancelled",
        )

        for value in known_filters:

            if re.search(
                rf"\b{re.escape(value)}\b",
                text,
            ):
                filters.append(
                    value
                )

        return filters

    def _infer_time_range(
        self,
        text: str,
    ) -> str | None:

        patterns = (
            r"last\s+\d+\s+(?:day|days|week|weeks|month|months|year|years)",
            r"this\s+(?:day|week|month|year)",
            r"today",
            r"yesterday",
            r"tomorrow",
            r"this quarter",
            r"last quarter",
        )

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
            )

            if match:
                return match.group(
                    0
                )

        return None

    # ========================================================
    # INTENT NAME
    # ========================================================

    @staticmethod
    def _build_intent_name(
        *,
        operation: str,
        target: str | None,
        user_prompt: str,
    ) -> str:

        if target:

            prefix = {
                "read": "view",
                "search": "search",
                "count": "count",
                "create": "create",
                "update": "update",
                "delete": "delete",
                "remove": "remove",
                "modify": "modify",
                "compare": "compare",
                "summarize": "summarize",
                "analyze": "analyze",
                "filter": "filter",
            }.get(
                operation,
                operation,
            )

            return (
                f"{prefix}_{target}"
            )

        if user_prompt:
            return "general_information"

        return "unknown"

    # ========================================================
    # PROMPT
    # ========================================================

    @staticmethod
    def _build_prompt(
        user_prompt: str,
    ) -> str:

        example = {
            "intent": "view_purchase_orders",
            "domain": "procurement",
            "operation": "read",
            "target": "purchase_order",
            "entities": [
                "purchase_order"
            ],
            "metrics": [],
            "filters": [],
            "time_range": None,
            "location": None,
            "requested_output": "table",
            "requested_components": [
                "heading",
                "table",
            ],
            "confidence": 0.96,
        }

        example_json = json.dumps(
            example,
            indent=2,
            ensure_ascii=False,
        )

        return f"""
You are ZenUI's semantic intent intelligence layer.

Understand the user's request and return ONLY valid JSON.

Do not answer the user.
Do not generate UI code.
Do not generate OpenUI Lang.
Do not invent data.

Your output is consumed by:
- resource planning
- tool selection
- result normalization
- dynamic UI planning
- conversational UI modification

============================================================
CANONICAL SEMANTIC CONTRACT
============================================================

intent:
A concise machine-readable description of the requested task.

domain:
The business or information domain.

Possible values include:
procurement
sales
finance
hr
inventory
customer
operations
weather
travel
general

operation:
One of:
create
read
update
delete
add
remove
modify
compare
search
filter
count
summarize
analyze
unknown

target:
The canonical singular entity.

Examples:
purchase_order
purchase_requisition
supplier
employee
customer
weather
product
sales_order
sale

entities:
Canonical entities explicitly involved.

metrics:
Requested measurements or KPIs.

filters:
Requested filters such as pending, approved, active, etc.

time_range:
Requested temporal constraint.

location:
Requested geographical location.

requested_output:
One of:
information
form
table
chart
dashboard
profile
detail
list
calendar
timeline
map
comparison
summary
unknown

requested_components:
Only components genuinely implied by the request.

Allowed:
text
heading
card
kpi
table
bar_chart
line_chart
pie_chart
form
input
select
button
badge
tabs
grid
stack
alert
progress

============================================================
SEMANTIC RULES
============================================================

1. Normalize singular/plural entities.

"purchase orders"
-> target = "purchase_order"

"purchase requisitions"
-> target = "purchase_requisition"

"employees"
-> target = "employee"

2. Choose the domain from semantic meaning.

3. "show", "display", "list", "view", "give me"
normally mean operation = "read".

4. "how many", "count", "number of"
normally mean operation = "count".

5. "create", "new", "add a new purchase order"
normally mean business operation = "create".

6. UI requests are different from business operations.

"add a bar chart"
is a UI modification.

Do NOT interpret it as creating a business entity.

7. "remove the bar chart"
is a UI modification.

8. Explicit output requests must be respected.

"show purchase orders as a table"
-> requested_output = "table"

"show sales as a bar chart"
-> requested_output = "chart"
-> requested_components includes "bar_chart"

9. Do not create unnecessary components.

10. Do not create a dashboard unless the user explicitly
asks for a dashboard, overview, executive view, or equivalent.

11. target must always be singular and canonical whenever
the entity is known.

============================================================
EXAMPLE
============================================================

User:
Show purchase orders

Expected semantic result:

{example_json}

============================================================
USER REQUEST
============================================================

{user_prompt}

Return JSON only.
"""

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _contains_phrase(
        text: str,
        phrase: str,
    ) -> bool:

        if " " in phrase:
            return phrase in text

        return bool(
            re.search(
                rf"\b{re.escape(phrase)}\b",
                text,
            )
        )

    @staticmethod
    def _clean_string(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        if isinstance(
            value,
            str,
        ):
            return value.strip()

        return str(value).strip()

    @staticmethod
    def _string_list(
        value: Any,
    ) -> list[str]:

        if not isinstance(
            value,
            list,
        ):
            return []

        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    @staticmethod
    def _list_value(
        value: Any,
    ) -> list[Any]:

        if not isinstance(
            value,
            list,
        ):
            return []

        return value

    @staticmethod
    def _confidence(
        value: Any,
    ) -> float:

        try:

            confidence = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return 0.0

        return max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

    @staticmethod
    def _unique(
        values: list[str],
    ) -> list[str]:

        result: list[str] = []

        for value in values:

            if value not in result:
                result.append(
                    value
                )

        return result