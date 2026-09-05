from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.llm.llm_service import LLMService
from app.tools.tool_models import ToolCall
from app.tools.tool_registry import ToolRegistry


# ============================================================
# TOOL SELECTION RESPONSE
# ============================================================

class ToolSelection(BaseModel):

    tool_name: str

    arguments: dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# TOOL SELECTOR
# ============================================================

class ToolSelector:
    """
    LLM-based tool selector.

    Responsibilities:

        User request
             ↓
        inspect registered tools
             ↓
        select one registered tool
             ↓
        validate tool arguments
             ↓
        ToolCall

    This class does NOT execute tools.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        llm: LLMService | None = None,
    ) -> None:

        self.registry = registry

        self.llm = (
            llm
            or LLMService()
        )

    # ========================================================
    # SELECT
    # ========================================================

    async def select(
        self,
        user_prompt: str,
        intent: Any = None,
    ) -> ToolCall | None:

        prompt = self._build_prompt(
            user_prompt=user_prompt,
            intent=intent,
        )

        try:

            raw = await self.llm.generate(
                prompt,
                temperature=0.0,
                max_tokens=1500,
            )

            print()
            print("========== TOOL SELECTOR RAW ==========")
            print(raw)
            print("========================================")

            selection = self._parse_selection(
                raw
            )

            if selection is None:

                print(
                    "Tool selector returned invalid JSON."
                )

                return None

            # ------------------------------------------------
            # Normalize tool name
            # ------------------------------------------------

            tool_name = (
                selection.tool_name
                .strip()
                .lower()
            )

            # ------------------------------------------------
            # Validate tool exists
            # ------------------------------------------------

            registered = self.registry.get(
                tool_name
            )

            # ------------------------------------------------
            # Validate arguments
            # ------------------------------------------------

            arguments = (
                selection.arguments
                or {}
            )

            validation_error = (
                self._validate_arguments(
                    registered.definition.parameters,
                    arguments,
                )
            )

            if validation_error:

                print()
                print(
                    "========== TOOL ARGUMENT ERROR =========="
                )

                print(
                    validation_error
                )

                print(
                    "=========================================="
                )

                return None

            # ------------------------------------------------
            # Final ToolCall
            # ------------------------------------------------

            tool_call = ToolCall(
                tool_name=tool_name,
                arguments=arguments,
            )

            print()
            print(
                "========== TOOL CALL =========="
            )

            print(
                "TOOL:",
                tool_call.tool_name,
            )

            print(
                "ARGUMENTS:",
                tool_call.arguments,
            )

            print(
                "==============================="
            )

            return tool_call

        except Exception as error:

            print()
            print(
                "========== TOOL SELECTOR ERROR =========="
            )

            print(
                error
            )

            print(
                "=========================================="
            )

            return None

    # ========================================================
    # BUILD PROMPT
    # ========================================================

    def _build_prompt(
        self,
        user_prompt: str,
        intent: Any = None,
    ) -> str:

        tools = (
            self.registry.list_tools()
        )

        tool_descriptions: list[
            dict[str, Any]
        ] = []

        for tool in tools:

            tool_descriptions.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            )

        intent_data = (
            self._to_dict(intent)
        )

        return f"""
You are the ZenUI Tool Selection Engine.

Your ONLY responsibility is to select the best
REGISTERED tool for the user's request.

You MUST NOT:

- answer the user
- generate UI
- generate OpenUI
- execute tools
- invent tools
- invent tool names
- invent parameter values
- invent resource names
- invent operation names
- use values that are not allowed by the tool schema

You may ONLY select from the tools listed below.

============================================================
REGISTERED TOOLS
============================================================

{json.dumps(
    tool_descriptions,
    indent=2,
    ensure_ascii=False,
)}

============================================================
USER REQUEST
============================================================

{user_prompt}

============================================================
SEMANTIC INTENT
============================================================

{json.dumps(
    intent_data,
    indent=2,
    ensure_ascii=False,
    default=str,
)}

