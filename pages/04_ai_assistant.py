"""
COPPER POC - AI Assistant (Vanna AI + Ollama + DuckDB)
Natural language querying over MedTech pricing data.
Uses local Ollama models — no API key needed.
"""

import os
import re
import streamlit as st
from utils.data_loader import DB_PATH, get_current_tenant_id

# ChromaDB persistence under project root (keeps vector store out of repo root)
CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(DB_PATH)), "chroma_db")

# Tables/views that are tenant-scoped (have tenant_id)
TENANT_SCOPED = ("transactions", "contracts", "v_portfolio_summary", "v_price_waterfall",
                 "v_customer_performance", "v_monthly_trends", "v_contract_risk")


def inject_tenant_filter(sql: str, tenant_id: str) -> str:
    """Inject tenant_id filter into generated SQL so AI Assistant respects manufacturer (tenant) isolation."""
    if not sql or not sql.strip():
        return sql
    # Only inject if the query references a tenant-scoped table/view
    sql_upper = sql.upper()
    if not any(re.search(rf"\b{t}\b", sql_upper) for t in (t.upper() for t in TENANT_SCOPED)):
        return sql
    tid = tenant_id.replace("'", "''")
    condition = f"tenant_id = '{tid}'"
    # Add after first WHERE, or add new WHERE before GROUP BY / ORDER BY / LIMIT
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
st.caption("Ask questions about your pricing data in plain English. Powered by Vanna AI + Ollama (local LLM) + DuckDB.")

# ─── Vanna AI Setup with Ollama ─────────────────────────────────────────────

