from __future__ import annotations

from typing import Any

from app.resources.resource_executor import (
    ResourceExecutor,
)

from app.resources.resource_registry import (
    list_resources,
)

from app.tools.tool_models import (
    ToolDefinition,
)


# ============================================================
# TOOL DEFINITION BUILDER
# ============================================================

def _build_tool_definition() -> ToolDefinition:

    resources = list_resources()

    properties: dict[str, Any] = {

        "resource": {

            "type": "string",

            "description": (
                "Exact name of an available "
                "internal enterprise resource."
            ),
        },

        "operation": {

            "type": "string",

            "description": (
                "Operation supported by the "
                "internal resource."
            ),

            "enum": [
                "list"
            ],

            "default": "list",
        },

        "parameters": {

            "type": "object",

            "description": (
                "Resource-specific filtering "
                "parameters."
            ),

        },
    }

    if resources:

        properties["resource"]["enum"] = resources

    return ToolDefinition(

        name="internal_resource",

        description=(
            "Retrieve structured enterprise "
            "data from a registered internal "
            "resource. "
            "Use operation=list to retrieve "
            "enterprise records. "
            "The resource name must exactly "
            "match one of the registered resources."
        ),

        parameters={

            "type": "object",

            "properties": properties,

            "required": [
                "resource"
            ],
        },
    )


# ============================================================
# TOOL DEFINITION
# ============================================================

INTERNAL_RESOURCE_TOOL = (
    _build_tool_definition()
)


# ============================================================
# INTERNAL RESOURCE TOOL
# ============================================================

class InternalResourceTool:

    def __init__(self) -> None:

        self.executor = (
            ResourceExecutor()
        )

    # ========================================================
    # EXECUTE
    # ========================================================

    async def execute(
        self,
        resource: str,
        operation: str = "list",
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        resource = (
            resource or ""
        ).strip()

        if not resource:

            raise ValueError(
                "Resource name cannot be empty."
            )

        operation = (
            operation or "list"
        ).strip().lower()

        parameters = (
            parameters or {}
        )

        # ----------------------------------------------------
        # Strict operation validation
        # ----------------------------------------------------

        if operation != "list":

            raise ValueError(
                f"Unsupported internal resource "
                f"operation: {operation}. "
                f"Supported operation: list"
            )

        # ----------------------------------------------------
        # Strict resource validation
        # ----------------------------------------------------

        available_resources = list_resources()

        if resource not in available_resources:

            raise ValueError(
                f"Unknown resource: {resource}. "
                f"Available resources: "
                f"{available_resources}"
            )

        # ----------------------------------------------------
        # Execute
        # ----------------------------------------------------

        result = await self.executor.execute(
            resource=resource,
            operation=operation,
            parameters=parameters,
        )

        if not result.success:

            raise RuntimeError(
                result.error
                or "Internal resource execution failed."
            )

        return result.data