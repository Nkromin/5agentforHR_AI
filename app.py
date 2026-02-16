"""Streamlit frontend for HR Multi-Agent System."""
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from agents.graph import create_hr_graph
from rag.vector_store import initialize_vector_store
import config


# Page configuration
st.set_page_config(
    page_title="HR Multi-Agent System",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .agent-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    .orchestrator { background-color: #e3f2fd; color: #1976d2; }
    .policy { background-color: #f3e5f5; color: #7b1fa2; }
    .action { background-color: #e8f5e9; color: #388e3c; }
    .fallback { background-color: #fce4ec; color: #c2185b; }
    .finalize { background-color: #fff3e0; color: #f57c00; }
    .debug-box {
        background-color: #f5f5f5;
        border-radius: 0.5rem;
        padding: 0.5rem;
        font-size: 0.75rem;
        font-family: monospace;
        max-height: 200px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_system():
    """Load the HR system (cached)."""
    try:
        # Force rebuild vector store to ensure latest policies
        vector_store = initialize_vector_store(force_rebuild=True)
        graph = create_hr_graph(vector_store)
        return graph, True
    except Exception as e:
        st.error(f"Error initializing system: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None, False


def initialize_session_state():
    """Initialize Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "routing_history" not in st.session_state:
        st.session_state.routing_history = []
    if "conversation_memory" not in st.session_state:
        # Store LangChain messages for memory across turns
        st.session_state.conversation_memory = []


def display_agent_badge(agent_name: str):
    """Display agent badge with appropriate styling."""
    return f'<span class="agent-badge {agent_name.lower()}">{agent_name}</span>'


def process_query(graph, user_input: str, conversation_memory: list):
    """
    Process user query through the agent graph with memory.

    Args:
        graph: Compiled LangGraph workflow
        user_input: User's query
        conversation_memory: List of previous messages for context

    Returns:
        Final response and routing information
    """
    # Add current user message to memory
    current_message = HumanMessage(content=user_input)

    # Initialize state with conversation memory
    initial_state = {
        "messages": conversation_memory + [current_message],
        "user_input": user_input,
        "intent": None,
        "retrieved_context": None,
        "retrieved_sources": None,
        "policy_response": None,
        "tool_calls": None,
        "action_response": None,
        "final_answer": "",
        "next_agent": None,
        "debug_log": []
    }

    # Run the graph
    result = graph.invoke(initial_state)

    return result


def main():
    """Main Streamlit application."""
    # Header
    st.markdown('<div class="main-header">🤖 HR Multi-Agent Automation System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Powered by LangGraph + Groq + FAISS</div>', unsafe_allow_html=True)

    # Check API key
    if not config.GROQ_API_KEY:
        st.error("⚠️ GROQ_API_KEY not found in .env file. Please add it to continue.")
        st.stop()

    # Load system
    with st.spinner("🔄 Initializing HR Agent System..."):
        graph, success = load_system()

    if not success or graph is None:
        st.error("Failed to initialize system. Please check your configuration.")
        st.stop()

    st.success("✅ System initialized successfully!")

    # Initialize session state
    initialize_session_state()

    # Layout: Main chat area and sidebar
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("💬 Chat Interface")

        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("Ask about HR policies or request an action..."):
            # Add user message to display
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Process query with memory
            with st.chat_message("assistant"):
                with st.spinner("🤔 Processing..."):
                    result = process_query(
                        graph,
                        prompt,
                        st.session_state.conversation_memory
                    )

                    # Extract response (use final_answer instead of final_response)
                    final_response = result.get("final_answer", "I apologize, but I couldn't process your request.")

                    # Display response
                    st.markdown(final_response)

                    # Update conversation memory for next turn
                    st.session_state.conversation_memory.append(HumanMessage(content=prompt))
                    st.session_state.conversation_memory.append(AIMessage(content=final_response))

                    # Keep memory manageable (last 10 messages)
                    if len(st.session_state.conversation_memory) > 10:
                        st.session_state.conversation_memory = st.session_state.conversation_memory[-10:]

                    # Store routing info
                    routing_info = {
                        "query": prompt,
                        "intent": result.get("intent", "Unknown"),
                        "next_agent": result.get("next_agent", "Unknown"),
                        "tool_calls": result.get("tool_calls", []),
                        "sources": result.get("retrieved_sources", []),
                        "debug_log": result.get("debug_log", [])
                    }
                    st.session_state.routing_history.append(routing_info)

                    # Add assistant message to display
                    st.session_state.messages.append({"role": "assistant", "content": final_response})

    with col2:
        st.subheader("📊 System Monitor")

        # Display latest routing info
        if st.session_state.routing_history:
            latest = st.session_state.routing_history[-1]

            st.markdown("**Latest Query Analysis:**")
            st.markdown(f"**Intent:** `{latest['intent']}`")

            # Display agent flow
            st.markdown("**Agent Flow:**")
            agent_name = latest.get('next_agent', 'unknown')
            if agent_name:
                agent_name = agent_name.title()
            st.markdown(
                display_agent_badge("Orchestrator") + " → " +
                display_agent_badge(agent_name) + " → " +
                display_agent_badge("Finalize"),
                unsafe_allow_html=True
            )

            # Display sources if available
            sources = latest.get('sources', [])
            if sources:
                st.markdown("**Retrieved Sources:**")
                for src in sources[:3]:
                    st.markdown(f"- `{src}`")

            # Display tool calls if any
            if latest.get('tool_calls'):
                st.markdown("**Tool Calls:**")
                for tool_call in latest['tool_calls']:
                    st.json(tool_call)

            # Debug log expander
            debug_log = latest.get('debug_log', [])
            if debug_log:
                with st.expander("🔍 Debug Log"):
                    st.markdown('<div class="debug-box">', unsafe_allow_html=True)
                    for log in debug_log:
                        st.text(log)
                    st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        # Example queries
        st.markdown("**💡 Example Queries:**")
        examples = [
            "What is the password policy?",
            "How many sick leaves do I get?",
            "I have fever, can I take leave?",
            "Check my leave balance for EMP001",
            "Create a ticket for laptop issue",
            "What is the remote work policy?",
            "Book flight tickets"
        ]

        for example in examples:
            if st.button(example, key=f"example_{example}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": example})
                st.rerun()

        st.divider()

        # Clear conversation button
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.routing_history = []
            st.session_state.conversation_memory = []
            st.rerun()

        # System info
        st.divider()
        st.markdown("**⚙️ System Info:**")
        st.markdown(f"**Model:** {config.MODEL_NAME}")
        st.markdown(f"**Embeddings:** {config.EMBEDDING_MODEL.split('/')[-1]}")
        st.markdown(f"**Total Queries:** {len(st.session_state.routing_history)}")
        st.markdown(f"**Memory Size:** {len(st.session_state.conversation_memory)} messages")


if __name__ == "__main__":
    main()

