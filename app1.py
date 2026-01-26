import streamlit as st
import pandas as pd
import pdfplumber
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# -------------------------------------------------
# ENV SETUP
# -------------------------------------------------
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("OPENAI_API_KEY not found in .env")

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
MODEL = "gpt-4o-mini"
DATA_DIR = "data"

st.set_page_config(page_title="Transaction Q&A", layout="wide")
st.title("📊 Transaction Q&A Assistant")

# -------------------------------------------------
# SCHEMA + EXAMPLES (FEW-SHOT)
# -------------------------------------------------
schema = """
date: datetime64[ns]
description: object
amount: float64
type: object   # debit or credit
balance: float64
"""

examples = """
# Example 1
User query: "Total amount debited in Feb 2025"
Python code:
result = df[
    (df['date'].dt.month == 2) &
    (df['date'].dt.year == 2025) &
    (df['type'] == 'debit')
]['amount'].sum()
print(result)

# Example 2
User query: "Give me all transactions on 2nd Feb 2025"
Python code:
result = df[df['date'] == '2025-02-02']
print(result)

# Example 3
User query: "Give me a monthly summary of debit and credit"
Python code:
df['month'] = df['date'].dt.to_period('M')
result = df.groupby(['month', 'type']).agg(
    total_amount=('amount', 'sum'),
    transaction_count=('amount', 'count')
).reset_index()
print(result)
"""

prompt_template = """
You are a Python pandas expert.

You are given a pandas DataFrame named `df`.

DataFrame schema:
{schema}

Below are example user questions and the exact Python code used to answer them:
{examples}

Rules:
- Only output valid Python code
- Code must use pandas
- Always assign final output to a variable named `result`
- Always print(result)
- Do NOT explain anything

User question:
{query}

Python code:
"""

prompt = PromptTemplate(
    input_variables=["schema", "examples", "query"],
    template=prompt_template
)

# -------------------------------------------------
# PDF LOADING
# -------------------------------------------------
@st.cache_data
def list_pdfs():
    return [f for f in os.listdir(DATA_DIR) if f.endswith(".pdf")]

@st.cache_data
def extract_transactions_from_pdf(pdf_path):
    rows = []
    headers = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table or len(table) < 2:
                continue

            if headers is None:
                headers = table[0]

            for row in table[1:]:
                if any(cell is not None for cell in row):
                    rows.append(row)

    return pd.DataFrame(rows, columns=headers)

# -------------------------------------------------
# DATA CLEANING
# -------------------------------------------------
def clean_transactions(df):
    df.columns = [c.strip().lower() for c in df.columns]

    column_map = {
        "transaction date": "date",
        "date": "date",
        "description": "description",
        "details": "description",
        "amount": "amount",
        "debit/credit": "type",
        "type": "type",
        "balance": "balance"
    }

    df.rename(columns=column_map, inplace=True)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace(",", "")
        .str.replace("$", "")
        .astype(float)
    )

    df["type"] = df["type"].str.lower()

    return df

# -------------------------------------------------
# UI
# -------------------------------------------------
pdf_files = list_pdfs()

if not pdf_files:
    st.error("No PDF files found in data/")
    st.stop()

selected_pdf = st.selectbox("Select a transaction statement", pdf_files)

if selected_pdf:
    pdf_path = os.path.join(DATA_DIR, selected_pdf)

    with st.spinner("Loading transactions..."):
        raw_df = extract_transactions_from_pdf(pdf_path)
        df = clean_transactions(raw_df)

    st.success("Transactions loaded")
    st.dataframe(df, use_container_width=True)

    # -------------------------------------------------
    # LLM
    # -------------------------------------------------
    llm = ChatOpenAI(model=MODEL, temperature=0)

    st.subheader("💬 Ask questions")
    user_query = st.text_input(
        "Example: Give me a monthly summary of debit and credit"
    )

    if user_query:
        with st.spinner("Thinking..."):
            formatted_prompt = prompt.format(
                schema=schema,
                examples=examples,
                query=user_query
            )

            response = llm.invoke(formatted_prompt)
            code = response.content.strip().replace("```python", "").replace("```", "")

            st.code(code, language="python")

            # Safe execution context
            local_env = {"df": df.copy(), "pd": pd}

            try:
                exec(code, {}, local_env)
                result = local_env.get("result")

                st.subheader("✅ Result")
                if isinstance(result, pd.DataFrame):
                    st.dataframe(result, use_container_width=True)
                else:
                    st.write(result)

            except Exception as e:
                st.error(f"Execution error: {e}")