@st.cache_resource
def setup_vanna():
    """Initialize and train Vanna AI on the COPPER schema using Ollama."""
    try:
        from vanna.legacy.ollama import Ollama
        from vanna.legacy.chromadb import ChromaDB_VectorStore

        class CopperVanna(ChromaDB_VectorStore, Ollama):
            def __init__(self, config=None):
                ChromaDB_VectorStore.__init__(self, config=config)
                Ollama.__init__(self, config=config)

        vn = CopperVanna(config={
            "path": CHROMA_PATH,
            "model": "llama3",  # or mistral, codellama, etc.
        })

        # Connect to DuckDB (read_only to match data_loader; avoids ConnectionException when switching tabs)
        vn.connect_to_duckdb(url=DB_PATH, read_only=True)

        # Train on schema DDL
        training_data = [
            # Table definitions
            """CREATE TABLE gpos (
                gpo_id VARCHAR, name VARCHAR, admin_fee_pct DOUBLE, member_count INTEGER
            ) -- Group Purchasing Organizations that negotiate contracts for member hospitals""",

            """CREATE TABLE idns (
                idn_id VARCHAR, name VARCHAR, gpo_id VARCHAR, facility_count INTEGER,
                annual_spend BIGINT, region VARCHAR, state VARCHAR, tier VARCHAR
            ) -- Integrated Delivery Networks (hospital systems). tier is Large/Medium/Small""",

            """CREATE TABLE products (
                product_id VARCHAR, name VARCHAR, category VARCHAR,
                list_price DOUBLE, cost DOUBLE, sku VARCHAR
            ) -- Medical device product catalog. category: Orthopedic Implants, Cardiovascular, Surgical Instruments, Consumables""",

            """CREATE TABLE contracts (
                contract_id VARCHAR, tenant_id VARCHAR, idn_id VARCHAR, gpo_id VARCHAR,
                deal_structure VARCHAR, device_category VARCHAR,
                start_date DATE, end_date DATE, duration_months INTEGER,
                base_discount_pct DOUBLE, market_share_commitment DOUBLE,
                status VARCHAR, annual_volume_target INTEGER,
                safe_harbor_compliant BOOLEAN, aks_risk_flag VARCHAR
            ) -- Pricing contracts. tenant_id isolates data by manufacturer. deal_structure: PV, DV, TV, Access, All Play. status: Active/Expired/Renewed/Pending""",

            """CREATE TABLE transactions (
                transaction_id VARCHAR, tenant_id VARCHAR, contract_id VARCHAR, idn_id VARCHAR,
                gpo_id VARCHAR, product_id VARCHAR, transaction_date DATE,
                quantity INTEGER, list_price DOUBLE, invoice_price DOUBLE,
                gpo_admin_fee DOUBLE, rebate_amount DOUBLE,
                lowest_net_price DOUBLE, unit_cost DOUBLE, margin DOUBLE,
                margin_pct DOUBLE, total_discount_pct DOUBLE,
                deal_structure VARCHAR, device_category VARCHAR,
                region VARCHAR, idn_tier VARCHAR, quarter VARCHAR,
                year INTEGER, month INTEGER
            ) -- Individual purchase transactions. tenant_id isolates by manufacturer. lowest_net_price = invoice_price - gpo_admin_fee - rebate_amount""",

            """CREATE TABLE rebate_programs (
                rebate_id VARCHAR, contract_id VARCHAR, rebate_type VARCHAR,
                rebate_pct DOUBLE, trigger_type VARCHAR, trigger_threshold DOUBLE,
                orientation VARCHAR, earned BOOLEAN
            ) -- Rebate programs attached to contracts. rebate_type: Volume/Loyalty/Bundle/Growth. orientation: Offensive (reward growth) or Defensive (reward maintenance)""",

            # Domain documentation
            "In MedTech pricing, 'lowest net' or 'pocket price' is the true floor price after all discounts: invoice_price minus GPO admin fees minus rebates.",
            "GPO admin fees are typically 1-3% of invoice price, paid by the vendor to the GPO for contract access.",
            "PV (Primary Vendor) deals give the strongest pricing power (80%+ market share commitment). Access deals have no commitment and highest prices.",
            "Price erosion means margin_pct is declining over time. Look at trends in margin_pct grouped by quarter.",
            "The price waterfall shows how list_price gets discounted down to lowest_net_price through contract discounts, GPO fees, and rebates.",
            "Safe Harbor compliance means rebate terms were pre-established and contracted. Anti-Kickback Statute (AKS) risk flags indicate potential compliance issues.",
            "Data is multi-tenant by manufacturer (tenant_id). Tables transactions, contracts and views v_portfolio_summary, v_price_waterfall, v_customer_performance, v_monthly_trends, v_contract_risk all have tenant_id; queries must filter by the current tenant for isolation.",
        ]

        for item in training_data:
            if item.startswith("CREATE"):
                vn.train(ddl=item)
            else:
                vn.train(documentation=item)

        # Train on example question-SQL pairs
        example_pairs = [
            {
                "question": "What is the total revenue by device category?",
                "sql": "SELECT device_category, ROUND(SUM(invoice_price * quantity), 2) AS total_revenue FROM transactions GROUP BY device_category ORDER BY total_revenue DESC"
            },
            {
                "question": "What is the average margin by deal structure?",
                "sql": "SELECT deal_structure, ROUND(AVG(margin_pct), 1) AS avg_margin_pct, COUNT(*) AS transactions FROM transactions GROUP BY deal_structure ORDER BY avg_margin_pct DESC"
            },
            {
                "question": "Which customers have the lowest margins?",
                "sql": "SELECT i.name AS customer, i.tier, ROUND(AVG(t.margin_pct), 1) AS avg_margin, ROUND(SUM(t.invoice_price * t.quantity), 2) AS revenue FROM transactions t JOIN idns i ON t.idn_id = i.idn_id GROUP BY i.name, i.tier HAVING COUNT(*) > 10 ORDER BY avg_margin ASC LIMIT 10"
            },
            {
                "question": "Show the price waterfall for orthopedic implants",
                "sql": "SELECT ROUND(AVG(list_price), 2) AS avg_list_price, ROUND(AVG(list_price - invoice_price), 2) AS avg_contract_discount, ROUND(AVG(gpo_admin_fee), 2) AS avg_gpo_fee, ROUND(AVG(rebate_amount), 2) AS avg_rebate, ROUND(AVG(lowest_net_price), 2) AS avg_lowest_net FROM transactions WHERE device_category = 'Orthopedic Implants'"
            },
            {
                "question": "How many contracts are at risk?",
                "sql": "SELECT risk_status, COUNT(*) AS contract_count FROM v_contract_risk GROUP BY risk_status ORDER BY CASE risk_status WHEN 'Critical' THEN 1 WHEN 'At Risk' THEN 2 WHEN 'Watch' THEN 3 ELSE 4 END"
            },
            {
                "question": "What is the margin trend by quarter?",
                "sql": "SELECT quarter, ROUND(AVG(margin_pct), 1) AS avg_margin, ROUND(SUM(invoice_price * quantity), 2) AS total_revenue, COUNT(*) AS transactions FROM transactions GROUP BY quarter ORDER BY quarter"
            },
            {
                "question": "Which GPO gives us the best margins?",
                "sql": "SELECT g.name AS gpo_name, ROUND(AVG(t.margin_pct), 1) AS avg_margin, ROUND(SUM(t.invoice_price * t.quantity), 2) AS total_revenue, COUNT(DISTINCT t.contract_id) AS contracts FROM transactions t JOIN gpos g ON t.gpo_id = g.gpo_id GROUP BY g.name ORDER BY avg_margin DESC"
            },
            {
                "question": "Show rebate earn rates by type",
                "sql": "SELECT rebate_type, COUNT(*) AS total_programs, SUM(CASE WHEN earned THEN 1 ELSE 0 END) AS earned_count, ROUND(AVG(rebate_pct) * 100, 1) AS avg_rebate_pct, ROUND(SUM(CASE WHEN earned THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS earn_rate_pct FROM rebate_programs GROUP BY rebate_type ORDER BY earn_rate_pct DESC"
            },
            {
                "question": "What is the revenue by region?",
                "sql": "SELECT region, ROUND(SUM(invoice_price * quantity), 2) AS total_revenue, ROUND(AVG(margin_pct), 1) AS avg_margin, COUNT(DISTINCT idn_id) AS customers FROM transactions GROUP BY region ORDER BY total_revenue DESC"
            },
            {
                "question": "Which products have the highest price erosion?",
                "sql": "SELECT p.name AS product, p.category, ROUND(AVG(t.total_discount_pct) * 100, 1) AS avg_discount_pct, ROUND(AVG(t.margin_pct), 1) AS avg_margin, COUNT(*) AS transactions FROM transactions t JOIN products p ON t.product_id = p.product_id GROUP BY p.name, p.category HAVING COUNT(*) > 20 ORDER BY avg_discount_pct DESC LIMIT 10"
            },
            {
                "question": "Which contracts are about to expire soon?",
                "sql": "SELECT c.contract_id, c.start_date, c.end_date, DATEDIFF('day', CURRENT_DATE, CAST(c.end_date AS DATE)) AS days_until_expiration FROM contracts c WHERE DATEDIFF('day', CURRENT_DATE, CAST(c.end_date AS DATE)) BETWEEN 0 AND 30 ORDER BY days_until_expiration ASC"
            },
        ]

        for pair in example_pairs:
            vn.train(question=pair["question"], sql=pair["sql"])

        return vn, None

    except ImportError as e:
        return None, f"⚠️ Missing dependency: {str(e)}. Run: `pip install 'vanna[chromadb]' ollama`"
    except Exception as e:
        error_msg = str(e)
        if "Connection refused" in error_msg or "connect" in error_msg.lower():
            return None, "⚠️ Cannot connect to Ollama. Make sure Ollama is running: `ollama serve`"
        return None, f"⚠️ Error initializing Vanna: {error_msg}"


