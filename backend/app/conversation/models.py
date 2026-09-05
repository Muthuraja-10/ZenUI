from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: str
    content: str

    # Generated OpenUI response
    ui: str | None = None

    # UI plan used to generate it
    ui_plan: dict[str, Any] = Field(
        default_factory=dict
    )

    # Data used by the resource layer
    resource_data: dict[str, Any] = Field(
        default_factory=dict
    )


class ConversationState(BaseModel):

    session_id: str

    messages: list[ConversationMessage] = Field(
        default_factory=list
    )

    current_ui: str | None = None

    current_ui_plan: dict[str, Any] = Field(
        default_factory=dict
    )

    current_resource_data: dict[str, Any] = Field(
        default_factory=dict
    )