# CLAUDE.md — Workspace Rules & Tech Stack Architecture

## Build & Test Commands
- **Build Suite:** docker-compose up --build
- **Run Backend Tests:** python -m pytest tests/test_pipeline.py -v
- **Run Frontend Tests:** npm run test

## Development Philosophy & Karpathy Rules
- **Incremental Refinement:** Make the absolute smallest code modification required to achieve a goal. Never rewrite surrounding functional code unnecessarily.
- **Strict Verification:** You must run the Build Suite and relevant Test suites immediately after every file modification. Never assume code works without executing it.
- **Explicit Logic:** Prioritize clean, explicit variable names over short, cryptic code.
- **Index vs Value Tracking:** When modifying queues, arrays, or sequences, maintain absolute separation between structural indices/pointers and actual data/card values. Handle bounds checking defensively.

## Git Branching Strategy
- **Strict Rule:** Always use the `jasmine/` branch naming convention for working features (e.g., `jasmine/karpathy-refactor`). Never commit directly to main.

---

## Core System Architecture (Medi_Travel Platform)

### 1. Multi-Agent AI Architecture & Orchestration
The system leverages a decoupled, multi-agent design pattern:
- **Clinical Parsing Agent:** Extracts, cleans, and structures medical histories/diagnostics into standard schema formats.
- **Logistics Optimization Agent:** Handles cross-border itinerary generation, scheduling constraints, and geo-location facility lookups.
- **Financial & Healthcare Matching Agent:** Handles algorithmic budget-to-facility routing against cost boundaries.
- **State Boundaries:** Strict context-passing boundaries must be maintained between concurrent agents to prevent context drift.

### 2. Advanced Data Engineering & Semantic Search
- **Vector Database:** ChromaDB powers low-latency semantic search and RAG. Maintain custom chunking and overlapping strategies optimized for dense clinical text.
- **Data Validation:** Enforce strict typing and JSON-Schema validation for incoming patient profiles to prevent downstream LLM hallucinations.

### 3. Core Software Engineering & System Design
- **Language:** Python (Advanced asynchronous execution, structural typing).
- **Environment:** Containerized services using Docker. Maintain low-coupling and high cohesion across modules.