"""State definition for the LangGraph workflow."""
from typing import TypedDict, List, Dict, Optional, Annotated
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """State that is passed between agents in the graph."""
    # Conversation messages (for memory - accumulates across turns)
    messages: Annotated[List[BaseMessage], operator.add]

    # Current user input
    user_input: str

    # Orchestrator output
    intent: Optional[str]  # POLICY_QUERY, ACTION_REQUEST, or UNKNOWN

    # Policy Agent output
    retrieved_context: Optional[str]
    retrieved_sources: Optional[List[str]]  # Document sources for debugging
    policy_response: Optional[str]

    # Action Agent output
    tool_calls: Optional[List[Dict]]
    action_response: Optional[str]

    # Final output
    final_answer: str

    # Routing info
    next_agent: Optional[str]

    # Debug info
    debug_log: Optional[List[str]]

