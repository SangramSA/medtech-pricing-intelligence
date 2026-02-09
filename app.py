"""
COPPER POC - Main Application Entrypoint
Comprehensive Pricing & Performance Excellence Resource
"""

import os
import streamlit as st

from config.tenant_config import get_tenants, get_tenant_id_by_name
from utils.ensure_db import ensure_data_ready
from utils.vanna_setup import start_vanna_warmup_thread

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure DB exists (runs generator once if missing; used for Streamlit Cloud / fresh local)
ensure_data_ready()
# Warm Vanna in background so AI Assistant page loads fast
start_vanna_warmup_thread()

st.set_page_config(
    page_title="COPPER - Pricing Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide Streamlit default elements for cleaner look (including duplicate sidebar page nav)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    div[data-testid="stSidebarHeader"] > img {
        height: 40px;
    }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 100%; }
    /* Sidebar ~25% wider and larger text */
    [data-testid="stSidebar"] { min-width: 26rem; width: 26rem; }
    [data-testid="stSidebar"] > div:first-child { width: 26rem; }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stCaption { font-size: 1.05rem !important; }
    [data-testid="stSidebar"] h1 { font-size: 1.75rem !important; }
    [data-testid="stSidebar"] h2 { font-size: 1.35rem !important; }
    /* Hide Streamlit's built-in multipage nav so only our custom "Navigate" radio shows */
    section[data-testid="stSidebarNav"], [data-testid="stSidebarNav"], [data-testid="stSidebarNavItems"] { display: none !important; }
    /* Hide sidebar collapse/icon button */
    [data-testid="stSidebar"] button:has(span[data-testid="stIconMaterial"]) { display: none !important; }
    /* Home page card-style sections */
    .copper-home-card {
        background-color: rgba(30, 37, 48, 0.6);
        border: 1px solid rgba(184, 115, 51, 0.25);
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
    }
    .copper-home-card h4 { margin-top: 0; margin-bottom: 0.75rem; color: #FAFAFA; }
    .copper-home-card table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    .copper-home-card th, .copper-home-card td { padding: 0.4rem 0.75rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.08); color: #FAFAFA; }
    .copper-home-card th { color: #B87333; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Sidebar branding
st.sidebar.markdown("""
# 🏥 COPPER
**Pricing Intelligence**
<small style="color: #B87333;">Comprehensive Pricing & Performance Excellence Resource</small>

---
""", unsafe_allow_html=True)

# Tenant selector (multi-tenancy demo) — drives data isolation
tenants = get_tenants()
tenant_names = [t["name"] for t in tenants]
tenant_display = st.sidebar.selectbox(
    "🏢 Manufacturer",
    tenant_names,
    help="Switch between tenants to see data isolation",
)
tenant_id = get_tenant_id_by_name(tenant_display)
st.session_state["tenant_id"] = tenant_id
tenant = tenant_display  # for caption

st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "📊 Portfolio (Drive)", "🔍 Customer Intel (Discover)",
     "🤖 AI Assistant"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Tenant: {tenant} | v0.1.0-POC")

# ─── Page Router ────────────────────────────────────────────────────────────

if page == "🏠 Home":
    st.title("🏥 COPPER")
    st.markdown("### Comprehensive Pricing & Performance Excellence Resource")
    st.markdown(
        '<p style="color: #B87333; font-size: 1rem; margin-top: -0.5rem;">MedTech pricing intelligence — dashboards, customer drill-downs, and natural language querying.</p>',
        unsafe_allow_html=True,
    )
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

    st.markdown("""
    <div class="copper-home-card">
    <h4>In this POC</h4>
    <table>
    <thead><tr><th>Area</th><th>What you can do</th></tr></thead>
    <tbody>
    <tr><td><strong>Portfolio (Drive)</strong></td><td>Margin trends, revenue by category, price waterfall, risk overview</td></tr>
    <tr><td><strong>Customer Intel (Discover)</strong></td><td>Drill down by customer (IDN), contracts, pricing, rebates</td></tr>
    <tr><td><strong>AI Assistant</strong></td><td>Ask questions about your pricing data in plain English</td></tr>
    </tbody>
    </table>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="copper-home-card">
    <h4>Capabilities in this demo</h4>
    <table>
    <thead><tr><th>Capability</th><th>Description</th></tr></thead>
    <tbody>
    <tr><td><strong>Price Waterfall</strong></td><td>Decompose list price to lowest net across discount layers</td></tr>
    <tr><td><strong>Deal / risk scoring</strong></td><td>Risk assessment and at-risk contract views</td></tr>
    <tr><td><strong>NL querying</strong></td><td>Ask pricing questions in plain English (AI Assistant)</td></tr>
    <tr><td><strong>Compliance</strong></td><td>Safe Harbor and Anti-Kickback flags on contracts</td></tr>
    <tr><td><strong>Multi-tenant</strong></td><td>Isolated data per manufacturer</td></tr>
    </tbody>
    </table>
    </div>
    """, unsafe_allow_html=True)

    st.info("Use the sidebar to open **Portfolio**, **Customer Intel**, or **AI Assistant**.")

elif page == "📊 Portfolio (Drive)":
    exec(open(os.path.join(_BASE_DIR, "pages", "02_portfolio.py")).read())

elif page == "🔍 Customer Intel (Discover)":
    exec(open(os.path.join(_BASE_DIR, "pages", "03_customer_intel.py")).read())

elif page == "🤖 AI Assistant":
    exec(open(os.path.join(_BASE_DIR, "pages", "04_ai_assistant.py")).read())
