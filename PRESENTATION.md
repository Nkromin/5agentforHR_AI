# Multi-Agent HR Automation System
## Presentation Slides

---

## SLIDE 1: Title Slide

### Multi-Agent HR Automation System
**Agentic AI for Enterprise HR Operations**

- **Tech Stack:** LangGraph, Groq Cloud, FAISS, Streamlit
- **LLM Model:** llama-3.1-8b-instant (Single Shared Instance)
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2
- **Framework:** Python 3.10+
- **Architecture:** Multi-Agent Orchestrated Workflow

---

## SLIDE 2: Industry Use Case

### Enterprise HR Automation - Problem Statement

- **Challenge:** HR departments handle repetitive queries (leave policies, IT security, expense rules) consuming significant human bandwidth
- **Volume:** Enterprises receive thousands of policy questions and action requests daily
- **Inconsistency:** Manual responses lead to inconsistent policy interpretation across departments
- **Solution:** Intelligent multi-agent system that routes queries, retrieves accurate policy information, and executes HR actions autonomously
- **Value of Multi-Agent:** Different agents specialize in distinct tasks (classification, retrieval, execution, validation) enabling modular and maintainable architecture
- **Scope:** Handles 5 policy domains - Leave, Remote Work, IT Security, Expense Reimbursement, Code of Conduct

---

## SLIDE 3: Agentic Process Overview

### End-to-End Flow from User Input to Final Response

1. **User Input** → Natural language query enters the system via Streamlit chat interface
2. **Orchestrator Agent** → Classifies intent into: `POLICY_QUERY`, `ACTION_REQUEST`, or `UNKNOWN`
3. **Conditional Routing** → LangGraph routes to appropriate specialized agent based on intent
4. **Specialized Processing:**
   - `POLICY_QUERY` → Policy Agent retrieves context from FAISS and generates answer
   - `ACTION_REQUEST` → Action Agent parses tool call and executes (e.g., create ticket, check balance)
   - `UNKNOWN` → Fallback node returns safe response
5. **Finalize Node** → Consolidates response, updates conversation memory
6. **Response Delivery** → Final answer displayed in Streamlit UI with routing debug info

---

## SLIDE 4: Multi-Agent Breakdown

### Four Specialized Agents with Distinct Responsibilities

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Orchestrator** | Intent Classification | User query | `{"intent": "POLICY_QUERY" \| "ACTION_REQUEST" \| "UNKNOWN"}` |
| **Policy Agent** | RAG-Based Q&A | Query + Retrieved Context | Policy answer grounded in documents |
| **Action Agent** | Tool Execution | Action request | Tool result (ticket ID, leave balance) |
| **Fallback/Compliance** | Validation & Safety | Proposed answer | Validated or safe fallback response |

**Key Design Decision:** Each agent has a specific system prompt defining its behavior boundaries. No agent performs tasks outside its designated role.

---

## SLIDE 5: Inter-Agent Communication

### State-Based Communication via LangGraph

**AgentState TypedDict Structure:**
```python
class AgentState(TypedDict):
    messages: List[BaseMessage]       # Conversation memory
    user_input: str                   # Current query
    intent: str                       # POLICY_QUERY | ACTION_REQUEST | UNKNOWN
    retrieved_context: str            # RAG context from FAISS
    policy_response: str              # Policy Agent output
    tool_calls: List[Dict]            # Action Agent tool invocations
    action_response: str              # Action Agent output
    final_answer: str                 # Finalized response
    next_agent: str                   # Routing decision
    debug_log: List[str]              # Debug traces
```

**Routing Decision Flow:**
- Orchestrator sets `intent` and `next_agent` in state
- LangGraph's conditional edges read `next_agent` to determine next node
- State is passed immutably between nodes; each node returns updated state

---

## SLIDE 6: Tool Assignment

### Strict Tool Isolation by Agent

| Agent | Tools Available | Reason |
|-------|-----------------|--------|
| **Orchestrator** | None | Classification only; no actions |
| **Policy Agent** | FAISS Retriever (implicit) | Retrieves documents; no execution capabilities |
| **Action Agent** | `create_hr_ticket(issue)`, `check_leave_balance(employee_id)` | Only agent with execution permissions |
| **Fallback** | None | Returns static safe message |

