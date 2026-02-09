---
name: new-chart
description: Add a new Plotly chart to COPPER's chart library with consistent theming and design
---

# Create a New Chart

When adding a chart to COPPER:

## File and Function Pattern
1. Add function to `components/charts.py`
2. Function signature: `def render_chartname(df: pd.DataFrame, height=350):`
3. Call `apply_copper_layout(fig, "Title", height)` before returning
4. Return the Plotly figure object
5. Call from page with `st.plotly_chart(render_chartname(data), use_container_width=True)`

## Theming (Non-Negotiable)
- Transparent backgrounds: `paper_bgcolor="rgba(0,0,0,0)"`, `plot_bgcolor="rgba(0,0,0,0)"`
- White text: `font=dict(color="#FAFAFA", size=12)`
- Subtle gridlines: `gridcolor="rgba(255,255,255,0.1)"`, `zeroline=False`
- All of this is handled by `apply_copper_layout()` — always call it

## Color Usage
- Single data series → COPPER_COLORS["primary"] (#B87333)
- Multiple categories → px.colors.qualitative.Warm (the warm palette, not default)
- Status encoding: green = good (#2ECC71), red = bad (#E74C3C), yellow = warning (#F39C12), blue = info (#3498DB)
- NEVER use Plotly default blue/red palette — it clashes with the dark theme
- For continuous color scales: use ["#E74C3C", "#F39C12", "#2ECC71"] (red → yellow → green)

## Chart Type Selection Guide
- Revenue/margin comparison across categories → **horizontal bar** (more readable than vertical)
- Composition/share breakdown → **donut chart** (go.Pie with hole=0.4-0.5)
- Time series trends → **line chart** with markers (go.Scatter, mode="lines+markers")
- Hierarchical data (GPO → IDN) → **treemap** (px.treemap)
- Pricing decomposition → **waterfall** (go.Waterfall)
- Risk/status distribution → **stacked horizontal bar**
- Single KPI with context → use st.metric(), not a chart

## Interactivity Requirements
- Set `hovertemplate` on every trace — demos rely on hover for detail
- Format hover values: `Revenue: $%{x:,.0f}` not raw numbers
- End hovertemplates with `<extra></extra>` to suppress trace name box
- For bar charts: add `text` parameter with formatted labels, `textposition="auto"`

## Sizing Rules
- Hero/centerpiece charts: height=450
- Side-by-side charts (in st.columns): height=350
- Small supporting charts: height=250-300
- Both charts in a row MUST have the same height
- Always use `use_container_width=True` when rendering

## Common Patterns

### Bar chart with value labels
```python
fig = go.Figure(go.Bar(
    x=df["value"], y=df["category"],
    orientation="h",
    marker_color=COPPER_COLORS["primary"],
    text=[f"${v/1e6:.1f}M" for v in df["value"]],
    textposition="auto",
    hovertemplate="%{y}<br>Value: $%{x:,.0f}<extra></extra>",
))
```

### Line chart with alert bands
```python
fig.add_hrect(y0=0, y1=threshold, fillcolor="rgba(231,76,60,0.1)", line_width=0)
fig.add_hline(y=target, line_dash="dash", line_color=COPPER_COLORS["success"])
```

### Donut chart
```python
fig = go.Figure(go.Pie(
    labels=df["label"], values=df["value"],
    hole=0.45,
    marker=dict(colors=px.colors.qualitative.Warm[:len(df)]),
    textinfo="label+percent",
))
```

## Reference Examples
- `render_waterfall()` — the centerpiece waterfall chart
- `render_margin_trend()` — line chart with alert bands and thresholds
- `render_customer_treemap()` — treemap with continuous color scale
- `render_risk_gauge()` — horizontal stacked bar for status distribution
