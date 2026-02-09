"""
COPPER POC - Reusable Plotly chart components.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Copper-themed color palette
COPPER_COLORS = {
    "primary": "#B87333",
    "secondary": "#D4956A",
    "accent": "#8B5E3C",
    "success": "#2ECC71",
    "warning": "#F39C12",
    "danger": "#E74C3C",
    "info": "#3498DB",
    "dark": "#0E1117",
    "text": "#FAFAFA",
}

CATEGORY_COLORS = px.colors.qualitative.Bold


def apply_copper_layout(fig, title=None, height=400):
    """Apply consistent COPPER theming to a Plotly figure."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COPPER_COLORS["text"])) if title else None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COPPER_COLORS["text"], size=12),
        height=height,
        margin=dict(l=40, r=20, t=50 if title else 20, b=40),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.1)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.1)", zeroline=False)
    return fig


def render_waterfall(df: pd.DataFrame, category: str = None, height=450):
    """
    Render a price waterfall chart - the centerpiece visualization.
    Shows: List Price → Contract Discount → GPO Fee → Rebates → Lowest Net
    """
    if category and category != "All":
        row = df[df["device_category"] == category].iloc[0]
        title = f"Price Waterfall: {category}"
    else:
        row = df.mean(numeric_only=True)
        title = "Price Waterfall: All Categories (Average)"

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total", "relative", "total"],
        x=["List Price", "Contract<br>Discount", "GPO<br>Admin Fee", "Rebates",
           "Lowest Net", "Unit Cost", "Margin"],
        y=[
            row["avg_list_price"],
            -row["avg_contract_discount"],
            -row["avg_gpo_fee"],
            -row["avg_rebate"],
            None,  # waterfall total
            -row["avg_cost"],
            None,  # waterfall total
        ],
        connector=dict(line=dict(color="rgba(255,255,255,0.2)", width=1)),
        increasing=dict(marker=dict(color=COPPER_COLORS["success"])),
        decreasing=dict(marker=dict(color=COPPER_COLORS["danger"])),
        totals=dict(marker=dict(color=COPPER_COLORS["primary"])),
        textposition="outside",
        text=[
            f"${row['avg_list_price']:,.0f}",
            f"-${row['avg_contract_discount']:,.0f}",
            f"-${row['avg_gpo_fee']:,.0f}",
            f"-${row['avg_rebate']:,.0f}",
            f"${row['avg_lowest_net']:,.0f}",
            f"-${row['avg_cost']:,.0f}",
            f"${row['avg_margin']:,.0f}",
        ],
    ))

    fig = apply_copper_layout(fig, title, height)
    fig.update_layout(showlegend=False)
    return fig


def render_margin_trend(df: pd.DataFrame, height=350):
    """Render margin % trend over time with alert bands."""
    monthly = df.groupby(["year", "month"]).agg(
        avg_margin=("avg_margin_pct", "mean"),
        revenue=("revenue", "sum")
    ).reset_index()
    monthly["date"] = pd.to_datetime(monthly[["year", "month"]].assign(day=1))
    monthly = monthly.sort_values("date")

    fig = go.Figure()

    # Alert bands
    fig.add_hrect(y0=0, y1=15, fillcolor="rgba(231,76,60,0.1)", line_width=0)
    fig.add_hrect(y0=15, y1=25, fillcolor="rgba(243,156,18,0.1)", line_width=0)
    fig.add_hrect(y0=25, y1=60, fillcolor="rgba(46,204,113,0.1)", line_width=0)

    fig.add_trace(go.Scatter(
        x=monthly["date"],
        y=monthly["avg_margin"],
        mode="lines+markers",
        line=dict(color=COPPER_COLORS["primary"], width=3),
        marker=dict(size=6),
        name="Avg Margin %",
        hovertemplate="Date: %{x|%b %Y}<br>Margin: %{y:.1f}%<extra></extra>",
    ))

    # Threshold lines
    fig.add_hline(y=15, line_dash="dash", line_color=COPPER_COLORS["danger"],
                  annotation_text="Min Target (15%)", annotation_position="bottom left")
    fig.add_hline(y=25, line_dash="dash", line_color=COPPER_COLORS["success"],
                  annotation_text="Target (25%)", annotation_position="top left")

    fig = apply_copper_layout(fig, "Margin Trend Over Time", height)
    fig.update_yaxes(title_text="Margin %")
    return fig