# ─── Model Selector ────────────────────────────────────────────────────────

st.sidebar.markdown("### 🤖 AI Model")
st.sidebar.markdown("Using **Ollama** (local, free)")
st.sidebar.caption("Model: llama3")
st.sidebar.markdown("---")

# ─── Chat Interface ────────────────────────────────────────────────────────

vn, error = setup_vanna()

if error:
    st.warning(error)
    st.markdown("---")
    st.markdown("### 💡 Setup Instructions")
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
    examples = [
        "What is the total revenue by device category?",
        "Which customers have the lowest margins?",
        "Show the price waterfall for orthopedic implants",
        "How many contracts are at risk?",
        "What is the margin trend by quarter?",
        "Which GPO gives us the best margins?",
        "Show rebate earn rates by type",
        "Which products have the highest price erosion?",
    ]
    for ex in examples:
        st.markdown(f"- *{ex}*")

else:
    # Suggested questions
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

    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "sql" in msg:
                with st.expander("🔍 View SQL"):
                    st.code(msg["sql"], language="sql")
            if "dataframe" in msg:
                st.dataframe(msg["dataframe"], use_container_width=True, hide_index=True)

    # Chat input
    user_input = st.chat_input("Ask a question about your pricing data...")

    # Handle suggestion clicks
    if "user_question" in st.session_state:
        user_input = st.session_state.pop("user_question")

    if user_input:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking... (local model, may take a few seconds)"):
                try:
                    # Generate SQL
                    sql = vn.generate_sql(user_input)

                    if sql and sql.strip():
                        # Scope to current tenant (manufacturer) for data isolation
                        tenant_id = get_current_tenant_id()
                        sql = inject_tenant_filter(sql, tenant_id)

                        st.markdown("Here's what I found:")

                        with st.expander("🔍 View generated SQL", expanded=False):
                            st.code(sql, language="sql")

                        # Execute SQL
                        try:
                            df = vn.run_sql(sql)
                            if df is not None and len(df) > 0:
                                st.dataframe(df, use_container_width=True, hide_index=True)

                                # Store in history
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

    # Clear chat button
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