**Tool Definitions:**
```python
create_hr_ticket(issue: str) → {"ticket_id": "TICKET-1234", "message": "..."}
check_leave_balance(employee_id: str) → {"leave_balance": 8, "message": "..."}
```

**Isolation Rationale:**
- Prevents Policy Agent from accidentally executing actions
- Ensures UNKNOWN intents never trigger tool execution
- Maintains separation of concerns for auditability

---

## SLIDE 7: RAG Implementation

### Retrieval-Augmented Generation Pipeline

**Document Loading:**
- Source: `/docs/` folder containing 5 policy files (`.txt` format)
- Loader validates all required policies exist before indexing
- Text cleaning: Whitespace normalization, punctuation fixing, encoding cleanup

**Chunking Strategy:**
```python
RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\nSection", "\n\n", "\n", ". ", " "]
)
```
- Total chunks: 14 across 5 documents
- Each chunk prefixed with policy title for better retrieval

**Embeddings:**
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Normalized embeddings for cosine similarity

**Vector Store:**
- FAISS (Facebook AI Similarity Search)
- Local persistence in `/faiss_index/` directory
- Force rebuild on startup to ensure freshness

**Retrieval:**
- Top-k=5 similarity search per query
- Context concatenated and injected into Policy Agent prompt

---

## SLIDE 8: LangGraph Workflow Design

### Graph Architecture with Deterministic Control

**Nodes Defined:**
1. `orchestrator` → Entry point; classifies intent
2. `policy` → RAG-based answering
3. `action` → Tool execution
4. `fallback` → Safe response for UNKNOWN
5. `finalize` → Memory update and response consolidation

**Conditional Routing:**
```python
workflow.add_conditional_edges(
    "orchestrator",
    route_after_orchestrator,  # Returns: "policy" | "action" | "fallback"
    {"policy": "policy", "action": "action", "fallback": "fallback"}
)
```

**Edge Configuration:**
- All specialized nodes (`policy`, `action`, `fallback`) → `finalize` → `END`
- No cycles; strictly DAG structure

**Single LLM Instance:**
```python
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0,
    max_tokens=512
)
# Same instance passed to Orchestrator, Policy Agent, Action Agent
```

---

## SLIDE 9: Streamlit UI Demo

### Interactive Chat Interface with Debug Visibility

**Main Chat Area (Left Column):**
- Standard chat message display (user/assistant alternating)
- Chat input box for natural language queries
- Conversation persists across turns using `st.session_state`

**System Monitor Sidebar (Right Column):**
- **Intent Display:** Shows classified intent (`POLICY_QUERY`, `ACTION_REQUEST`, `UNKNOWN`)
- **Agent Flow Visualization:** `Orchestrator → [Policy/Action/Fallback] → Finalize`
- **Retrieved Sources:** List of document chunks used for RAG
- **Tool Calls:** JSON display of executed tools and results
- **Debug Log Expander:** Step-by-step execution trace

**User Actions:**
- Example query buttons for quick testing
- Clear conversation button to reset session state and memory

---

## SLIDE 10: System Strengths

### Key Architectural Advantages

- **Modularity:** Each agent is a separate Python class; easy to modify, test, or replace independently
- **Controlled Execution:** LangGraph's deterministic routing prevents uncontrolled agent spawning
- **Tool Isolation:** Only Action Agent can execute tools; prevents accidental or malicious execution
- **Reduced Hallucination:** Policy Agent strictly answers from retrieved context; includes fallback for insufficient information
- **Single LLM Efficiency:** One Groq instance shared across all agents reduces latency and API costs
- **Debug Transparency:** Full execution trace visible in UI for troubleshooting and viva demonstration
- **Memory Handling:** Conversation history preserved in state; follow-up questions maintain context

---

## SLIDE 11: Known Limitations

### Current System Constraints and Edge Cases

