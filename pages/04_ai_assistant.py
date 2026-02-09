"""
COPPER POC - AI Assistant (Vanna AI + Ollama or Gemini + DuckDB)
Natural language querying over MedTech pricing data.
Local: Ollama (Llama3). Cloud: Google Gemini (set GOOGLE_API_KEY in Secrets).
"""

import re
import time
import streamlit as st
from utils.data_loader import get_current_tenant_id
from utils.vanna_setup import setup_vanna, is_vanna_warmup_done

# Tables/views that are tenant-scoped (have tenant_id)
TENANT_SCOPED = ("transactions", "contracts", "v_portfolio_summary", "v_price_waterfall",
                 "v_customer_performance", "v_monthly_trends", "v_contract_risk")


def inject_tenant_filter(sql: str, tenant_id: str) -> str:
    """Inject tenant_id filter into generated SQL so AI Assistant respects manufacturer (tenant) isolation."""
    if not sql or not sql.strip():
        return sql
    sql_upper = sql.upper()
    if not any(re.search(rf"\b{t}\b", sql_upper) for t in (t.upper() for t in TENANT_SCOPED)):
        return sql
    tid = tenant_id.replace("'", "''")
    condition = f"tenant_id = '{tid}'"
    if re.search(r"\bWHERE\b", sql, re.IGNORECASE):
        sql = re.sub(r"(\bWHERE\b)", rf" WHERE {condition} AND ", sql, count=1)
    else:
        for pattern in [r"\bGROUP\s+BY\b", r"\bORDER\s+BY\b", r"\bLIMIT\s+\d+"]:
            m = re.search(pattern, sql, re.IGNORECASE)
            if m:
                sql = sql[: m.start()] + f" WHERE {condition} " + sql[m.start() :]
                break
        else:
            sql = sql.rstrip().rstrip(";") + f" WHERE {condition} "
    return sql


st.title("🤖 AI Pricing Assistant")
st.caption("Ask questions about your pricing data in plain English. Powered by Vanna AI +  Gemini.")

# ─── Wait for background warmup or get Vanna ─────────────────────────────────

if not is_vanna_warmup_done():
    st.info("Preparing AI… (runs once at app start)")
    time.sleep(2)
    st.rerun()

vn, error, use_gemini = setup_vanna()

# ─── Model caption ───────────────────────────────────────────────────────────

st.sidebar.markdown("### 🤖 AI Model")
if use_gemini:
    st.sidebar.markdown("Using **Gemini** (cloud)")
    st.sidebar.caption("Model: gemini-3-flash-preview")
else:
    st.sidebar.markdown("Using **Ollama** (local, free)")
    st.sidebar.caption("Model: llama3")
st.sidebar.markdown("---")

# ─── Chat Interface ──────────────────────────────────────────────────────────

if error:
    st.warning(error)
    st.markdown("---")
    st.markdown("### 💡 Setup Instructions")
    if use_gemini:
        st.markdown("Set **GOOGLE_API_KEY** in Streamlit Cloud Secrets (or env) for Gemini.")
    else:
        st.code("""
# 1. Install Ollama (if not installed):
#    Visit https://ollama.com/download

# 2. Pull a model:
ollama pull llama3

# 3. Make sure Ollama is running:
ollama serve

# 4. Restart the Streamlit app:
streamlit run app.py
    """, language="bash")
    st.markdown("---")
    st.markdown("### 📝 Example Questions You Can Ask")
    for ex in [
        "What is the total revenue by device category?",
        "Which customers have the lowest margins?",
        "Show the price waterfall for orthopedic implants",
        "How many contracts are at risk?",
        "What is the margin trend by quarter?",
        "Which GPO gives us the best margins?",
        "Show rebate earn rates by type",
        "Which products have the highest price erosion?",
    ]:
        st.markdown(f"- *{ex}*")

else:
    st.markdown("**Try asking:**")
    suggestions = [
        "What is the total revenue by device category?",
        "Which customers have the lowest margins?",
        "What is the margin trend by quarter?",
        "How many contracts are at risk?",
    ]
    suggestion_cols = st.columns(len(suggestions))
    for col, suggestion in zip(suggestion_cols, suggestions):
        if col.button(suggestion, key=f"suggest_{suggestion[:20]}"):
            st.session_state["user_question"] = suggestion

    st.markdown("---")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "sql" in msg:
                with st.expander("🔍 View SQL"):
                    st.code(msg["sql"], language="sql")
            if "dataframe" in msg:
                st.dataframe(msg["dataframe"], use_container_width=True, hide_index=True)

    user_input = st.chat_input("Ask a question about your pricing data...")
    if "user_question" in st.session_state:
        user_input = st.session_state.pop("user_question")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    sql = vn.generate_sql(user_input)
                    if sql and sql.strip():
                        tenant_id = get_current_tenant_id()
                        sql = inject_tenant_filter(sql, tenant_id)
                        st.markdown("Here's what I found:")
                        with st.expander("🔍 View generated SQL", expanded=False):
                            st.code(sql, language="sql")
                        try:
                            df = vn.run_sql(sql)
                            if df is not None and len(df) > 0:
                                st.dataframe(df, use_container_width=True, hide_index=True)
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": "Here's what I found:",
                                    "sql": sql,
                                    "dataframe": df,
                                })
                            else:
                                st.info("Query returned no results.")
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": "Query returned no results.",
                                    "sql": sql,
                                })
                        except Exception as e:
                            st.error(f"SQL execution error: {str(e)}")
                            st.code(sql, language="sql")
                            st.caption("The generated SQL had an error. Try rephrasing your question.")
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": f"SQL error: {str(e)}",
                                "sql": sql,
                            })
                    else:
                        st.warning("I couldn't generate a query for that question. Try rephrasing?")
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": "I couldn't generate a query for that question.",
                        })
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"Error: {str(e)}",
                    })

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
