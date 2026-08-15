from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class ActionRoute(str, Enum):
    EXECUTE_AUTOMATICALLY = "EXECUTE_AUTOMATICALLY"
    PREPARE_FOR_HUMAN_REVIEW = "PREPARE_FOR_HUMAN_REVIEW"
    CANNOT_EXECUTE = "CANNOT_EXECUTE"
    REQUIRES_CLARIFICATION = "REQUIRES_CLARIFICATION"


class ToolParams(BaseModel):
    url: Optional[str] = Field(None, description="URL for web_check")
    recipient: Optional[str] = Field(None, description="Recipient name or email for draft_communication")
    context: Optional[str] = Field(None, description="Context or instructions for draft_communication")
    due_date_or_duration: Optional[str] = Field(None, description="Duration or date for simulate_reminder")
    query: Optional[str] = Field(None, description="Search query for search_stored_work")


class ActionItem(BaseModel):
    description: str = Field(
        ...,
        description="Specific action that needs to be performed"
    )

    automatable: bool = Field(
        ...,
        description="Whether the action can be performed automatically"
    )

    route: ActionRoute = Field(
        ...,
        description="How the agent should route this action"
    )

    reason: str = Field(
        ...,
        description="Brief reason for the selected execution route"
    )

    tool_name: Optional[str] = Field(
        None,
        description="The name of the tool to execute: 'web_check', 'draft_communication', 'generate_markdown_brief', 'simulate_reminder', 'search_stored_work', or null if none match"
    )

    tool_params: Optional[ToolParams] = Field(
        None,
        description="Parameters for the tool"
    )


class PriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WorkInterpretation(BaseModel):
    title: str
    summary: str
    priority: PriorityEnum
    deadline: Optional[str] = None

    action_items: List[ActionItem] = Field(
        default_factory=list
    )

    missing_information: List[str] = Field(
        default_factory=list
    )

    requires_human_confirmation: List[str] = Field(
        default_factory=list
    )