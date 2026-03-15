# 📈 FinSight

> AI-powered financial analysis assistant — stock analysis, document Q&A, and conversational finance.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit)
![Claude](https://img.shields.io/badge/Claude-Anthropic-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

| Feature | Description |
|---|---|
| **📊 Stock Analysis** | Technical indicators (RSI, MACD, Bollinger Bands, SMAs) + fundamental metrics + AI-generated analysis |
| **📄 Document Q&A** | Upload 10-K / 10-Q / earnings transcripts → ask questions grounded in the text (RAG) |
| **💬 AI Chat** | Conversational financial assistant with full session memory |

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Claude (Anthropic) via `anthropic` SDK |
| Orchestration | LangChain |
| Vector Store | FAISS |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, no API key) |
| Market Data | yfinance |
| Technical Analysis | `ta` library |
| UI | Streamlit + Plotly |
| Config | Pydantic-settings |
| Logging | structlog |

---

## Project Structure

```
finsight/
├── app/
│   ├── Home.py                  # Entry point
│   └── pages/
│       ├── 1_Stock_Analysis.py
│       ├── 2_Document_QA.py
│       └── 3_Chat.py
├── core/
│   ├── data/
│   │   └── stock_client.py      # yfinance wrapper + TTL cache
│   ├── analysis/
│   │   └── technical.py         # Technical indicators & signals
│   ├── llm/
│   │   └── claude_client.py     # Claude API + streaming + retry
│   └── rag/
│       └── pipeline.py          # LangChain + FAISS RAG pipeline
├── config/
│   └── settings.py              # Pydantic-settings config
├── tests/
│   ├── test_technical.py
│   └── test_stock_client.py
├── scripts/
│   └── setup.sh                 # Dev environment bootstrap
├── data/
│   ├── documents/               # Uploaded PDFs (gitignored)
│   └── faiss_index/             # Persisted FAISS index (gitignored)
├── .streamlit/
│   └── config.toml              # Dark theme + server config
├── .env.example
├── pyproject.toml               # black / ruff / mypy / pytest config
├── requirements.txt
└── Makefile
```

---

## Quick Start

### 1. Clone & setup

```bash
git clone https://github.com/yourname/finsight.git
cd finsight
make setup          # creates .venv, installs deps, copies .env
```

### 2. Add API key

```bash
# Edit .env
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run

```bash
source .venv/bin/activate
make run
# → http://localhost:8501
```

---

## Development

```bash
make test           # pytest + coverage
make lint           # ruff check
make format         # black
make typecheck      # mypy
make clean          # remove caches
```

---

## Roadmap

- [ ] Phase 1 — MVP (current)
  - [x] Stock analysis with technical indicators
  - [x] Claude AI analysis (streaming)
  - [x] RAG pipeline for financial documents
  - [x] Conversational chat with session memory
- [ ] Phase 2
  - [ ] News sentiment analysis
  - [ ] Portfolio tracking & comparison
  - [ ] Earnings calendar integration
  - [ ] Export analysis as PDF report
- [ ] Phase 3
  - [ ] Agentic stock screener
  - [ ] Multi-document cross-referencing
  - [ ] User authentication & saved watchlists

---

## Disclaimer

> FinSight is for **informational and educational purposes only**.
> Nothing in this application constitutes investment advice.
> Always consult a qualified financial professional before making investment decisions.

---

*Built by Eymen — KSU CS · NIH Research Background*
