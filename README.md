# 📊 Transaction PDF Q&A Assistant

This project is a Streamlit-based LLM application that allows users to query bank transaction statements using natural language.

The application:
- Reads transaction PDFs from a local project folder (PDF's are generated using sample_statements_pdf_generater.py code)
- Extracts tabular transaction data
- Loads it into Pandas
- Uses an LLM to interpret user queries
- Executes analytical queries safely on structured data

---

## 🚀 Features

- No file uploads (secure, deterministic)
- PDF table extraction
- Natural language transaction queries
- Date-based filtering (e.g., Feb 2025)
- Debit / Credit aggregations
- Streamlit UI
- No vector database required

---

## 🔁 End-to-End Flow

```text
┌──────────────┐
│  User (UI)   │
│  Streamlit   │
└──────┬───────┘
       │ Natural Language Query
       ▼
┌──────────────────────┐
│ Prompt Engineering   │
│ • Schema             │
│ • Examples           │
│ • User Query         │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ LangChain Pandas     │
│ DataFrame Agent      │
│ (GPT-4o-mini)        │
└──────┬───────────────┘
       │ Python Code
       ▼
┌──────────────────────┐
│ Secure Code Execution│
│ (Pandas Operations)  │
└──────┬───────────────┘
       │ Results
       ▼
┌──────────────────────┐
│ Streamlit UI Output  │
└──────────────────────┘
