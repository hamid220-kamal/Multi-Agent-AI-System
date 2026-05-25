# System Architecture

This document breaks down the core structural design of the Advanced Multi-Agent Autonomous Pipeline.

## 1. The Global State (`core/schema.py`)
At the heart of the system is the `SystemState` object. This is a single, mutable Pydantic V2 model that acts as the absolute source of truth.
Unlike architectures that pass arbitrary `*args` or `**kwargs` between functions, every single compute node in this system receives the `SystemState` as its sole input, and returns an updated `SystemState` as its sole output.

### Key State Components:
- **`status`**: Drives the execution graph (`PENDING`, `PROCESSING`, `PAUSED`, `REVISE`, `COMPLETED`, `FAILED`).
- **`agent_logs`**: A segregated dictionary tracking the thought processes and actions of individual agents.
- **`human_feedback`**: A nullable string field injected during `PAUSED` states to steer subsequent agent decisions.
- **Hash Tracking**: The state generates a cryptographic hash of itself on every loop. If the state machine detects that the hash has not mutated across multiple iterations, it forces a failure to prevent catastrophic infinite loops.

## 2. The Engine (`core/engine.py`)
The `AsyncGraphOrchestrator` is a lightweight, zero-dependency alternative to LangGraph. 
It operates by mapping strings (Node Names) to Callables (`NodeFunction`).

1. It evaluates the current node function.
2. It yields a Server-Sent Event (SSE) indicating node completion and active status.
3. It passes the mutated state into the `RouterFunction` for the current node.
4. The router deterministically outputs the string name of the next node to execute.

## 3. The Agent Nodes (`nodes/agents.py`)
Agents are simply native Python async functions that wrap LLM calls. 

- **Planner Agent**: Decomposes the user's objective into an array of sequential steps.
- **Researcher Agent**: Takes the current step, formulates a web search, executes the tool, and dumps the raw HTML/Text findings directly into the Vector Database (ChromaDB) to prevent Context Window overflow.
- **Supervisor Agent**: A simple logic gate that checks if `state.human_feedback` is present. If not, it flips the state to `PAUSED` and yields execution.
- **Critic Agent**: Queries the Vector Database using semantic search to retrieve the top 5 most relevant chunks of context. It then evaluates if the context fulfills the user's objective (with human feedback taken into account).

## 4. The RAG Memory Layer (`core/memory.py`)
To prevent the global `SystemState` from ballooning to hundreds of thousands of tokens, raw data is pushed to a local ChromaDB instance.
- **Offline Reliability**: The database uses a custom `OfflineDummyEmbedding` function that generates 384-dimensional vectors using string hashes. This completely bypasses the need for ChromaDB to download external ONNX models, making the system 100% reliable on restricted networks.
