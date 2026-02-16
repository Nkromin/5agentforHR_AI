"""Orchestrator Agent - Classifies user intent and routes to appropriate agent."""
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from agents.state import AgentState
import config
import json
import re


ORCHESTRATOR_PROMPT = """You are an intent classifier for an HR system. Your ONLY job is to classify user intent.

CLASSIFICATION RULES:
- POLICY_QUERY: User is asking INFORMATIONAL questions about policies, rules, procedures, entitlements, benefits, or guidelines. This includes questions about leave policies, sick leave, password policies, remote work, benefits, etc.
- ACTION_REQUEST: User EXPLICITLY wants to PERFORM an action. They must use action words like "check my balance", "create a ticket", "submit a request", "book", "register", etc.
- UNKNOWN: Query is unrelated to HR (e.g., weather, flights, restaurants) or completely unclear.

CRITICAL DISTINCTIONS:
- "What is the password policy?" → POLICY_QUERY (asking about a policy)
- "How many sick days do I get?" → POLICY_QUERY (asking about entitlement)
- "I have fever, can I take leave?" → POLICY_QUERY (asking about leave rules)
- "Check my leave balance" → ACTION_REQUEST (explicit action verb)
- "Create a ticket for laptop issue" → ACTION_REQUEST (explicit action verb)
- "Book flight tickets" → UNKNOWN (not HR related)
- "What's the weather?" → UNKNOWN (not HR related)

You MUST respond with ONLY valid JSON in this exact format:
{"intent": "POLICY_QUERY"}
or
{"intent": "ACTION_REQUEST"}
or
{"intent": "UNKNOWN"}

Do NOT include any other text, explanation, or markdown. ONLY the JSON object."""


class OrchestratorAgent:
    """Orchestrator agent that classifies user intent using strict JSON output."""

    def __init__(self, llm: ChatGroq):
        """Initialize with shared LLM instance."""
        self.llm = llm

    def _parse_intent(self, response_text: str) -> str:
        """
        Safely parse intent from LLM response.

        Args:
            response_text: Raw LLM response

        Returns:
            Validated intent string
        """
        # Try to extract JSON from response
        try:
            # First, try direct JSON parse
            data = json.loads(response_text.strip())
            intent = data.get("intent", "").upper()
            if intent in ["POLICY_QUERY", "ACTION_REQUEST", "UNKNOWN"]:
                return intent
        except json.JSONDecodeError:
            pass

        # Try to find JSON in response using regex
        json_match = re.search(r'\{[^}]+\}', response_text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                intent = data.get("intent", "").upper()
                if intent in ["POLICY_QUERY", "ACTION_REQUEST", "UNKNOWN"]:
                    return intent
            except json.JSONDecodeError:
                pass

        # Fallback: look for intent keywords in response
        response_upper = response_text.upper()
        if "POLICY_QUERY" in response_upper:
            return "POLICY_QUERY"
        elif "ACTION_REQUEST" in response_upper:
            return "ACTION_REQUEST"

        # Default to UNKNOWN for safety (not ACTION_REQUEST!)
        return "UNKNOWN"

    def run(self, state: AgentState) -> AgentState:
        """
        Classify user intent and determine routing.

        Args:
            state: Current agent state

        Returns:
            Updated state with intent and routing information
        """
        user_input = state["user_input"]

        # Initialize debug log
        debug_log = state.get("debug_log", []) or []
        debug_log.append(f"[ORCHESTRATOR] Processing: {user_input}")

        messages = [
            SystemMessage(content=ORCHESTRATOR_PROMPT),
            HumanMessage(content=f"Classify this query: {user_input}")
        ]

        response = self.llm.invoke(messages)
        response_text = response.content.strip()

        debug_log.append(f"[ORCHESTRATOR] Raw response: {response_text}")

        # Parse intent safely
        intent = self._parse_intent(response_text)

        debug_log.append(f"[ORCHESTRATOR] Classified intent: {intent}")

        # Determine next agent based on intent
        if intent == "POLICY_QUERY":
            next_agent = "policy"
        elif intent == "ACTION_REQUEST":
            next_agent = "action"
        else:
            next_agent = "fallback"

        debug_log.append(f"[ORCHESTRATOR] Routing to: {next_agent}")

        state["intent"] = intent
        state["next_agent"] = next_agent
        state["debug_log"] = debug_log

        return state