- **Intent Misclassification:** LLM-based classification can occasionally misroute ambiguous queries (e.g., "I'm sick" could be POLICY or ACTION)
- **Memory Limitations:** Conversation memory limited to last 10 messages to manage token budget; very long conversations may lose early context
- **Static Tool Responses:** Tools return hardcoded dummy data; no actual backend integration
- **Single Retriever:** Same chunking strategy for all documents; some policies may need specialized handling
- **No Human-in-the-Loop:** System cannot escalate to human HR staff for complex cases
- **Language Limitation:** Currently English-only; no multilingual support
- **Compliance Agent Simplified:** Current implementation uses Finalize node instead of full LLM-based compliance validation for efficiency

---

## SLIDE 12: Future Enhancements

### Roadmap for Production Readiness

1. **Improved Intent Classification:**
   - Fine-tune classifier on HR-specific dataset
   - Add confidence scores and fallback for low-confidence predictions

2. **Enhanced Memory:**
   - Implement sliding window with summarization for long conversations
   - Add persistent memory across sessions using database

3. **Human-in-the-Loop:**
   - Escalation mechanism for complex or sensitive requests
   - Approval workflow for action execution

4. **Real Backend Integration:**
   - Connect to actual HRIS systems (SAP SuccessFactors, Workday)
   - Live leave balance queries from employee database
   - Actual ticket creation in ServiceNow/Jira

5. **Advanced RAG:**
   - Hybrid search (keyword + semantic)
   - Cross-encoder reranking for improved retrieval accuracy

6. **Production Deployment:**
   - Containerization with Docker
   - Rate limiting and authentication
   - Logging and monitoring stack

---

## APPENDIX: Technical Specifications

### Configuration Summary

| Parameter | Value |
|-----------|-------|
| LLM Model | `llama-3.1-8b-instant` |
| Temperature | `0.0` (deterministic) |
| Max Tokens | `512` |
| Embedding Model | `all-MiniLM-L6-v2` |
| Chunk Size | `800` characters |
| Chunk Overlap | `150` characters |
| Retrieval Top-K | `5` |
| Memory Limit | `10` messages |

### File Structure
```
project_root/
├── app.py                 # Streamlit frontend
├── config.py              # Configuration settings
├── tools.py               # Tool definitions
├── requirements.txt       # Dependencies
├── agents/
│   ├── orchestrator.py    # Intent classification
│   ├── policy_agent.py    # RAG answering
│   ├── action_agent.py    # Tool execution
│   ├── compliance_agent.py# Validation (optional)
│   ├── graph.py           # LangGraph workflow
│   └── state.py           # State definition
├── rag/
│   ├── loader.py          # Document loading
│   └── vector_store.py    # FAISS management
├── docs/
│   ├── leave_policy.txt
│   ├── remote_work_policy.txt
│   ├── expense_policy.txt
│   ├── it_security_policy.txt
│   └── code_of_conduct.txt
└── faiss_index/           # Persisted vector store
```

---

## APPENDIX: Sample Interactions

### Test Cases for Demo

| Query | Expected Routing | Expected Output |
|-------|------------------|-----------------|
| "What is the password policy?" | POLICY_QUERY → Policy Agent | Lists 14-char requirement, 90-day change, etc. |
| "How many sick leaves do I get?" | POLICY_QUERY → Policy Agent | "12 sick leave days per year" |
| "I joined 3 months ago. Can I work remotely?" | POLICY_QUERY → Policy Agent | "Need 6 months probation; wait 3 more months" |
| "Check my leave balance for EMP001" | ACTION_REQUEST → Action Agent | "Employee EMP001 has 8 leave days remaining" |
| "Create a ticket for laptop issue" | ACTION_REQUEST → Action Agent | "Ticket ID: TICKET-1234 created" |
| "Book flight tickets" | UNKNOWN → Fallback | Safe message: "I can only assist with HR policies..." |

---

## END OF PRESENTATION

**Prepared for:** Agentic AI Assignment Viva
**System:** Multi-Agent HR Automation
**Author:** [Your Name]
**Date:** February 2026

