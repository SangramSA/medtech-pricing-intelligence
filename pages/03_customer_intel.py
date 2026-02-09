"""
COPPER POC - Customer Intelligence (Discover Module)
Drill-down into individual customer (IDN) performance.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from utils.data_loader import query_params, get_idn_list
from components.charts import COPPER_COLORS, apply_copper_layout
from components.kpi_cards import render_kpi_row, format_currency

st.title("🔍 Customer Intelligence")
st.caption("Discover Module — Deep-dive into customer deal history, pricing, and risk")

# ─── Customer Selector ──────────────────────────────────────────────────────

idn_list = get_idn_list()
selected_idn_name = st.selectbox(
    "Select Customer (IDN)",
    idn_list["name"].tolist(),
)
selected_idn = idn_list[idn_list["name"] == selected_idn_name].iloc[0]
idn_id = selected_idn["idn_id"]

st.markdown("---")

# ─── Customer Overview KPIs ─────────────────────────────────────────────────

customer_data = query_params(
    "SELECT * FROM v_customer_performance WHERE idn_id = ?",
    [idn_id],
)

if len(customer_data) > 0:
    c = customer_data.iloc[0]
    render_kpi_row([
        {"label": "Total Revenue", "value": format_currency(c["total_revenue"])},
        {"label": "Avg Margin", "value": f"{c['avg_margin_pct']}%",
         "delta": "Below target" if c["avg_margin_pct"] < 20 else "On target",
         "delta_color": "inverse" if c["avg_margin_pct"] < 20 else "normal"},
        {"label": "Active Contracts", "value": str(c["active_contracts"])},
        {"label": "Transactions", "value": f"{int(c['transaction_count']):,}"},
    ])

    st.markdown(f"""
    | Attribute | Value |
    |-----------|-------|
    | **IDN Tier** | {selected_idn['tier']} |
    | **Region** | {selected_idn['region']} |
    | **GPO** | {c['gpo_name']} |
    | **Avg Discount** | {c['avg_discount_pct']}% |
    """)

st.markdown("---")

# ─── Contract Portfolio ────────────────────────────────────────────────────

st.subheader("📋 Contract Portfolio")

contracts = query_params(
    """
    SELECT
        c.contract_id,
        c.deal_structure,
        c.device_category,
        c.status,
        c.base_discount_pct,
        c.market_share_commitment,
        c.start_date,
        c.end_date,
        c.aks_risk_flag,
        COALESCE(cr.avg_margin_pct, 0) as avg_margin_pct,
        COALESCE(cr.total_revenue, 0) as total_revenue,
        COALESCE(cr.risk_status, 'Unknown') as risk_status
    FROM contracts c
    LEFT JOIN v_contract_risk cr ON c.contract_id = cr.contract_id
    WHERE c.idn_id = ?
    ORDER BY c.status, c.end_date
    """,
    [idn_id],
)

if len(contracts) > 0:
    # Color-code risk status
    st.dataframe(
        contracts[[
            "contract_id", "deal_structure", "device_category", "status",
            "base_discount_pct", "market_share_commitment", "avg_margin_pct",
            "total_revenue", "risk_status", "end_date"
        ]].rename(columns={
            "contract_id": "Contract",
            "deal_structure": "Structure",
            "device_category": "Category",
            "status": "Status",
            "base_discount_pct": "Base Discount",
            "market_share_commitment": "Share Commit",
            "avg_margin_pct": "Margin %",
            "total_revenue": "Revenue",
            "risk_status": "Risk",
            "end_date": "Expires",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # Deal structure breakdown
    col1, col2 = st.columns(2)

    with col1:
        struct_counts = contracts["deal_structure"].value_counts().reset_index()
        struct_counts.columns = ["structure", "count"]
        fig = go.Figure(go.Pie(
            labels=struct_counts["structure"],
            values=struct_counts["count"],
            hole=0.4,
            marker=dict(colors=px.colors.qualitative.Bold[:len(struct_counts)]),
        ))
        fig = apply_copper_layout(fig, "Deal Structure Mix", 300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "risk_status" in contracts.columns:
            risk_counts = contracts["risk_status"].value_counts().reset_index()
            risk_counts.columns = ["status", "count"]
            color_map = {
                "Critical": COPPER_COLORS["danger"],
                "At Risk": COPPER_COLORS["warning"],
                "Watch": COPPER_COLORS["info"],
                "Healthy": COPPER_COLORS["success"],
                "Unknown": "#666",
            }
            fig = go.Figure(go.Bar(
                x=risk_counts["status"],
                y=risk_counts["count"],
                marker_color=[color_map.get(s, "#666") for s in risk_counts["status"]],
                text=risk_counts["count"],
                textposition="auto",
            ))
            fig = apply_copper_layout(fig, "Risk Distribution", 300)
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ─── Pricing Analysis ──────────────────────────────────────────────────────

st.subheader("💰 Pricing Analysis")

pricing = query_params(
    """
    SELECT
        device_category,
        ROUND(AVG(list_price), 2) as avg_list,
        ROUND(AVG(invoice_price), 2) as avg_invoice,
        ROUND(AVG(lowest_net_price), 2) as avg_lowest_net,
        ROUND(AVG(margin_pct), 1) as avg_margin_pct,
        ROUND(AVG(total_discount_pct) * 100, 1) as avg_total_discount,
        COUNT(*) as txn_count
    FROM transactions
    WHERE idn_id = ?
    GROUP BY device_category
    ORDER BY avg_list DESC
    """,
    [idn_id],
)

if len(pricing) > 0:
    # Grouped bar chart: List vs Invoice vs Lowest Net by category
    fig = go.Figure()
    fig.add_trace(go.Bar(name="List Price", x=pricing["device_category"], y=pricing["avg_list"],
                         marker_color=COPPER_COLORS["info"]))
    fig.add_trace(go.Bar(name="Invoice Price", x=pricing["device_category"], y=pricing["avg_invoice"],
                         marker_color=COPPER_COLORS["primary"]))
    fig.add_trace(go.Bar(name="Lowest Net", x=pricing["device_category"], y=pricing["avg_lowest_net"],
                         marker_color=COPPER_COLORS["accent"]))
    fig.update_layout(barmode="group")
    fig = apply_copper_layout(fig, "Average Pricing by Category", 400)
    fig.update_yaxes(title_text="Price ($)")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(pricing.rename(columns={
        "device_category": "Category",
        "avg_list": "Avg List ($)",
        "avg_invoice": "Avg Invoice ($)",
        "avg_lowest_net": "Avg Lowest Net ($)",
        "avg_margin_pct": "Margin %",
        "avg_total_discount": "Total Discount %",
        "txn_count": "Transactions",
    }), use_container_width=True, hide_index=True)

st.markdown("---")

# ─── Transaction History (Recent) ──────────────────────────────────────────

st.subheader("📜 Recent Transactions")

recent_txns = query_params(
    """
    SELECT
        t.transaction_id,
        t.transaction_date,
        p.name as product_name,
        p.category,
        t.quantity,
        t.list_price,
        t.invoice_price,
        t.lowest_net_price,
        t.margin_pct,
        t.deal_structure
    FROM transactions t
    JOIN products p ON t.product_id = p.product_id
    WHERE t.idn_id = ?
    ORDER BY t.transaction_date DESC
    LIMIT 50
    """,
    [idn_id],
)

st.dataframe(recent_txns.rename(columns={
    "transaction_id": "TXN ID",
    "transaction_date": "Date",
    "product_name": "Product",
    "category": "Category",
    "quantity": "Qty",
    "list_price": "List ($)",
    "invoice_price": "Invoice ($)",
    "lowest_net_price": "Lowest Net ($)",
    "margin_pct": "Margin %",
    "deal_structure": "Structure",
}), use_container_width=True, hide_index=True)

# ─── Rebate Programs ──────────────────────────────────────────────────────

st.markdown("---")
st.subheader("🎯 Rebate Programs")

rebates = query_params(
    """
    SELECT
        r.rebate_id,
        r.contract_id,
        r.rebate_type,
        r.rebate_pct,
        r.trigger_type,
        r.trigger_threshold,
        r.orientation,
        r.earned
    FROM rebate_programs r
    JOIN contracts c ON r.contract_id = c.contract_id
    WHERE c.idn_id = ?
    ORDER BY r.rebate_type
    """,
    [idn_id],
)

if len(rebates) > 0:
    col1, col2 = st.columns([1, 1])
    with col1:
        earned = rebates["earned"].sum()
        total = len(rebates)
        st.metric("Rebates Earned", f"{earned}/{total}", f"{earned/total*100:.0f}% earn rate")

    with col2:
        avg_pct = rebates["rebate_pct"].mean() * 100
        st.metric("Avg Rebate %", f"{avg_pct:.1f}%")

    st.dataframe(rebates.rename(columns={
        "rebate_id": "Rebate ID",
        "contract_id": "Contract",
        "rebate_type": "Type",
        "rebate_pct": "Rate",
        "trigger_type": "Trigger",
        "trigger_threshold": "Threshold",
        "orientation": "Orientation",
        "earned": "Earned?",
    }), use_container_width=True, hide_index=True)
else:
    st.info("No rebate programs found for this customer.")
