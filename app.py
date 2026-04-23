import streamlit as st
import pandas as pd
import pdfplumber
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from tools import make_tools

# -------------------------------------------------
# ENV SETUP
# -------------------------------------------------
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("OPENAI_API_KEY not found in .env")

# Load user credentials from .env
# Format in .env: USER1_ID, USER1_PASSWORD, USER1_NAME (supports up to USER9)
USERS = {}
for i in range(1, 10):
    uid  = os.getenv(f"USER{i}_ID")
    pwd  = os.getenv(f"USER{i}_PASSWORD")
    name = os.getenv(f"USER{i}_NAME")
    if uid and pwd and name:
        USERS[uid] = (pwd, name, uid)   # (password, display_name, pdf_prefix)

if not USERS:
    raise EnvironmentError("No user credentials found in .env (expected USER1_ID, USER1_PASSWORD, USER1_NAME ...)")

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
MODEL    = "gpt-4o-mini"
DATA_DIR = "data"
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# -------------------------------------------------
# CHAT LOGGING
# -------------------------------------------------
def log_message(username: str, session_id: str, pdf: str, role: str, content: str):
    """Append one message event to the user's JSONL chat log."""
    record = {
        "session_id": session_id,
        "user_id":    username,
        "pdf":        pdf,
        "timestamp":  datetime.now().isoformat(timespec="seconds"),
        "role":       role,
        "content":    content,
    }
    log_path = os.path.join(LOGS_DIR, f"{username}_chat_history.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

SYSTEM_PROMPT = (
    "You are a financial assistant that answers questions about the user's bank transactions. "
    "Use the available tools to look up, filter, and summarize transaction data. "
    "Always use a tool before answering — never make up numbers. "
    "Present answers in a clear, concise way. "
    "When comparing or summarizing across months, call the relevant tools for each month needed."
)

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Transaction Q&A", layout="wide")

# -------------------------------------------------
# SESSION STATE INIT
# -------------------------------------------------
for key, default in [
    ("logged_in", False),
    ("username", ""),
    ("df_ref", {"df": None}),
    ("agent", None),
    ("loaded_pdf", None),
    ("chat_history", []),
    ("session_id", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# -------------------------------------------------
# LOGIN PAGE
# -------------------------------------------------
def show_login():
    st.title("🔐 Transaction Q&A Assistant")
    st.subheader("Please log in to access your statements")

    with st.form("login_form"):
        username = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if username in USERS and USERS[username][0] == password:
            st.session_state.logged_in   = True
            st.session_state.username    = username
            st.session_state.chat_history = []
            st.rerun()
        else:
            st.error("Invalid User ID or Password. Please try again.")

# -------------------------------------------------
# PDF LOADING
# -------------------------------------------------
@st.cache_data
def list_pdfs_for_user(prefix):
    return sorted([
        f for f in os.listdir(DATA_DIR)
        if f.endswith(".pdf") and f.startswith(prefix)
    ])

@st.cache_data
def extract_transactions_from_pdf(pdf_path):
    rows    = []
    headers = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table or len(table) < 2:
                continue
            if headers is None:
                headers = table[0]
            for row in table[1:]:
                if not any(cell is not None for cell in row):
                    continue
                # skip repeated header rows that appear on new pages
                normalized_row = [str(c).strip() if c else "" for c in row]
                normalized_hdr = [str(h).strip() if h else "" for h in headers]
                if normalized_row == normalized_hdr:
                    continue
                rows.append(row)

    return pd.DataFrame(rows, columns=headers)

# -------------------------------------------------
# DATA CLEANING
# -------------------------------------------------
def clean_transactions(df):
    df.columns = [c.strip().lower() for c in df.columns]

    column_map = {
        "transaction date": "date",
        "date":             "date",
        "description":      "description",
        "details":          "description",
        "amount":           "amount",
        "debit/credit":     "type",
        "type":             "type",
        "balance":          "balance",
    }
    df.rename(columns=column_map, inplace=True)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = (
        df["amount"].astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .astype(float)
    )
    df["type"] = df["type"].str.lower()

    return df

# -------------------------------------------------
# MAIN APP
# -------------------------------------------------
def show_app():
    username                      = st.session_state.username
    _, display_name, pdf_prefix   = USERS[username]

    # Header row with logout
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("📊 Transaction Q&A Assistant")
        st.caption(f"Logged in as: **{display_name}**")
    with col2:
        if st.button("Logout"):
            for key in ["logged_in", "username", "agent", "loaded_pdf", "chat_history"]:
                st.session_state[key] = False if key == "logged_in" else "" if key == "username" else None if key in ["agent", "loaded_pdf"] else []
            st.session_state["df_ref"] = {"df": None}
            st.rerun()

    # PDF selector
    pdf_files = list_pdfs_for_user(pdf_prefix)
    if not pdf_files:
        st.error(
            f"No PDF statements found for {display_name}. "
            "Run sample_statements_pdf_generater.py first."
        )
        st.stop()

    selected_pdf = st.selectbox("Select a transaction statement", pdf_files)

    if not selected_pdf:
        st.stop()

    pdf_path = os.path.join(DATA_DIR, selected_pdf)

    with st.spinner("Loading transactions..."):
        raw_df = extract_transactions_from_pdf(pdf_path)
        df     = clean_transactions(raw_df)

    st.success(f"Loaded {len(df)} transactions")
    with st.expander("View transactions", expanded=False):
        st.dataframe(df, use_container_width=True)

    # Build (or rebuild) the agent when the PDF changes
    st.session_state["df_ref"]["df"] = df

    if st.session_state["loaded_pdf"] != selected_pdf:
        llm   = ChatOpenAI(model=MODEL, temperature=0)
        tools = make_tools(st.session_state["df_ref"])
        st.session_state["agent"]        = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT)
        st.session_state["loaded_pdf"]   = selected_pdf
        st.session_state["chat_history"] = []
        st.session_state["session_id"]   = datetime.now().strftime("%Y%m%d_%H%M%S")

    # -------------------------------------------------
    # CHAT UI
    # -------------------------------------------------
    st.subheader("💬 Ask questions about your transactions")

    # Render existing chat history
    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_query = st.chat_input("e.g. Which month had the highest spending?")

    if user_query:
        # Show user message
        st.session_state["chat_history"].append({"role": "user", "content": user_query})
        log_message(username, st.session_state["session_id"], selected_pdf, "user", user_query)

        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Include the last 3 exchanges (6 messages) so the agent can
                # resolve follow-up references like "that month" or "those expenses"
                MEMORY_WINDOW = 3
                history  = st.session_state["chat_history"][-(MEMORY_WINDOW * 2):]
                messages = history + [{"role": "user", "content": user_query}]

                result = st.session_state["agent"].invoke({"messages": messages})
                answer = result["messages"][-1].content

            st.write(answer)
            log_message(username, st.session_state["session_id"], selected_pdf, "assistant", answer)

            # Optional: show agent reasoning in expander
            with st.expander("Agent reasoning trace", expanded=False):
                for msg in result["messages"]:
                    role    = getattr(msg, "type", "message")
                    content = msg.content or str(getattr(msg, "tool_calls", ""))
                    st.markdown(f"**{role}:** {content}")

        st.session_state["chat_history"].append({"role": "assistant", "content": answer})

# -------------------------------------------------
# ROUTER
# -------------------------------------------------
if st.session_state.logged_in:
    show_app()
else:
    show_login()
