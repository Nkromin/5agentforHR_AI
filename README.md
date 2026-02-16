# 🤖 HR Multi-Agent Automation System

Enterprise-grade HR automation system built with **LangGraph**, **Groq LLM**, and **FAISS** vector store.

## 🌟 Features

- **Multi-Agent Architecture** using LangGraph (NOT simple agent executor)
- **Single Groq LLM Instance** (llama3-8b-8192) shared across all agents
- **RAG-powered Policy Q&A** using FAISS + HuggingFace Embeddings
- **Tool Execution** for HR actions (tickets, leave balance)
- **Compliance Validation** to prevent hallucinations
- **Streamlit Frontend** with real-time agent monitoring

## 🏗️ Architecture

### Agents

1. **Orchestrator Agent** - Classifies intent and routes requests
2. **Policy Agent** - RAG-based policy Q&A
3. **Action Agent** - Executes HR tools
4. **Compliance Agent** - Validates responses

### Workflow

```
User Input
    ↓
Orchestrator (classify intent)
    ↓
Conditional Routing:
    → Policy Agent (RAG)
    → Action Agent (Tools)
    → Fallback
    ↓
Compliance Agent (validation)
    ↓
Final Response
```

## 📁 Project Structure

```
5ApiChekr/
│
├── app.py                      # Streamlit frontend
├── config.py                   # Configuration
├── tools.py                    # HR tools (tickets, leave)
├── requirements.txt            # Dependencies
├── .env                        # API keys (create from .env.example)
│
├── agents/
│   ├── __init__.py
│   ├── state.py               # LangGraph state definition
│   ├── orchestrator.py        # Intent classification
│   ├── policy_agent.py        # RAG-based policy Q&A
│   ├── action_agent.py        # Tool execution
│   ├── compliance_agent.py    # Response validation
│   └── graph.py               # LangGraph workflow
│
└── rag/
    ├── __init__.py
    ├── loader.py              # HR policy documents
    └── vector_store.py        # FAISS initialization
```

## 🚀 Setup

### Prerequisites

- Python 3.10+
- Groq API Key (get from [console.groq.com](https://console.groq.com))

### Installation

1. **Clone/navigate to project:**
   ```bash
   cd /home/nkro/PycharmProjects/5ApiChekr
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your GROQ_API_KEY
   ```

5. **Run the application:**
   ```bash
   streamlit run app.py
   ```

## 💡 Usage Examples

### Policy Questions
- "What is the leave policy?"
- "How many vacation days do I get?"
- "What is the remote work policy?"
- "Tell me about health insurance benefits"

### Action Requests
- "Check my leave balance for EMP001"
- "Create a ticket for laptop issue"
- "Check leave balance"

## 🔧 Tools

### Available Tools

1. **create_hr_ticket(issue: str)**
   - Creates HR ticket
   - Returns: `TICKET-1234`

2. **check_leave_balance(employee_id: str)**
   - Checks leave balance
   - Returns: "You have 8 leave days remaining."

## 📊 System Monitor

The Streamlit UI includes a real-time system monitor showing:
- Intent classification
- Agent routing flow
- Tool calls
- Compliance status

## 🔒 Compliance & Safety

The **Compliance Agent** ensures:
- No hallucinations in policy answers
- Responses grounded in retrieved context
- Safe fallbacks for unknown queries
- Tool outputs validated

## 🛠️ Configuration

Edit `config.py` to customize:
- Model name (default: `llama3-8b-8192`)
- Temperature (default: 0.0 for consistency)
- Max tokens (default: 512)
- Embedding model

## 📦 Dependencies

- `langchain` - LLM framework
- `langchain-groq` - Groq integration
- `langgraph` - Multi-agent workflows
- `streamlit` - Web UI
- `faiss-cpu` - Vector store
- `sentence-transformers` - Embeddings

## 🎯 Key Features

✅ **Single LLM Instance** - One Groq client shared across all agents  
✅ **LangGraph** - Proper graph-based workflow (not simple executor)  
✅ **RAG** - FAISS vector store with HuggingFace embeddings  
✅ **Tool Execution** - Structured tool calls with validation  
✅ **Compliance** - Anti-hallucination checks  
✅ **Streamlit UI** - Interactive chat with agent monitoring  

## 🐛 Troubleshooting

### GROQ_API_KEY not found
Create a `.env` file with:
```
GROQ_API_KEY=your_actual_api_key_here
```

### Import errors
Reinstall dependencies:
```bash
pip install -r requirements.txt --force-reinstall
```

### Vector store issues
Delete `faiss_index` folder and restart the app to rebuild.

## 📝 License

MIT License

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

Built with ❤️ using LangGraph + Groq + FAISS