============================================================
STRICT RULES
============================================================

1. tool_name MUST exactly match a registered tool.

2. Every argument MUST conform to the selected tool's
   parameter schema.

3. NEVER invent a resource name.

4. NEVER invent an operation.

5. If a parameter has an enum, you MUST select one of
   the enum values.

6. Do not convert "list" into "read".

7. Do not convert resource names into singular/plural forms.

8. Do not add arguments that are not supported.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Required structure:

{{
    "tool_name": "registered_tool_name",
    "arguments": {{}}
}}

Do not return markdown.

Do not explain your decision.
"""

    # ========================================================
    # ARGUMENT VALIDATION
    # ========================================================

    @staticmethod
    def _validate_arguments(
        schema: dict[str, Any],
        arguments: dict[str, Any],
    ) -> str | None:

        if not isinstance(
            arguments,
            dict,
        ):

            return (
                "Tool arguments must be an object."
            )

        properties = (
            schema.get(
                "properties",
                {},
            )
        )

        required = (
            schema.get(
                "required",
                [],
            )
        )

        # ----------------------------------------------------
        # Required arguments
        # ----------------------------------------------------

        for name in required:

            if name not in arguments:

                return (
                    f"Missing required argument: {name}"
                )

        # ----------------------------------------------------
        # Unknown arguments
        # ----------------------------------------------------

        for name in arguments:

            if name not in properties:

                return (
                    f"Unknown tool argument: {name}"
                )

        # ----------------------------------------------------
        # Enum validation
        # ----------------------------------------------------

        for name, value in arguments.items():

            definition = properties.get(
                name,
                {},
            )

            enum_values = definition.get(
                "enum"
            )

            if (
                enum_values
                and value not in enum_values
            ):

                return (
                    f"Invalid value for '{name}': "
                    f"{value!r}. "
                    f"Allowed values: "
                    f"{enum_values}"
                )

        # ----------------------------------------------------
        # Basic object validation
        # ----------------------------------------------------

        for name, value in arguments.items():

            definition = properties.get(
                name,
                {},
            )

            expected_type = definition.get(
                "type"
            )

            if (
                expected_type == "object"
                and not isinstance(value, dict)
            ):

                return (
                    f"Argument '{name}' "
                    f"must be an object."
                )

            if (
                expected_type == "string"
                and not isinstance(value, str)
            ):

                return (
                    f"Argument '{name}' "
                    f"must be a string."
                )

        return None

    # ========================================================
    # PARSE
    # ========================================================

    @staticmethod
    def _parse_selection(
        raw: str | None,
    ) -> ToolSelection | None:

        if not raw:
            return None

        text = raw.strip()

        # ----------------------------------------------------
        # Remove markdown fences
        # ----------------------------------------------------

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        text = text.strip()

        # ----------------------------------------------------
        # Direct JSON
        # ----------------------------------------------------

        try:

            data = json.loads(
                text
            )

            if isinstance(
                data,
                dict,
            ):

                return ToolSelection.model_validate(
                    data
                )

        except Exception:
            pass

        # ----------------------------------------------------
        # Extract JSON object
        # ----------------------------------------------------

        start = text.find(
            "{"
        )

        end = text.rfind(
            "}"
        )

        if (
            start == -1
            or end == -1
            or end <= start
        ):

            return None

        candidate = text[
            start:end + 1
        ]

        try:

            data = json.loads(
                candidate
            )

            if not isinstance(
                data,
                dict,
            ):

                return None

            return ToolSelection.model_validate(
                data
            )

        except Exception:

            return None

    # ========================================================
    # TO DICT
    # ========================================================

    @staticmethod
    def _to_dict(
        value: Any,
    ) -> Any:

        if value is None:

            return {}

        if isinstance(
            value,
            dict,
        ):

            return value

        if hasattr(
            value,
            "model_dump",
        ):

            try:

                return value.model_dump()

            except Exception:

                pass

        return str(value)