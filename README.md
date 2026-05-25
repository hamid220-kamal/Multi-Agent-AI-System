# Advanced Multi-Agent Autonomous Pipeline

A high-performance, native Python state machine orchestrator for distributed AI agents. 

Built entirely from scratch without high-level frameworks (like LangGraph, CrewAI, or AutoGen) to maintain strict, deterministic control over performance, latencies, and state mutations. This architecture serves as a foundational blueprint for enterprise-grade autonomous AI systems.

## 🚀 Key Features

* **Zero-Framework Orchestration:** Custom native `asyncio` graph engine for executing complex multi-agent workflows.
* **Deterministic State Machine:** Robust state tracking via Pydantic V2 with built-in cryptographic hashing for Infinite Loop detection and prevention.
* **Human-in-the-Loop (HITL):** Secure execution pausing (`PAUSED` state) allowing human supervisors to validate or inject feedback and instantly resume via state-snapshot rehydration.
* **Local Vector RAG Memory:** Fully offline ChromaDB integration with custom deterministic hashing. Bypasses external ONNX model downloads, ensuring 100% functionality behind strict enterprise firewalls.
* **Real-time SSE Streaming:** FastAPI endpoints yielding live `text/event-stream` JSON telemetry for seamless front-end integration.
* **Intelligent Offline Fallbacks:** Graceful exception handling for API connection timeouts, automatically routing to deterministic mock schemas to ensure demo resilience.

## 🛠️ Installation & Setup

1. **Clone the repository and enter the directory:**
   ```bash
   cd "Multi-Agent AI System"
   ```

2. **Install the dependencies:**
   It is highly recommended to use a virtual environment, or install dependencies locally for the current user.
   ```bash
   pip install -r requirements.txt --user
   ```

3. **Run the Orchestration Server:**
   The backend is powered by FastAPI and Uvicorn. Start it with live-reloading enabled.
   ```bash
   python -m uvicorn main:app --reload
   ```

## 🧪 Testing the Pipelines

With the server running on `http://127.0.0.1:8000`, open a new terminal window to test the clients.

### Standard Autonomous Execution
Run the standard pipeline that delegates tasks from the Planner to the Researcher and Critic.
```bash
python test_client.py
```

### Human-in-the-Loop Execution
Run the advanced resume script which initiates the pipeline, hits the Supervisor node, pauses execution for human validation, and resumes cleanly.
```bash
python test_resume.py
```

## 📁 Project Structure

```
├── core/
│   ├── engine.py       # The zero-framework async graph orchestrator
│   ├── llm.py          # LLM API wrapper with structured JSON constraint enforcement
│   ├── memory.py       # ChromaDB local persistent RAG memory
│   └── schema.py       # Pydantic V2 State definitions (the source of truth)
├── nodes/
│   └── agents.py       # Compute nodes (Planner, Researcher, Supervisor, Critic)
├── tools/
│   └── search.py       # DuckDuckGo search integration
├── main.py             # FastAPI entrypoint (Stream and Resume API routes)
├── requirements.txt    # Project dependencies
├── test_client.py      # Standard execution demo
└── test_resume.py      # Human-in-the-loop execution demo
```

## 🛡️ License

This project is licensed under the MIT License.
