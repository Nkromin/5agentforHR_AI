"""Compliance Agent - Validates responses and ensures no hallucination."""
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage
from agents.state import AgentState


COMPLIANCE_AGENT_PROMPT = """You are a Compliance Validator. Your job is to verify that the answer is grounded in facts.

Original Question: {question}

Retrieved Context: {context}

Proposed Answer: {answer}

RULES:
1. If the answer is grounded in the retrieved context or tool output, mark it as APPROVED
2. If the answer contains information NOT in the context, mark it as REJECTED
3. For tool outputs, always approve if the tool executed successfully
4. If rejected, provide a safe fallback response

Respond in this format:
STATUS: APPROVED or REJECTED
REASON: brief explanation
FINAL: the final answer to give to the user (either the original answer if approved, or a safe fallback if rejected)"""


class ComplianceAgent:
    """Compliance agent that validates responses."""

    def __init__(self, llm: ChatGroq):
        """
        Initialize with shared LLM instance.

        Args:
            llm: Shared Groq LLM instance
        """
        self.llm = llm

    def run(self, state: AgentState) -> AgentState:
        """
        Validate the response and ensure no hallucination.

        Args:
            state: Current agent state

        Returns:
            Updated state with validated final response
        """
        user_input = state["user_input"]

        # Determine which response to validate
        if state.get("policy_response"):
            answer = state["policy_response"]
            context = state.get("retrieved_context", "No context")
        elif state.get("action_response"):
            answer = state["action_response"]
            context = f"Tool execution: {state.get('tool_calls', [])}"
        else:
            # Unknown or fallback
            state["final_response"] = "I apologize, but I'm not sure how to help with that. Please ask about HR policies or request specific actions like checking leave balance or creating tickets."
            state["compliance_check"] = "FALLBACK"
            return state

        # For action responses with successful tool calls, approve directly
        if state.get("tool_calls") and len(state.get("tool_calls", [])) > 0:
            state["final_response"] = answer
            state["compliance_check"] = "APPROVED - Tool execution"
            return state

        # Validate policy responses
        prompt = COMPLIANCE_AGENT_PROMPT.format(
            question=user_input,
            context=context,
            answer=answer
        )

        messages = [HumanMessage(content=prompt)]
        response = self.llm.invoke(messages)
        response_text = response.content.strip()

        # Parse response
        final_answer = answer  # Default to original answer

        if "FINAL:" in response_text:
            final_answer = response_text.split("FINAL:")[-1].strip()

        if "STATUS: REJECTED" in response_text:
            state["compliance_check"] = "REJECTED"
            # Provide safe fallback
            if not final_answer or final_answer == answer:
                final_answer = "I don't have enough information in the HR policies to answer that question accurately. Please contact HR directly for clarification."
        else:
            state["compliance_check"] = "APPROVED"

        state["final_response"] = final_answer

        return state

