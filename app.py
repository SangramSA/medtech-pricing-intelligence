"""
COPPER POC - Main Application Entrypoint
Comprehensive Pricing & Performance Excellence Resource
"""

import os
import streamlit as st

from config.tenant_config import get_tenants, get_tenant_id_by_name

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(
    page_title="COPPER - Pricing Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide Streamlit default elements for cleaner look
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    div[data-testid="stSidebarHeader"] > img {
        height: 40px;
    }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# Sidebar branding
st.sidebar.markdown("""
# 🏥 COPPER
**Pricing Intelligence**
<small style="color: #B87333;">Comprehensive Pricing & Performance Excellence Resource</small>

---
""", unsafe_allow_html=True)

# Tenant selector (multi-tenancy demo)
tenant = st.sidebar.selectbox(
    "🏢 Manufacturer",
    ["MedDevice Corp", "OrthoTech Inc"],
    help="Switch between tenants to see data isolation"
)

st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "📊 Portfolio (Drive)", "🔍 Customer Intel (Discover)",
     "🤖 AI Assistant", "⚙️ Architecture"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Tenant: {tenant} | v0.1.0-POC")

# ─── Page Router ────────────────────────────────────────────────────────────

if page == "🏠 Home":
    st.title("🏥 COPPER")
    st.markdown("### Comprehensive Pricing & Performance Excellence Resource")
    st.markdown("---")

    st.markdown("""
    **COPPER** is a MedTech pricing intelligence platform that gives medical device
    sales teams the data they need to negotiate confidently, protect margins, and
    ensure compliance.

    MedTech is a **$71B market** where even small pricing improvements translate to
    hundreds of millions in margin recovery. But today, sales teams negotiate with
    spreadsheets, tribal knowledge, and gut instinct.

    COPPER changes that.
    """)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📦 Platform Modules")
        st.markdown("""
        | Module | Purpose |
        |--------|---------|
        | **Discover** | Pre-deal intelligence — customer health, competitive landscape |
        | **Build** | Deal construction — pricing recommendations, guardrails |
        | **Monitor** | Active deal tracking — performance, at-risk alerts |
        | **Drive** | Portfolio dashboards — margin trends, revenue analysis |
        | **Optimize** | Opportunity identification — margin recovery, bundling |
        """)

    with col2:
        st.markdown("#### 🔑 Key Capabilities")
        st.markdown("""
        | Capability | Description |
        |-----------|-------------|
        | **Price Waterfall** | Decompose list price → lowest net across discount layers |
        | **Deal Scoring** | AI-powered risk assessment for every contract |
        | **NL Querying** | Ask pricing questions in plain English |
        | **Compliance** | Safe Harbor & Anti-Kickback monitoring |
        | **Multi-Tenant** | Isolated data per manufacturer |
        """)

    st.markdown("---")
    st.info("👈 Use the sidebar to navigate to **Portfolio (Drive)** for dashboards or **AI Assistant** to query data with natural language.")

elif page == "📊 Portfolio (Drive)":
    exec(open(os.path.join(_BASE_DIR, "pages", "02_portfolio.py")).read())

elif page == "🔍 Customer Intel (Discover)":
    exec(open(os.path.join(_BASE_DIR, "pages", "03_customer_intel.py")).read())

elif page == "🤖 AI Assistant":
    exec(open(os.path.join(_BASE_DIR, "pages", "04_ai_assistant.py")).read())

elif page == "⚙️ Architecture":
    exec(open(os.path.join(_BASE_DIR, "pages", "05_architecture.py")).read())
