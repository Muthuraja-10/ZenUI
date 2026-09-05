from __future__ import annotations

from typing import Any, Callable

from app.tools.tool_models import (
    ToolDefinition,
)


ToolFunction = Callable[..., Any]


class RegisteredTool:

    def __init__(
        self,
        definition: ToolDefinition,
        function: ToolFunction,
    ) -> None:

        self.definition = definition

        self.function = function


class ToolRegistry:

    def __init__(self) -> None:

        self._tools: dict[
            str,
            RegisteredTool,
        ] = {}

    # ========================================================
    # REGISTER
    # ========================================================

    def register(
        self,
        definition: ToolDefinition,
        function: ToolFunction,
    ) -> None:

        name = (
            definition.name
            .strip()
            .lower()
        )

        if not name:

            raise ValueError(
                "Tool name cannot be empty."
            )

        if name in self._tools:

            raise ValueError(
                f"Tool already registered: {name}"
            )

        self._tools[name] = RegisteredTool(
            definition=definition,
            function=function,
        )

    # ========================================================
    # GET
    # ========================================================

    def get(
        self,
        name: str,
    ) -> RegisteredTool:

        normalized = (
            name or ""
        ).strip().lower()

        if normalized not in self._tools:

            raise ValueError(
                f"Unknown tool: {name}"
            )

        return self._tools[
            normalized
        ]

    # ========================================================
    # LIST
    # ========================================================

    def list_tools(
        self,
    ) -> list[ToolDefinition]:

        return [
            registered.definition
            for registered
            in self._tools.values()
        ]

    # ========================================================
    # NAMES
    # ========================================================

    def names(self) -> list[str]:

        return list(
            self._tools.keys()
        )

    # ========================================================
    # DESCRIPTIONS
    # ========================================================

    def describe(
        self,
    ) -> list[dict[str, Any]]:

        return [
            {
                "name": (
                    registered.definition.name
                ),
                "description": (
                    registered.definition.description
                ),
                "parameters": (
                    registered.definition.parameters
                ),
            }
            for registered
            in self._tools.values()
        ]