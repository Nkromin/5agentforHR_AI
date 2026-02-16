"""LangGraph workflow definition with memory and proper routing."""
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from agents.state import AgentState
from agents.orchestrator import OrchestratorAgent
from agents.policy_agent import PolicyAgent
from agents.action_agent import ActionAgent
import config


# Safe fallback message for UNKNOWN intents
SAFE_FALLBACK_MESSAGE = """I'm only able to assist with HR policies and specific HR actions like creating tickets or checking leave balance.

For HR policy questions, you can ask about:
- Leave policies (annual, sick, parental)
- Remote work policies
- Benefits and compensation
- IT security and password policies
- Expense reimbursement
- Code of conduct

For HR actions, you can:
- Check your leave balance (requires employee ID)
- Create an HR support ticket"""


def create_hr_graph(vector_store=None):
    """
    Create the LangGraph workflow for HR automation.

    Args:
        vector_store: FAISS vector store for policy RAG

    Returns:
        Compiled LangGraph workflow
    """
    # Initialize single shared LLM instance
    print("[GRAPH] Initializing Groq LLM...")
    llm = ChatGroq(
        api_key=config.GROQ_API_KEY,
        model=config.MODEL_NAME,
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS
    )
    print(f"[GRAPH] Using model: {config.MODEL_NAME}")

    # Initialize agents with shared LLM
    orchestrator = OrchestratorAgent(llm)
    policy_agent = PolicyAgent(llm, vector_store)
    action_agent = ActionAgent(llm)

    # Define node functions
    def orchestrator_node(state: AgentState) -> AgentState:
        """Orchestrator node - classifies intent."""
        print("\n" + "="*50)
        print("[NODE] ORCHESTRATOR")
        print("="*50)
        result = orchestrator.run(state)
        print(f"[NODE] Intent: {result.get('intent')}")
        print(f"[NODE] Routing to: {result.get('next_agent')}")
        return result

    def policy_node(state: AgentState) -> AgentState:
        """Policy agent node - RAG-based Q&A."""
        print("\n" + "="*50)
        print("[NODE] POLICY AGENT")
        print("="*50)
        result = policy_agent.run(state)

        # Set final answer from policy response
        if result.get("policy_response"):
            result["final_answer"] = result["policy_response"]

        # Log retrieved sources
        sources = result.get("retrieved_sources", [])
        print(f"[NODE] Retrieved sources: {sources}")
        return result

    def action_node(state: AgentState) -> AgentState:
        """Action agent node - tool execution."""
        print("\n" + "="*50)
        print("[NODE] ACTION AGENT")
        print("="*50)
        result = action_agent.run(state)

        # Set final answer from action response
        if result.get("action_response"):
            result["final_answer"] = result["action_response"]

        # Log tool calls
        tool_calls = result.get("tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                print(f"[NODE] Tool executed: {tc.get('tool')} -> {tc.get('result', {}).get('message', 'N/A')}")
        else:
            print("[NODE] No tools executed")
        return result

    def fallback_node(state: AgentState) -> AgentState:
        """Safe fallback for unknown/unrelated queries."""
        print("\n" + "="*50)
        print("[NODE] FALLBACK (UNKNOWN Intent)")
        print("="*50)

        debug_log = state.get("debug_log", []) or []
        debug_log.append("[FALLBACK] Returning safe fallback message")

        state["final_answer"] = SAFE_FALLBACK_MESSAGE
        state["debug_log"] = debug_log

        print("[NODE] Returning safe fallback message")
        return state

    def finalize_node(state: AgentState) -> AgentState:
        """
        Finalize the response and update conversation memory.
        Replaces the compliance agent for simplicity.
        """
        print("\n" + "="*50)
        print("[NODE] FINALIZE")
        print("="*50)

        # Ensure we have a final answer
        if not state.get("final_answer"):
            state["final_answer"] = "I apologize, but I couldn't process your request. Please try asking about HR policies or specific actions."

        # Add assistant message to memory for next turn
        final_answer = state["final_answer"]
        state["messages"] = [AIMessage(content=final_answer)]

        print(f"[NODE] Final answer length: {len(final_answer)} chars")

        # Print debug log
        debug_log = state.get("debug_log", [])
        if debug_log:
            print("\n[DEBUG LOG]")
            for log in debug_log[-10:]:  # Last 10 entries
                print(f"  {log}")

        return state

    # Define routing function
    def route_after_orchestrator(state: AgentState) -> str:
        """Route to appropriate agent based on intent."""
        next_agent = state.get("next_agent", "fallback")
        return next_agent

    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("policy", policy_node)
    workflow.add_node("action", action_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("finalize", finalize_node)

    # Set entry point
    workflow.set_entry_point("orchestrator")

    # Add conditional edges from orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "policy": "policy",
            "action": "action",
            "fallback": "fallback"
        }
    )

    # Route all agents to finalize
    workflow.add_edge("policy", "finalize")
    workflow.add_edge("action", "finalize")
    workflow.add_edge("fallback", "finalize")

    # End after finalize
    workflow.add_edge("finalize", END)

    # Compile the graph
    app = workflow.compile()
    print("[GRAPH] Workflow compiled successfully")

    return app

