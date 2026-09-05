from __future__ import annotations

from typing import Any

from app.resources.resource_registry import (
    normalize_resource,
)

from app.tools.internal_resource_tool import (
    INTERNAL_RESOURCE_TOOL,
    InternalResourceTool,
)

from app.tools.linkup_tool import (
    LINKUP_TOOL,
    LinkupTool,
)

from app.tools.serper_tool import (
    SERPER_TOOL,
    SerperTool,
)

from app.tools.tool_executor import (
    ToolExecutor,
)

from app.tools.tool_models import (
    ToolAgentResult,
    ToolCall,
)

from app.tools.tool_registry import (
    ToolRegistry,
)

from app.tools.tool_selector import (
    ToolSelector,
)


# ============================================================
# TOOL AGENT
# ============================================================


class ToolAgent:
    """
    ZenUI Tool Agent.

    Responsibilities:

        1. Discover registered tools.
        2. Ask the LLM-based selector which tool to use.
        3. Execute the selected tool.
        4. Return structured results.

    It does NOT:

        - detect sales
        - detect purchase orders
        - detect employees
        - detect customers
        - generate UI
        - generate OpenUI
    """

    def __init__(self) -> None:

        # ----------------------------------------------------
        # REGISTRY
        # ----------------------------------------------------

        self.registry = (
            ToolRegistry()
        )

        # ----------------------------------------------------
        # TOOL IMPLEMENTATIONS
        # ----------------------------------------------------

        self.internal_resource = (
            InternalResourceTool()
        )

        self.serper = (
            SerperTool()
        )

        self.linkup = (
            LinkupTool()
        )

        # ----------------------------------------------------
        # REGISTER
        # ----------------------------------------------------

        self._register_tools()

        # ----------------------------------------------------
        # EXECUTOR
        # ----------------------------------------------------

        self.executor = ToolExecutor(
            self.registry
        )

        # ----------------------------------------------------
        # SELECTOR
        # ----------------------------------------------------

        self.selector = ToolSelector(
            registry=self.registry
        )

    # ========================================================
    # REGISTER
    # ========================================================

    def _register_tools(
        self,
    ) -> None:

        self.registry.register(
            INTERNAL_RESOURCE_TOOL,
            self.internal_resource.execute,
        )

        self.registry.register(
            SERPER_TOOL,
            self.serper.execute,
        )

        self.registry.register(
            LINKUP_TOOL,
            self.linkup.execute,
        )

    # ========================================================
    # RUN
    # ========================================================

    async def run(
        self,
        user_prompt: str,
        intent: Any = None,
    ) -> ToolAgentResult:

        intent_name = (
            intent.get("intent", "")
            if isinstance(intent, dict)
            else getattr(intent, "intent", "")
        )

        if str(intent_name).strip().lower() in {
            "greeting",
            "capability_query",
        }:
            return ToolAgentResult(
                success=True,
                tool_calls=[],
                results=[],
                data={},
            )

        print()
        print(
            "========== ZENUI TOOL AGENT =========="
        )

        print(
            "USER:",
            user_prompt,
        )

        print(
            "AVAILABLE TOOLS:",
            self.registry.names(),
        )

        # ====================================================
        # SELECT
        # ====================================================

        selection = await self.selector.select(
            user_prompt=user_prompt,
            intent=intent,
        )

        # ====================================================
        # FALLBACK: DETERMINISTIC SELECTION
        # ====================================================

        if selection is None:

            print(
                "LLM selection failed. Using deterministic fallback..."
            )

            selection = (
                self._fallback_tool_selection(
                    user_prompt=user_prompt,
                    intent=intent,
                )
            )

        if selection is None:

            print(
                "NO TOOL SELECTED"
            )

            print(
                "========================================"
            )

            return ToolAgentResult(
                success=False,
                tool_calls=[],
                results=[],
                data={},
                message=(
                    "No suitable tool was selected."
                ),
            )

        # ====================================================
        # DEBUG
        # ====================================================

        print(
            "SELECTED TOOL:",
            selection.tool_name,
        )

        print(
            "ARGUMENTS:",
            selection.arguments,
        )

        # ====================================================
        # EXECUTE
        # ====================================================

        result = await self.executor.execute(
            selection
        )

        print(
            "TOOL SUCCESS:",
            result.success,
        )

        if not result.success:

            print(
                "TOOL ERROR:",
                result.error,
            )

        print(
            "========================================"
        )

        # ====================================================
        # DATA
        # ====================================================

        data: dict[str, Any] = {}

        if (
            result.success
            and isinstance(
                result.data,
                dict,
            )
        ):

            data = result.data

        # ====================================================
        # RESULT
        # ====================================================

        return ToolAgentResult(
            success=result.success,
            tool_calls=[
                selection
            ],
            results=[
                result
            ],
            data=data,
            message=(
                None
                if result.success
                else result.error
            ),
        )

    # ========================================================
    # FALLBACK TOOL SELECTION
    # ========================================================

    def _fallback_tool_selection(
        self,
        user_prompt: str,
        intent: Any = None,
    ) -> ToolCall | None:

        """
        Deterministic tool selection fallback when LLM fails.

        This ensures ZenUI remains functional even when:
        - Groq rate limit is hit
        - LLM service fails
        - LLM returns invalid JSON

        The selection is based purely on intent semantics,
        not on LLM interpretation.
        """

        if not intent:
            intent = {}

        intent_name = (
            intent.get("intent", "")
            if isinstance(intent, dict)
            else getattr(intent, "intent", "")
        )

        if str(intent_name).strip().lower() in {
            "greeting",
            "capability_query",
        }:
            return None

        # ====================================================
        # CHECK IF INTENT INDICATES INTERNAL RESOURCE
        # ====================================================

        raw_target = (
            intent.get("target", "")
            if isinstance(intent, dict)
            else getattr(intent, "target", "")
        )

        intent_target = str(
            raw_target or ""
        ).strip().lower()

        if intent_target:

            try:

                # Try to normalize the intent target to a
                # registered resource name
                normalized = (
                    normalize_resource(
                        intent_target
                    )
                )

                print(
                    f"FALLBACK: Using internal_resource "
                    f"based on intent target "
                    f"({intent_target} → {normalized})"
                )

                return ToolCall(
                    tool_name="internal_resource",
                    arguments={
                        "resource": normalized,
                    },
                )

            except (ValueError, KeyError):
                # Target is not a registered resource
                pass

        # ====================================================
        # CHECK USER PROMPT FOR KEYWORDS
        # ====================================================

        prompt_lower = (
            user_prompt or ""
        ).strip().lower()

        # Helper to detect keywords and normalize
        def try_resource(keywords: list[str], resource_name: str) -> ToolCall | None:

            if any(
                keyword in prompt_lower
                for keyword in keywords
            ):
                try:
                    normalized = (
                        normalize_resource(
                            resource_name
                        )
                    )

                    print(
                        f"FALLBACK: Detected keyword, "
                        f"using {normalized}"
                    )

                    return ToolCall(
                        tool_name="internal_resource",
                        arguments={
                            "resource": normalized,
                        },
                    )

                except (ValueError, KeyError):
                    pass

            return None

        # Try each resource type
        result = try_resource(
            [
                "purchase order",
                "purchase orders",
                "purchase requisition",
                "po ",
                "pos ",
            ],
            "purchase_order",
        )

        if result:
            return result

        result = try_resource(
            [
                "sale",
                "sales",
            ],
            "sales",
        )

        if result:
            return result

        result = try_resource(
            [
                "employee",
                "employees",
                "staff",
            ],
            "employee",
        )

        if result:
            return result

        result = try_resource(
            [
                "customer",
                "customers",
                "client",
                "clients",
            ],
            "customer",
        )

        if result:
            return result

        # ====================================================
        # DEFAULT: EXTERNAL SEARCH
        # ====================================================

        # If none of the internal keywords matched,
        # try external search (for questions like "What is OpenUI?")
        print(
            "FALLBACK: Using serper for external search"
        )

        return ToolCall(
            tool_name="serper",
            arguments={
                "query": user_prompt,
            },
        )