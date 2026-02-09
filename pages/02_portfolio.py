"""
COPPER POC - Portfolio Dashboard (Drive Module)
The main dashboard showing portfolio-level pricing intelligence.
"""

import streamlit as st
from utils.data_loader import (
    get_kpi, get_kpi_params, get_current_tenant_id, build_tenant_where,
    get_portfolio_summary, get_price_waterfall,
    get_customer_performance, get_monthly_trends, get_contract_risk,
)
from components.charts import (
    render_waterfall, render_margin_trend, render_revenue_by_category,
    render_deal_structure_pie, render_customer_treemap, render_risk_gauge,
    render_region_map,
)
from components.kpi_cards import render_kpi_row, format_currency, format_number
from components.filters import render_filters, build_where_clause

st.title("📊 Portfolio Dashboard")
st.caption("Drive Module — Portfolio-level pricing intelligence for managers and governance teams")

# ─── Filters ────────────────────────────────────────────────────────────────

filters = render_filters()
where = build_where_clause(filters)  # full filters for transaction-scoped KPIs
# View-appropriate WHERE for charts (each view supports only some dimensions)
where_waterfall = build_where_clause(filters, use_gpo_name=False, include_keys=["category"])
where_portfolio = build_where_clause(filters, use_gpo_name=False, include_keys=["category", "structure"])
where_trends = build_where_clause(filters, use_gpo_name=False, include_keys=["category"])
where_customers = build_where_clause(filters, use_gpo_name=True, include_keys=["region", "gpo"])
where_risk = build_where_clause(filters, use_gpo_name=False, include_keys=["category", "structure"])

# ─── KPI Cards (tenant-scoped) ──────────────────────────────────────────────

total_rev = get_kpi(f"SELECT ROUND(SUM(invoice_price * quantity), 2) FROM transactions{build_tenant_where(where)}")
avg_margin = get_kpi(f"SELECT ROUND(AVG(margin_pct), 1) FROM transactions{build_tenant_where(where)}")
active_contracts = get_kpi_params(
    "SELECT COUNT(*) FROM contracts WHERE tenant_id = ? AND status = 'Active'",
    [get_current_tenant_id()],
)
risk_conditions = (where_risk.replace(" WHERE ", "").strip() + " AND ") if where_risk else ""
at_risk_extra = risk_conditions + "risk_status IN ('Critical', 'At Risk')"
at_risk = get_kpi(f"SELECT COUNT(*) FROM v_contract_risk{build_tenant_where(at_risk_extra)}")

render_kpi_row([
    {"label": "Total Revenue", "value": format_currency(total_rev or 0), "delta": "+12.3% vs prior year", "delta_color": "normal"},
    {"label": "Avg Margin", "value": f"{avg_margin or 0}%", "delta": "-2.1pp vs target", "delta_color": "inverse"},
    {"label": "Active Contracts", "value": format_number(active_contracts or 0)},
    {"label": "At-Risk Deals", "value": format_number(at_risk or 0), "delta": f"{at_risk} need attention", "delta_color": "off"},
])

st.markdown("---")

# ─── Price Waterfall (Centerpiece) ──────────────────────────────────────────

st.subheader("💧 Price Waterfall Analysis")
st.caption("Decomposing List Price → Lowest Net across every discount layer. This is where margin leaks.")

waterfall_data = get_price_waterfall(where_waterfall, get_current_tenant_id())

waterfall_category = st.selectbox(
    "Select category",
    ["All"] + waterfall_data["device_category"].tolist(),
    key="waterfall_cat"
)
st.plotly_chart(
    render_waterfall(waterfall_data, waterfall_category),
    use_container_width=True,
)

st.markdown("---")

# ─── Margin Trend + Revenue Breakdown ──────────────────────────────────────

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("📈 Margin Trend")
    trends = get_monthly_trends(where_trends, get_current_tenant_id())
    st.plotly_chart(render_margin_trend(trends), use_container_width=True)

with col2:
    st.subheader("📦 Revenue by Category")
    portfolio = get_portfolio_summary(where_portfolio, get_current_tenant_id())
    st.plotly_chart(render_revenue_by_category(portfolio), use_container_width=True)

st.markdown("---")

# ─── Deal Structure + Customer Concentration ──────────────────────────────

col3, col4 = st.columns(2)

with col3:
    st.subheader("🤝 Deal Structure Mix")
    st.plotly_chart(render_deal_structure_pie(portfolio), use_container_width=True)

with col4:
    st.subheader("🌍 Revenue by Region")
    customers = get_customer_performance(where_customers, get_current_tenant_id())
    st.plotly_chart(render_region_map(customers), use_container_width=True)

st.markdown("---")

# ─── Customer Concentration Treemap ────────────────────────────────────────

st.subheader("🏥 Customer Concentration")
st.caption("Treemap: size = revenue, color = margin %. Red customers are eroding margin.")
st.plotly_chart(render_customer_treemap(customers), use_container_width=True)

st.markdown("---")

# ─── Risk Dashboard ────────────────────────────────────────────────────────

st.subheader("⚠️ Contract Risk Overview")
risk_data = get_contract_risk(where_risk, get_current_tenant_id())

critical = len(risk_data[risk_data["risk_status"] == "Critical"])
at_risk_count = len(risk_data[risk_data["risk_status"] == "At Risk"])
watch = len(risk_data[risk_data["risk_status"] == "Watch"])
healthy = len(risk_data[risk_data["risk_status"] == "Healthy"])

st.plotly_chart(render_risk_gauge(critical, at_risk_count, watch, healthy), use_container_width=True)

# Show critical contracts table
critical_contracts = risk_data[risk_data["risk_status"].isin(["Critical", "At Risk"])].head(10)
if len(critical_contracts) > 0:
    st.markdown("**Contracts needing attention:**")
    st.dataframe(
        critical_contracts[[
            "contract_id", "idn_name", "deal_structure", "device_category",
            "avg_margin_pct", "total_revenue", "risk_status", "aks_risk_flag"
        ]].rename(columns={
            "contract_id": "Contract",
            "idn_name": "Customer",
            "deal_structure": "Structure",
            "device_category": "Category",
            "avg_margin_pct": "Margin %",
            "total_revenue": "Revenue",
            "risk_status": "Risk",
            "aks_risk_flag": "AKS Flag",
        }),
        use_container_width=True,
        hide_index=True,
    )
