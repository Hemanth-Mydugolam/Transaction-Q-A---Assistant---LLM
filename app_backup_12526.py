import streamlit as st
import pandas as pd
import pdfplumber
import os
from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent
import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate

load_dotenv()  # loads .env into environment

if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("OPENAI_API_KEY not found. Please set it in .env")

schema = """
date: datetime64[ns]
description: object
amount: float64
type: object   # 'debit' or 'credit'
balance: float64
"""

examples = """
# Example 1
User query: "Total amount debited in Feb 2025"
Python code:
feb_debit = df[(df['date'].dt.month == 2) & (df['debit_credit'] == 'debit')]['amount'].sum()
print(feb_debit)

# Example 2
User query: "Give me all transactions on 2nd Feb 2025"
Python code:
transactions = df[df['date'] == '2025-02-02']
print(transactions)

# Example 3
User query: "Give me a monthly summary of debit and credit"
Python code:
df['month'] = df['date'].dt.month
summary_table = df.groupby(['month', 'debit_credit']).agg(
    total_amount=('amount', 'sum'),
    transaction_count=('amount', 'count')
).reset_index()
print(summary_table)
"""
prompt_template = """
You are a Python agent that can execute pandas DataFrame code.
The DataFrame is named `df`.

Columns and types:
{schema}

Here are some examples of user queries and the Python code to answer them:
{examples}

Now answer the following query. Only write Python code that executes and prints the result. Do not include explanations.

User query: {query}

Python code:
"""

prompt = PromptTemplate(
    input_variables=["schema", "examples", "query"],
    template=prompt_template
)

# ---------------------------------------
# CONFIG
# ---------------------------------------
MODEL = "gpt-4o-mini"
DATA_DIR = "data"

st.set_page_config(page_title="Transaction Q&A", layout="wide")
st.title("📊 Transaction Q&A Assistant")

# ---------------------------------------
# PDF DISCOVERY
# ---------------------------------------
@st.cache_data
def list_pdfs():
    return [f for f in os.listdir(DATA_DIR) if f.endswith(".pdf")]

@st.cache_data
# ❌ REMOVE this line for now
# @st.cache_data
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

    if headers is None or not rows:
        raise ValueError(
            "No transaction table found in the PDF. "
            "Ensure the PDF follows the expected format."
        )

    return pd.DataFrame(rows, columns=headers)



# ---------------------------------------
# DATA CLEANING
# ---------------------------------------
def clean_transactions(df):
    df.columns = [c.strip().lower() for c in df.columns]

    column_map = {
        "date": "date",
        "transaction date": "date",
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


# ---------------------------------------
# UI
# ---------------------------------------
def clean_llm_code(text: str) -> str:
    return (
        text.replace("```python", "")
            .replace("```", "")
            .strip()
    )
pdf_files = list_pdfs()
if not pdf_files:
    st.error("No PDF files found in the data/ directory.")
    st.stop()

selected_pdf = st.selectbox("Select a transaction statement", pdf_files)

if selected_pdf:
    pdf_path = os.path.join(DATA_DIR, selected_pdf)

    with st.spinner("Loading transactions..."):
        raw_df = extract_transactions_from_pdf(pdf_path)
        df = clean_transactions(raw_df)

    st.success(f"Loaded transactions from {selected_pdf}")
    st.dataframe(df, use_container_width=True)

    # ---------------------------------------
    # LLM AGENT
    # ---------------------------------------
    llm = ChatOpenAI(model=MODEL, temperature=0)

    agent = create_pandas_dataframe_agent(
        llm,
        df,
        verbose=True,
        allow_dangerous_code=True,
        handle_parsing_errors=True
    )

    st.subheader("💬 Ask questions")

    user_query = st.text_input(
        "Example: Total amount debited in Feb 2025"
    )

    if user_query:
        with st.spinner("Analyzing transactions..."):
            #response = agent.run(user_query)
            #response = agent.invoke(user_query)
            response = agent.invoke(prompt.format(schema=schema, examples=examples, query=user_query))
            clean_code = clean_llm_code(response["output"])
            exec(clean_code)

        st.markdown("### ✅ Answer")
        st.write(response)
