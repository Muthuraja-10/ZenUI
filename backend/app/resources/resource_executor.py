from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.resources.resource_registry import (
    get_resource,
    normalize_resource,
)


# ============================================================
# RESOURCE RESULT
# ============================================================

class ResourceResult(BaseModel):

    resource: str

    operation: str

    parameters: dict[str, Any] = Field(
        default_factory=dict
    )

    success: bool

    data: dict[str, Any] = Field(
        default_factory=dict
    )

    error: str | None = None


# ============================================================
# OPERATION ALIASES
# ============================================================

OPERATION_ALIASES: dict[
    str,
    str,
] = {
    "read": "list",
    "get": "list",
    "fetch": "list",
    "show": "list",
    "view": "list",
    "list": "list",
}


# ============================================================
# NORMALIZE OPERATION
# ============================================================

def normalize_operation(
    operation: str | None,
) -> str:

    normalized = (
        operation or "list"
    ).strip().lower()

    return OPERATION_ALIASES.get(
        normalized,
        normalized,
    )


# ============================================================
# RESOURCE EXECUTOR
# ============================================================

class ResourceExecutor:

    async def execute(
        self,
        resource: str,
        operation: str = "list",
        parameters: dict[str, Any] | None = None,
    ) -> ResourceResult:

        parameters = (
            parameters or {}
        )

        try:

            # ------------------------------------------------
            # NORMALIZE RESOURCE
            # ------------------------------------------------

            normalized_resource = (
                normalize_resource(
                    resource
                )
            )

            # ------------------------------------------------
            # NORMALIZE OPERATION
            # ------------------------------------------------

            normalized_operation = (
                normalize_operation(
                    operation
                )
            )

            # ------------------------------------------------
            # CURRENT DEMO SUPPORT
            #
            # We intentionally support READ/LIST only.
            # CRUD will be added later.
            # ------------------------------------------------

            if normalized_operation != "list":

                raise ValueError(
                    "Unsupported resource operation: "
                    f"{operation}"
                )

            # ------------------------------------------------
            # GET RESOURCE FUNCTION
            # ------------------------------------------------

            function = get_resource(
                normalized_resource
            )

            # ------------------------------------------------
            # EXECUTE RESOURCE
            # ------------------------------------------------

            data = function(
                **parameters
            )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            return ResourceResult(
                resource=normalized_resource,
                operation=normalized_operation,
                parameters=parameters,
                success=True,
                data={
                    normalized_resource: data
                },
            )

        except Exception as error:

            # ------------------------------------------------
            # FAILURE
            # ------------------------------------------------

            return ResourceResult(
                resource=(
                    normalize_resource(resource)
                    if resource
                    else ""
                ),
                operation=(
                    normalize_operation(operation)
                ),
                parameters=parameters,
                success=False,
                data={},
                error=str(error),
            )