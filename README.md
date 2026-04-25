# 🩺 ASEAN Medical AI Matching Backend

A sophisticated multi-layer AI agentic system designed to match international patients (Medical Tourists) with specialized healthcare providers, logistical support, and financial aid in Malaysia.

## 🚀 Recent Progress (Update for Teammates)
We have successfully pivoted the core architecture from a simple "Hospital Search" to a highly granular **Doctor-Centric RAG System**.

## 🧠 AI Architecture & Data Layers

Our system is built as a **Multi-Layer Agentic Orchestrator**. Each layer uses specific AI tools to ensure accuracy and transparency.

### Layer 1: Medical Specialist Matching
*   **AI Tools**: **Ollama (Llama 3.2:3b)** + **ChromaDB (Vector RAG)**.
*   **How it Works**: 
    1.  The **Medical Agent** uses LLM reasoning to infer the specific sub-specialty needed (e.g., "Electrophysiology" from a general heart report).
    2.  It performs a **Semantic Search** against our centralized Doctor RAG database.
*   **Data Retrieval**: Real-time retrieval from the `malaysia_doctors` vector collection, populated by our custom scraping pipeline.

### Layer 2: Logistics & Flight Intelligence
*   **AI Tools**: **SerpApi (Google Flights API)** + **Logistic Reasoning Engine**.
*   **How it Works**: 
    1.  Analyzes the patient's medical chart to determine mobility (Ambulatory vs. Stretcher).
    2.  If the patient is ambulatory, it fetches **LIVE flight data** (prices, times, airlines).
    3.  If the patient requires a stretcher, it automatically generates a professional **Medical Charter Email Draft**.
*   **Data Retrieval**: Real-time API calls to Google Flights.

### Layer 3: Financial Aid & Charity Matching
*   **AI Tools**: **Ollama (Eligibility Reasoning)**.
*   **How it Works**: 
    1.  Matches the patient's country of origin and medical condition against local Malaysian NGO rules.
    2.  Provides a reasoned explanation of why a specific charity might cover the patient's costs.
*   **Data Retrieval**: Expert-curated knowledge base stored in `data/charities.json`.

---

## 🛠️ Project Structure
- `app.py`: Main FastAPI entry point.
- `api_test.py`: Simple script to test the end-to-end matching flow without local dependencies.
- `agents/`:
  - `medical_agent.py`: Queries the Doctor RAG database.
  - `logistics_agent.py`: Handles transport analysis and flight search.
  - `charity_agent.py`: Matches patients with local NGOs/Charities.
  - `orchestrator.py`: Merges agent outputs into packages.
- `pipeline/`:
  - `ingest_doctors.py`: The scraping and RAG injection engine.
  - `generate_report.py`: Creates the visual HTML dashboard for demo/judging.
- `reports/`: Stores the visual `db_dashboard.html`.
- `utils/`: Core processing tools (OCR, Translation, Medical Parsing).

---

## ⚙️ How to Run & Test

### 1. Start the Backend (Docker)
Ensure Docker Desktop is running and Ollama is open on your host.
```bash
docker-compose up --build
```

### 2. Ingest Data (One-time)
Populate the centralized database with real doctor profiles:
```bash
docker exec -it ai_medical_matching-api-1 python pipeline/ingest_doctors.py
```

### 3. Generate Visual Dashboard
To show the judges the data granularity:
```bash
docker exec -it ai_medical_matching-api-1 python pipeline/generate_report.py
```
*Open `reports/db_dashboard.html` in your browser to view.*

### 4. Test the Matching Logic
Run the end-to-end demo script:
```bash
python tests/test_vietnamese_flow.py
```

---
**Build for ASEAN AI Hackathon 2026**
