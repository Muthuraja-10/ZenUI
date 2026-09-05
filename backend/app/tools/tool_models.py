from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# TOOL DEFINITION
# ============================================================

class ToolDefinition(BaseModel):

    name: str

    description: str

    parameters: dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# TOOL CALL
# ============================================================

class ToolCall(BaseModel):

    tool_name: str

    arguments: dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# TOOL RESULT
# ============================================================

class ToolResult(BaseModel):

    success: bool = False

    tool_name: str

    data: Any = None

    error: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# TOOL AGENT RESULT
# ============================================================

class ToolAgentResult(BaseModel):

    success: bool = False

    tool_calls: list[ToolCall] = Field(
        default_factory=list
    )

    results: list[ToolResult] = Field(
        default_factory=list
    )

    data: dict[str, Any] = Field(
        default_factory=dict
    )

    message: str | None = None