def render_revenue_by_category(df: pd.DataFrame, height=350):
    """Revenue breakdown by device category - horizontal bar."""
    cat_rev = df.groupby("device_category").agg(
        total_revenue=("total_revenue", "sum"),
        avg_margin=("avg_margin_pct", "mean"),
    ).reset_index().sort_values("total_revenue", ascending=True)

    fig = go.Figure(go.Bar(
        y=cat_rev["device_category"],
        x=cat_rev["total_revenue"],
        orientation="h",
        marker_color=CATEGORY_COLORS[:len(cat_rev)],
        text=[f"${v/1e6:.1f}M" for v in cat_rev["total_revenue"]],
        textposition="auto",
        hovertemplate="%{y}<br>Revenue: $%{x:,.0f}<extra></extra>",
    ))

    fig = apply_copper_layout(fig, "Revenue by Device Category", height)
    fig.update_xaxes(title_text="Revenue ($)")
    return fig


def render_deal_structure_pie(df: pd.DataFrame, height=350):
    """Deal structure distribution as a donut chart."""
    struct = df.groupby("deal_structure")["contract_count"].sum().reset_index()

    fig = go.Figure(go.Pie(
        labels=struct["deal_structure"],
        values=struct["contract_count"],
        hole=0.45,
        marker=dict(colors=CATEGORY_COLORS[:len(struct)]),
        textinfo="label+percent",
        hovertemplate="%{label}<br>Contracts: %{value}<br>Share: %{percent}<extra></extra>",
    ))

    fig = apply_copper_layout(fig, "Contract Mix by Deal Structure", height)
    return fig


def render_customer_treemap(df: pd.DataFrame, top_n=20, height=400):
    """Customer concentration treemap showing revenue by IDN."""
    top = df.nlargest(top_n, "total_revenue")

    fig = px.treemap(
        top,
        path=["gpo_name", "idn_name"],
        values="total_revenue",
        color="avg_margin_pct",
        color_continuous_scale=["#E74C3C", "#F39C12", "#2ECC71"],
        range_color=[10, 40],
        hover_data={"total_revenue": ":$,.0f", "avg_margin_pct": ":.1f"},
    )

    fig = apply_copper_layout(fig, f"Top {top_n} Customers by Revenue (color = margin %)", height)
    fig.update_coloraxes(colorbar_title="Margin %")
    return fig


def render_risk_gauge(critical, at_risk, watch, healthy, height=250):
    """Simple risk distribution horizontal stacked bar."""
    fig = go.Figure()

    categories = ["Critical", "At Risk", "Watch", "Healthy"]
    values = [critical, at_risk, watch, healthy]
    colors = [COPPER_COLORS["danger"], COPPER_COLORS["warning"],
              COPPER_COLORS["info"], COPPER_COLORS["success"]]

    for cat, val, color in zip(categories, values, colors):
        fig.add_trace(go.Bar(
            x=[val], y=["Contracts"],
            orientation="h",
            name=cat,
            marker_color=color,
            text=[f"{cat}: {val}"],
            textposition="inside",
        ))

    fig.update_layout(barmode="stack")
    fig = apply_copper_layout(fig, "Contract Risk Distribution", height)
    return fig


def render_region_map(df: pd.DataFrame, height=350):
    """Revenue by region as a bar chart."""
    region_data = df.groupby("region").agg(
        total_revenue=("total_revenue", "sum"),
        avg_margin=("avg_margin_pct", "mean"),
        contracts=("active_contracts", "sum"),
    ).reset_index().sort_values("total_revenue", ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=region_data["region"],
        y=region_data["total_revenue"],
        marker_color=COPPER_COLORS["primary"],
        text=[f"${v/1e6:.1f}M" for v in region_data["total_revenue"]],
        textposition="auto",
        name="Revenue",
    ))

    fig = apply_copper_layout(fig, "Revenue by Region", height)
    return fig
