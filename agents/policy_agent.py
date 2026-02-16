"""Policy Agent - Answers questions using RAG from HR policy documents."""
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.state import AgentState
from typing import Optional, List


POLICY_AGENT_PROMPT = """You are an HR Policy Assistant. You answer questions using the retrieved HR policy context.

RULES:
1. Use ONLY information from the retrieved context below
2. If the context contains RELEVANT information that can help answer the question, provide a clear and helpful answer
3. When the user asks "can I..." questions, check the context for eligibility requirements and explain them
4. Quote specific numbers, durations, and details from the context (e.g., "6 months", "12 days", "14 characters")
5. If the user provides personal details (e.g., "I joined 3 months ago"), apply the policy rules to their situation
6. Only say "I don't have that information" if the context truly has NO relevant policy information
7. Consider the conversation history for follow-up questions
8. Be helpful - if the policy states requirements, explain whether the user meets them based on what they've shared

EXAMPLES:
- User: "I joined 3 months ago. Can I work remotely?"
  Context has: "Employees must complete 6 months probation period before requesting remote work"
  Good Answer: "According to the Remote Work Policy, employees must complete 6 months probation period before requesting remote work. Since you joined 3 months ago, you would need to wait 3 more months before becoming eligible for remote work."

- User: "How many sick leaves do I get?"
  Context has: "Employees are entitled to 12 sick leave days per year"
  Good Answer: "According to the Leave Policy, you are entitled to 12 sick leave days per year."

Retrieved Context:
{context}

Conversation History:
{history}

Current Question: {question}

Provide a helpful answer based on the context above:"""


class PolicyAgent:
    """Policy agent that uses RAG to answer HR policy questions."""

    def __init__(self, llm: ChatGroq, vector_store):
        """
        Initialize with shared LLM instance and vector store.

        Args:
            llm: Shared Groq LLM instance
            vector_store: FAISS vector store for RAG
        """
        self.llm = llm
        self.vector_store = vector_store

    def _build_search_query(self, user_input: str, messages: List) -> str:
        """
        Build an enhanced search query using conversation context.

        Args:
            user_input: Current user input
            messages: Conversation history

        Returns:
            Enhanced search query
        """
        # For follow-up questions, include recent context
        if messages and len(messages) >= 2:
            # Get last few exchanges for context
            recent_context = []
            for msg in messages[-4:]:  # Last 2 exchanges
                if hasattr(msg, 'content'):
                    recent_context.append(msg.content[:200])  # Truncate for efficiency

            # Combine current input with recent context
            context_str = " ".join(recent_context)
            enhanced_query = f"{user_input} {context_str}"
            return enhanced_query

        return user_input

    def _format_history(self, messages: List) -> str:
        """Format conversation history for the prompt."""
        if not messages:
            return "No previous conversation."

        history_lines = []
        for msg in messages[-6:]:  # Last 3 exchanges max
            if isinstance(msg, HumanMessage):
                history_lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                history_lines.append(f"Assistant: {msg.content[:300]}...")

        return "\n".join(history_lines) if history_lines else "No previous conversation."

    def run(self, state: AgentState) -> AgentState:
        """
        Answer policy questions using RAG with conversation memory.

        Args:
            state: Current agent state

        Returns:
            Updated state with policy response
        """
        user_input = state["user_input"]
        messages = state.get("messages", [])
        debug_log = state.get("debug_log", []) or []

        debug_log.append(f"[POLICY AGENT] Processing query: {user_input}")

        # Build enhanced search query for better retrieval
        search_query = self._build_search_query(user_input, messages)
        debug_log.append(f"[POLICY AGENT] Search query: {search_query}")

        # Retrieve relevant context from vector store with k=5 for better coverage
        if self.vector_store:
            docs = self.vector_store.similarity_search(search_query, k=5)

            # Build context from retrieved docs
            context_parts = []
            sources = []

            debug_log.append(f"[POLICY AGENT] Retrieved {len(docs)} chunks:")

            for i, doc in enumerate(docs):
                source = doc.metadata.get("source", "unknown")
                chunk_idx = doc.metadata.get("chunk_index", "?")
                sources.append(source)
                context_parts.append(doc.page_content)

                # Log snippet of each retrieved chunk
                snippet = doc.page_content[:200].replace('\n', ' ')
                debug_log.append(f"[POLICY AGENT]   {i+1}. {source} (chunk {chunk_idx}): \"{snippet}...\"")

            context = "\n\n---\n\n".join(context_parts)
        else:
            context = "No policy documents available."
            sources = []
            debug_log.append("[POLICY AGENT] WARNING: No vector store available")

        state["retrieved_context"] = context
        state["retrieved_sources"] = sources

        # Format conversation history
        history = self._format_history(messages)

        # Generate response using retrieved context and history
        prompt = POLICY_AGENT_PROMPT.format(
            context=context,
            history=history,
            question=user_input
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        policy_response = response.content.strip()

        debug_log.append(f"[POLICY AGENT] Generated response length: {len(policy_response)}")

        state["policy_response"] = policy_response
        state["debug_log"] = debug_log

        return state

