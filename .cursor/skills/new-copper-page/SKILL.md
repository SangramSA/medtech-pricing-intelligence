---
name: new-copper-page
description: Create a new COPPER dashboard page with consistent layout, design, and data patterns
---

# Create a New COPPER Page

When the user asks to create a new page/module for COPPER:

## File Setup
1. Create `pages/0X_pagename.py` following the pattern in `pages/02_portfolio.py`
2. Add data query functions to `utils/data_loader.py` with @st.cache_data(ttl=300)
3. Add any new chart functions to `components/charts.py` using apply_copper_layout()
4. Add the page to the navigation radio in `app.py`
5. Add the exec() routing in app.py

## Required Page Structure (Top to Bottom)
Every page MUST follow this layout order:

```
1. st.title("📊 Page Title")          ← emoji + title
2. st.caption("Module Name — ...")     ← one-line description
3. render_kpi_row([...])               ← 3-5 KPI metric cards in a single row
4. st.markdown("---")                  ← horizontal divider
5. Primary visualization               ← the "hero" chart (full width, 450px height)
6. st.markdown("---")
7. Two-column layout                   ← st.columns([3, 2]) or st.columns(2) with supporting charts
8. st.markdown("---")
9. Detail section                      ← data tables, drill-downs, expandable detail
```

## Design Principles
- **Information hierarchy**: Most important insight at the top (KPIs), supporting detail below, raw data last
- **Consistent heights within rows**: If two charts are side by side, both must be the same height
- **No orphaned charts**: Every chart needs a st.subheader() label above it
- **White space matters**: Always use st.markdown("---") between major sections. Never stack 3+ charts without a divider.
- **Column ratios**: Use [3, 2] when one chart is more important. Use [1, 1] for equal weight. Never use 3+ columns for charts (too narrow).
- **Tables last**: Data tables should be at the bottom or inside st.expander(). Don't put tables between charts.
- **Rename columns for display**: Always use .rename(columns={...}) to convert snake_case to human-readable labels
- **Format numbers in tables**: Currency as $X,XXX.XX, percentages as XX.X%

## Color and Theme
- Import COPPER_COLORS from components/charts
- Primary accent: #B87333 (copper) — use for main data series, active elements
- Success/healthy: #2ECC71 (green)
- Warning/watch: #F39C12 (yellow)  
- Danger/critical: #E74C3C (red)
- Informational: #3498DB (blue)
- NEVER use Plotly default colors. Always pass explicit colors from COPPER_COLORS or px.colors.qualitative.Warm
- All chart backgrounds must be transparent (rgba(0,0,0,0))

## KPI Card Guidelines
- Use render_kpi_row() from components/kpi_cards
- Format values: currency → format_currency(), counts → format_number()
- Add delta text for context: "+12.3% vs prior year", "Below target", "3 need attention"
- delta_color: "normal" (green up), "inverse" (red up is bad), "off" (neutral)
- Limit to 4-5 cards per row. More than 5 gets cramped.

## Chart Guidelines
- Every chart function returns a Plotly figure
- Call apply_copper_layout(fig, "Title Text", height) before returning
- Set hovertemplate for every trace — users hover constantly in demos
- Use textposition="auto" or "outside" to show values on bars
- For bar charts: horizontal bars with text labels are more readable than vertical
- For trend lines: add threshold/target lines with fig.add_hline() for context

## Import Pattern
```python
import streamlit as st
from utils.data_loader import query, get_kpi
from components.charts import COPPER_COLORS, apply_copper_layout
from components.kpi_cards import render_kpi_row, format_currency, format_number
```
