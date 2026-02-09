"""
COPPER POC - Shared Vanna AI setup for SQL-from-natural-language.
Supports Ollama (local, Llama3) and Google Gemini (cloud deploy).
Used by the AI Assistant page; can be warmed in background at app start.

Vanna 2.0 moved the legacy text-to-SQL classes under vanna.legacy.*
The Gemini chat is implemented inline to avoid vanna.legacy.google's
BigQuery/VertexAI import side-effects.
"""

import os
import threading
import streamlit as st

from utils.data_loader import DB_PATH

# ChromaDB path (same directory layout as before)
CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(DB_PATH)), "chroma_db")

# Set by background warmup thread when setup_vanna() has finished (success or failure)
_vanna_warmup_done = False
_warmup_thread_started = False


def start_vanna_warmup_thread():
    """Start a daemon thread that runs setup_vanna() once. Safe to call every rerun."""
    global _warmup_thread_started
    if _warmup_thread_started:
        return
    _warmup_thread_started = True

    def _run():
        try:
            setup_vanna()
        finally:
            pass  # setup_vanna's finally already sets _vanna_warmup_done

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _get_gemini_api_key():
    """Return Gemini/Google API key from Streamlit secrets or env. Empty string if not set."""
    try:
        key = st.secrets.get("GOOGLE_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        return (key or "").strip()
    except Exception:
        return os.environ.get("GOOGLE_API_KEY", "").strip()


def is_vanna_warmup_done():
    """True if background warmup has completed."""
    return _vanna_warmup_done


# ---------------------------------------------------------------------------
# Import helpers – Vanna 2.0 moved classes under vanna.legacy.*
# ---------------------------------------------------------------------------

def _import_chromadb_vector_store():
    """Import ChromaDB_VectorStore from the installed Vanna version."""
    try:
        from vanna.legacy.chromadb import ChromaDB_VectorStore
        return ChromaDB_VectorStore
    except ImportError:
        pass
    try:
        from vanna.legacy.chromadb.chromadb_vector import ChromaDB_VectorStore
        return ChromaDB_VectorStore
    except ImportError:
        pass
    from vanna.chromadb import ChromaDB_VectorStore  # vanna <2.0 fallback
    return ChromaDB_VectorStore


def _import_ollama():
    """Import Ollama from the installed Vanna version."""
    try:
        from vanna.legacy.ollama import Ollama
        return Ollama
    except ImportError:
        pass
    try:
        from vanna.legacy.ollama.ollama import Ollama
        return Ollama
    except ImportError:
        pass
    from vanna.ollama import Ollama  # vanna <2.0 fallback
    return Ollama


# ---------------------------------------------------------------------------
# setup_vanna  – cached, called once per process
# ---------------------------------------------------------------------------

@st.cache_resource
def setup_vanna():
    """
    Initialize and train Vanna on the COPPER schema.
    Uses Gemini if GOOGLE_API_KEY is set (e.g. Streamlit Cloud); otherwise Ollama (local).
    Returns (vn, error, use_gemini). error is None on success.
    """
    global _vanna_warmup_done
    use_gemini = bool(_get_gemini_api_key())

    try:
        ChromaDB_VectorStore = _import_chromadb_vector_store()

        if use_gemini:
            # Inline Gemini chat to avoid vanna.legacy.google's BigQuery/VertexAI imports
            import google.generativeai as genai

            api_key = _get_gemini_api_key()
            if not api_key:
                return None, "Set GOOGLE_API_KEY in Streamlit Secrets or env for cloud deployment.", True

            genai.configure(api_key=api_key)

            class CopperVanna(ChromaDB_VectorStore):
                """ChromaDB vector store + Google Gemini LLM."""

                def __init__(self, config=None):
                    ChromaDB_VectorStore.__init__(self, config=config)
                    model_name = (config or {}).get("model_name", "gemini-3-flash-preview")
                    self.temperature = (config or {}).get("temperature", 0.7)
                    self.chat_model = genai.GenerativeModel(model_name)

                def system_message(self, message: str):
                    return message

                def user_message(self, message: str):
                    return message

                def assistant_message(self, message: str):
                    return message

                def submit_prompt(self, prompt, **kwargs) -> str:
                    response = self.chat_model.generate_content(
                        prompt,
                        generation_config={"temperature": self.temperature},
                    )
                    return response.text

            vn = CopperVanna(config={
                "path": CHROMA_PATH,
                "api_key": api_key,
                "model_name": "gemini-3-flash-preview",
            })

        else:
            Ollama = _import_ollama()

            class CopperVanna(ChromaDB_VectorStore, Ollama):
                def __init__(self, config=None):
                    ChromaDB_VectorStore.__init__(self, config=config)
                    Ollama.__init__(self, config=config)

            vn = CopperVanna(config={
                "path": CHROMA_PATH,
                "model": "llama3",
            })

        vn.connect_to_duckdb(url=DB_PATH, read_only=True)

        # ----- Training data -----
        training_data = [
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
            ) -- Medical device product catalog.""",
            """CREATE TABLE contracts (
                contract_id VARCHAR, tenant_id VARCHAR, idn_id VARCHAR, gpo_id VARCHAR,
                deal_structure VARCHAR, device_category VARCHAR,
                start_date DATE, end_date DATE, duration_months INTEGER,
                base_discount_pct DOUBLE, market_share_commitment DOUBLE,
                status VARCHAR, annual_volume_target INTEGER,
                safe_harbor_compliant BOOLEAN, aks_risk_flag VARCHAR
            ) -- Pricing contracts. tenant_id isolates by manufacturer.""",
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
            ) -- Individual purchase transactions. tenant_id isolates by manufacturer.""",
            """CREATE TABLE rebate_programs (
                rebate_id VARCHAR, contract_id VARCHAR, rebate_type VARCHAR,
                rebate_pct DOUBLE, trigger_type VARCHAR, trigger_threshold DOUBLE,
                orientation VARCHAR, earned BOOLEAN
            ) -- Rebate programs attached to contracts.""",
            "In MedTech pricing, 'lowest net' or 'pocket price' is the true floor price after all discounts.",
            "GPO admin fees are typically 1-3% of invoice price.",
            "PV (Primary Vendor) deals give the strongest pricing power (80%+ share). Access deals have no commitment.",
            "Price erosion means margin_pct is declining over time.",
            "The price waterfall shows how list_price gets discounted down to lowest_net_price.",
            "Safe Harbor compliance means rebate terms were pre-established. AKS risk flags indicate potential compliance issues.",
            "Data is multi-tenant (tenant_id). Tables transactions, contracts and views v_portfolio_summary, v_price_waterfall, v_customer_performance, v_monthly_trends, v_contract_risk have tenant_id; filter by current tenant.",
        ]
        for item in training_data:
            if item.startswith("CREATE"):
                vn.train(ddl=item)
            else:
                vn.train(documentation=item)

        example_pairs = [
            {"question": "What is the total revenue by device category?", "sql": "SELECT device_category, ROUND(SUM(invoice_price * quantity), 2) AS total_revenue FROM transactions GROUP BY device_category ORDER BY total_revenue DESC"},
            {"question": "What is the average margin by deal structure?", "sql": "SELECT deal_structure, ROUND(AVG(margin_pct), 1) AS avg_margin_pct, COUNT(*) AS transactions FROM transactions GROUP BY deal_structure ORDER BY avg_margin_pct DESC"},
            {"question": "Which customers have the lowest margins?", "sql": "SELECT i.name AS customer, i.tier, ROUND(AVG(t.margin_pct), 1) AS avg_margin, ROUND(SUM(t.invoice_price * t.quantity), 2) AS revenue FROM transactions t JOIN idns i ON t.idn_id = i.idn_id GROUP BY i.name, i.tier HAVING COUNT(*) > 10 ORDER BY avg_margin ASC LIMIT 10"},
            {"question": "Show the price waterfall for orthopedic implants", "sql": "SELECT ROUND(AVG(list_price), 2) AS avg_list_price, ROUND(AVG(list_price - invoice_price), 2) AS avg_contract_discount, ROUND(AVG(gpo_admin_fee), 2) AS avg_gpo_fee, ROUND(AVG(rebate_amount), 2) AS avg_rebate, ROUND(AVG(lowest_net_price), 2) AS avg_lowest_net FROM transactions WHERE device_category = 'Orthopedic Implants'"},
            {"question": "How many contracts are at risk?", "sql": "SELECT risk_status, COUNT(*) AS contract_count FROM v_contract_risk GROUP BY risk_status ORDER BY CASE risk_status WHEN 'Critical' THEN 1 WHEN 'At Risk' THEN 2 WHEN 'Watch' THEN 3 ELSE 4 END"},
            {"question": "What is the margin trend by quarter?", "sql": "SELECT quarter, ROUND(AVG(margin_pct), 1) AS avg_margin, ROUND(SUM(invoice_price * quantity), 2) AS total_revenue, COUNT(*) AS transactions FROM transactions GROUP BY quarter ORDER BY quarter"},
            {"question": "Which GPO gives us the best margins?", "sql": "SELECT g.name AS gpo_name, ROUND(AVG(t.margin_pct), 1) AS avg_margin, ROUND(SUM(t.invoice_price * t.quantity), 2) AS total_revenue, COUNT(DISTINCT t.contract_id) AS contracts FROM transactions t JOIN gpos g ON t.gpo_id = g.gpo_id GROUP BY g.name ORDER BY avg_margin DESC"},
            {"question": "Show rebate earn rates by type", "sql": "SELECT rebate_type, COUNT(*) AS total_programs, SUM(CASE WHEN earned THEN 1 ELSE 0 END) AS earned_count, ROUND(AVG(rebate_pct) * 100, 1) AS avg_rebate_pct, ROUND(SUM(CASE WHEN earned THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS earn_rate_pct FROM rebate_programs GROUP BY rebate_type ORDER BY earn_rate_pct DESC"},
            {"question": "What is the revenue by region?", "sql": "SELECT region, ROUND(SUM(invoice_price * quantity), 2) AS total_revenue, ROUND(AVG(margin_pct), 1) AS avg_margin, COUNT(DISTINCT idn_id) AS customers FROM transactions GROUP BY region ORDER BY total_revenue DESC"},
            {"question": "Which products have the highest price erosion?", "sql": "SELECT p.name AS product, p.category, ROUND(AVG(t.total_discount_pct) * 100, 1) AS avg_discount_pct FROM transactions t JOIN products p ON t.product_id = p.product_id GROUP BY p.name, p.category HAVING COUNT(*) > 20 ORDER BY avg_discount_pct DESC LIMIT 10"},
            {"question": "Which contracts are about to expire soon?", "sql": "SELECT c.contract_id, c.start_date, c.end_date, DATEDIFF('day', CURRENT_DATE, CAST(c.end_date AS DATE)) AS days_until_expiration FROM contracts c WHERE DATEDIFF('day', CURRENT_DATE, CAST(c.end_date AS DATE)) BETWEEN 0 AND 30 ORDER BY days_until_expiration ASC"},
        ]
        for pair in example_pairs:
            vn.train(question=pair["question"], sql=pair["sql"])

        return vn, None, use_gemini

    except ImportError as e:
        if use_gemini:
            return None, f"Missing Gemini dependency: {e}. Install with: pip install 'vanna[gemini]'", use_gemini
        return None, f"Missing dependency: {e}. Run: pip install 'vanna[chromadb]' ollama", use_gemini
    except Exception as e:
        err = str(e)
        if not use_gemini and ("Connection refused" in err or "connect" in err.lower()):
            return None, "Cannot connect to Ollama. Make sure Ollama is running: ollama serve", use_gemini
        return None, f"Error initializing Vanna: {err}", use_gemini
    finally:
        _vanna_warmup_done = True
