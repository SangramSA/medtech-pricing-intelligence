"""
COPPER POC - Architecture Visualization
Shows the data pipeline and system design.
"""

import streamlit as st

st.title("⚙️ Data Architecture")
st.caption("How COPPER ingests, transforms, and serves MedTech pricing data")

st.subheader("🔄 Data Pipeline")

st.graphviz_chart("""
digraph {
    rankdir=TB
    bgcolor="transparent"
    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fontcolor="white"]
    edge [color="#B87333", penwidth=1.5]

    subgraph cluster_source {
        label="SOURCE SYSTEMS"
        style="dashed"
        fontcolor="#B87333"
        color="#B87333"
        CRM [label="CRM (Salesforce)", fillcolor="#2C3E50"]
        ERP [label="ERP (SAP)", fillcolor="#2C3E50"]
        CLM [label="Contract Mgmt", fillcolor="#2C3E50"]
        EXT [label="External Data", fillcolor="#2C3E50"]
    }

    subgraph cluster_ingest {
        label="INGESTION LAYER"
        style="dashed"
        fontcolor="#B87333"
        color="#B87333"
        BATCH [label="Batch ETL", fillcolor="#34495E"]
        AI_ING [label="AI Doc Extraction", fillcolor="#8B5E3C"]
    }

    RAW [label="RAW LAYER", fillcolor="#2C3E50"]

    subgraph cluster_transform {
        label="TRANSFORMATION LAYER"
        style="dashed"
        fontcolor="#B87333"
        color="#B87333"
        CLEAN [label="Clean and Validate", fillcolor="#34495E"]
        MODEL [label="Business Logic", fillcolor="#34495E"]
        AI_TR [label="AI Entity Resolution", fillcolor="#8B5E3C"]
    }

    subgraph cluster_serve {
        label="SERVING LAYER"
        style="dashed"
        fontcolor="#B87333"
        color="#B87333"
        DASH [label="Dashboards", fillcolor="#34495E"]
        API [label="Real-time API", fillcolor="#34495E"]
        AI_SV [label="AI Recommendations", fillcolor="#8B5E3C"]
    }

    APP [label="COPPER Application", fillcolor="#B87333", fontsize=13]

    CRM -> BATCH
    ERP -> BATCH
    CLM -> AI_ING
    EXT -> BATCH
    BATCH -> RAW
    AI_ING -> RAW
    RAW -> CLEAN
    CLEAN -> MODEL
    CLEAN -> AI_TR
    AI_TR -> MODEL
    MODEL -> DASH
    MODEL -> API
    MODEL -> AI_SV
    DASH -> APP
    API -> APP
    AI_SV -> APP
}
""")

st.markdown("---")

st.subheader("🛠️ Technology Stack")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### POC Stack (Current)")
    st.markdown("""
    | Layer | Technology |
    |-------|-----------|
    | **Storage** | DuckDB |
    | **Transform** | DuckDB SQL |
    | **Dashboard** | Streamlit |
    | **Charts** | Plotly |
    | **AI/NLQ** | Vanna AI + GPT-4o |
    | **Data Gen** | Faker + NumPy |
    """)

with col2:
    st.markdown("#### Production Stack (Target)")
    st.markdown("""
    | Layer | Technology |
    |-------|-----------|
    | **Storage** | Snowflake / BigQuery |
    | **Transform** | dbt Core |
    | **Orchestration** | Airflow / Dagster |
    | **Dashboard** | React + Plotly |
    | **AI/NLQ** | Vanna AI / Custom |
    | **Ingestion** | Fivetran / Airbyte |
    """)

st.markdown("---")

st.subheader("📊 Data Model")

st.graphviz_chart("""
digraph {
    rankdir=LR
    bgcolor="transparent"
    node [shape=record, style="filled", fontname="Helvetica", fontsize=10, fontcolor="white", fillcolor="#2C3E50"]
    edge [color="#B87333", penwidth=1.2]

    gpos [label="{GPOs|gpo_id PK\\lname\\ladmin_fee_pct\\l}"]
    idns [label="{IDNs|idn_id PK\\lgpo_id FK\\ltier\\lregion\\l}"]
    facilities [label="{Facilities|facility_id PK\\lidn_id FK\\ltype\\l}"]
    products [label="{Products|product_id PK\\lcategory\\llist_price\\l}"]
    contracts [label="{Contracts|contract_id PK\\lidn_id FK\\ldeal_structure\\lbase_discount_pct\\l}"]
    rebates [label="{Rebates|rebate_id PK\\lcontract_id FK\\lrebate_type\\l}"]
    txns [label="{Transactions|transaction_id PK\\lcontract_id FK\\lproduct_id FK\\llowest_net_price\\lmargin_pct\\l}", fillcolor="#B87333"]

    gpos -> idns
    idns -> facilities
    idns -> contracts
    gpos -> contracts
    contracts -> rebates
    contracts -> txns
    products -> txns
}
""")

st.markdown("---")

st.subheader("🏢 Multi-Tenancy Architecture")

st.markdown("""
The POC demonstrates tenant isolation through a sidebar selector. In production,
this maps to schema-per-tenant with row-level security as defense-in-depth.

| Approach | Isolation | Cost | Best For |
|----------|-----------|------|----------|
| Shared DB + tenant column | Low | Lowest | Early-stage, small customers |
| **Schema per tenant** | **Medium** | **Moderate** | **Recommended for COPPER** |
| Database per tenant | High | Highest | Enterprise / regulated customers |
""")

st.markdown("---")

st.subheader("🤖 AI Agent Integration Points")

st.markdown("""
| Layer | AI Capability | Status |
|-------|--------------|--------|
| **Ingestion** | Contract PDF extraction, auto-classification | Planned |
| **Transformation** | Entity resolution, anomaly detection | Planned |
| **Serving** | NL querying, price recommendations, deal risk scoring | **Active (AI Assistant page)** |
""")

st.info("The AI Assistant page demonstrates the Serving Layer integration using Vanna AI for natural language querying over DuckDB.")
