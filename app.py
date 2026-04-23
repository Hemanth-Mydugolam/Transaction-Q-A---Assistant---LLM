import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from utils.tools import make_tools
from utils.pdf_loader import list_pdfs_for_user, extract_transactions_from_pdf, clean_transactions
from utils.logger import log_message, log_feedback

# -------------------------------------------------
# ENV SETUP
# -------------------------------------------------
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("OPENAI_API_KEY not found in .env")

# Load user credentials from .env
# Format: USER1_ID, USER1_PASSWORD, USER1_NAME  (supports USER1 through USER9)
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
MODEL                = "gpt-4o-mini"
DATA_DIR             = "data"
MEMORY_WINDOW        = 3    # number of past exchanges passed to the agent for context
IDLE_TIMEOUT_SECONDS = 300  # auto-logout after 5 minutes of inactivity

SYSTEM_PROMPT = (
    "You are a financial assistant that answers questions about the user's bank transactions. "
    "Use the available tools to look up, filter, and summarize transaction data. "
    "Always use a tool before answering — never make up numbers. "
    "Present answers in a clear, concise way. "
    "When comparing or summarizing across months, call the relevant tools for each month needed."
)

SUGGESTED_QUESTIONS = [
    "Which month had the highest spending?",
    "What were my top 3 expenses overall?",
    "Give me a debit and credit summary for each month.",
]

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Transaction Q&A", layout="wide")

# -------------------------------------------------
# SESSION STATE INIT
# -------------------------------------------------
for key, default in [
    ("logged_in",       False),
    ("username",        ""),
    ("df_ref",          {"df": None}),
    ("agent",           None),
    ("loaded_pdf",      None),
    ("chat_history",    []),
    ("session_id",      None),
    ("suggested_query", None),
    ("login_time",      None),
    ("last_activity",   None),
    ("timed_out",       False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# -------------------------------------------------
# LOGIN PAGE  — centered layout
# -------------------------------------------------
def show_login():
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🔐 Transaction Q&A Assistant")
        st.markdown(
            "Your personal AI-powered assistant for understanding your bank statements. "
            "Log in to get started."
        )
        st.markdown("---")

        with st.form("login_form"):
            username  = st.text_input("User ID")
            password  = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if username in USERS and USERS[username][0] == password:
                now = datetime.now()
                st.session_state.logged_in    = True
                st.session_state.username     = username
                st.session_state.chat_history = []
                st.session_state.login_time   = now
                st.session_state.last_activity = now
                st.session_state.timed_out    = False
                st.rerun()
            else:
                st.error("Invalid User ID or Password. Please try again.")

        if st.session_state.get("timed_out"):
            st.warning("⏱ Your session expired after 5 minutes of inactivity. Please log in again.")
            st.session_state.timed_out = False

# -------------------------------------------------
# MAIN APP
# -------------------------------------------------
def _reset_session():
    """Clear all session state and flag for timeout message if needed."""
    for key in ["logged_in", "username", "agent", "loaded_pdf", "chat_history", "session_id",
                "suggested_query", "login_time", "last_activity"]:
        st.session_state[key] = (
            False if key == "logged_in"
            else "" if key == "username"
            else None if key in ["agent", "loaded_pdf", "session_id", "suggested_query", "login_time", "last_activity"]
            else []
        )
    st.session_state["df_ref"] = {"df": None}


def show_app():
    username                    = st.session_state.username
    _, display_name, pdf_prefix = USERS[username]
    now                         = datetime.now()

    # --- Idle timeout check (fires on every rerun) ---
    last = st.session_state.get("last_activity")
    if last and (now - last).total_seconds() > IDLE_TIMEOUT_SECONDS:
        _reset_session()
        st.session_state["timed_out"] = True
        st.rerun()

    # Update activity timestamp for this rerun
    st.session_state["last_activity"] = now

    # --- Header ---
    login_time    = st.session_state.get("login_time", now)
    elapsed       = now - login_time
    elapsed_mins  = int(elapsed.total_seconds() // 60)
    elapsed_str   = f"{elapsed_mins}m" if elapsed_mins > 0 else "just now"
    login_str     = login_time.strftime("%I:%M %p")

    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("📊 Transaction Q&A Assistant")
        st.caption(
            f"👤 **{display_name}** &nbsp;|&nbsp; "
            f"🕐 Logged in at {login_str} ({elapsed_str} ago) &nbsp;|&nbsp; "
            f"⏱ Auto-logout after {IDLE_TIMEOUT_SECONDS // 60} min inactivity"
        )
    with col2:
        if st.button("Logout"):
            _reset_session()
            st.rerun()

    # Auto-load the user's statement (no dropdown needed — one PDF per user)
    pdf_files = list_pdfs_for_user(DATA_DIR, pdf_prefix)
    if not pdf_files:
        st.error(
            f"No PDF statements found for {display_name}. "
            "Run: python scripts/generate_statements.py"
        )
        st.stop()

    selected_pdf = pdf_files[0]
    pdf_path     = os.path.join(DATA_DIR, selected_pdf)

    with st.spinner("Loading your statement..."):
        raw_df = extract_transactions_from_pdf(pdf_path)
        df     = clean_transactions(raw_df)

    # Welcome banner + app description
    st.markdown(f"### Welcome, {display_name}! 👋")
    st.markdown(
        "This assistant helps you explore and understand your bank transaction history "
        "using natural language. Ask anything about your spending, credits, monthly summaries, "
        "or top expenses — the AI will analyse your statement and answer instantly."
    )

    with st.expander("📄 View raw transactions", expanded=False):
        st.dataframe(df, use_container_width=True)

    st.divider()

    # Build (or rebuild) agent when the PDF changes
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

    # Render chat history
    for i, message in enumerate(st.session_state["chat_history"]):
        with st.chat_message(message["role"]):
            st.write(message["content"])

            # Feedback buttons only on assistant messages
            if message["role"] == "assistant":
                feedback = message.get("feedback")
                if feedback is None:
                    col_up, col_down, _ = st.columns([1, 1, 10])
                    if col_up.button("👍", key=f"fb_up_{i}", help="Helpful"):
                        st.session_state["chat_history"][i]["feedback"] = "positive"
                        question = st.session_state["chat_history"][i - 1]["content"] if i > 0 else ""
                        log_feedback(username, st.session_state["session_id"], selected_pdf, "positive", question, message["content"])
                        st.rerun()
                    if col_down.button("👎", key=f"fb_down_{i}", help="Not helpful"):
                        st.session_state["chat_history"][i]["feedback"] = "negative"
                        question = st.session_state["chat_history"][i - 1]["content"] if i > 0 else ""
                        log_feedback(username, st.session_state["session_id"], selected_pdf, "negative", question, message["content"])
                        st.rerun()
                elif feedback == "positive":
                    st.caption("👍 Marked as helpful")
                else:
                    st.caption("👎 Feedback recorded")

    # Suggested questions — shown only on a fresh session (empty chat)
    if not st.session_state["chat_history"]:
        st.markdown("**Suggested questions:**")
        cols = st.columns(3)
        for i, question in enumerate(SUGGESTED_QUESTIONS):
            if cols[i].button(question, use_container_width=True):
                st.session_state["suggested_query"] = question
                st.rerun()

    # Determine active query: button click takes priority over typed input
    typed_query = st.chat_input("Type your question here...")
    active_query = None
    if st.session_state["suggested_query"]:
        active_query = st.session_state["suggested_query"]
        st.session_state["suggested_query"] = None
    elif typed_query:
        active_query = typed_query

    if active_query:
        st.session_state["chat_history"].append({"role": "user", "content": active_query})
        log_message(username, st.session_state["session_id"], selected_pdf, "user", active_query)

        with st.chat_message("user"):
            st.write(active_query)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                history  = st.session_state["chat_history"][-(MEMORY_WINDOW * 2):]
                messages = history + [{"role": "user", "content": active_query}]
                result   = st.session_state["agent"].invoke({"messages": messages})
                answer   = result["messages"][-1].content

            st.write(answer)
            log_message(username, st.session_state["session_id"], selected_pdf, "assistant", answer)

            with st.expander("Agent reasoning trace", expanded=False):
                for msg in result["messages"]:
                    role    = getattr(msg, "type", "message")
                    content = msg.content or str(getattr(msg, "tool_calls", ""))
                    st.markdown(f"**{role}:** {content}")

            # Append assistant message now so the index is known for feedback keys
            st.session_state["chat_history"].append({"role": "assistant", "content": answer, "feedback": None})
            asst_idx = len(st.session_state["chat_history"]) - 1

            # Show feedback buttons immediately for this new answer
            col_up, col_down, _ = st.columns([1, 1, 10])
            if col_up.button("👍", key=f"fb_up_{asst_idx}", help="Helpful"):
                st.session_state["chat_history"][asst_idx]["feedback"] = "positive"
                log_feedback(username, st.session_state["session_id"], selected_pdf, "positive", active_query, answer)
                st.rerun()
            if col_down.button("👎", key=f"fb_down_{asst_idx}", help="Not helpful"):
                st.session_state["chat_history"][asst_idx]["feedback"] = "negative"
                log_feedback(username, st.session_state["session_id"], selected_pdf, "negative", active_query, answer)
                st.rerun()

# -------------------------------------------------
# ROUTER
# -------------------------------------------------
if st.session_state.logged_in:
    show_app()
else:
    show_login()
