# COPPER Project Rules

## Commands
- `source .venv/bin/activate` — Always activate venv first
- `streamlit run app.py` — Launch the app (http://localhost:8501)
- `python generators/generate_synthetic_data.py` — Regenerate all data + DuckDB

## Code Patterns
- All data queries go through `utils/data_loader.py` with `@st.cache_data(ttl=300)`
- All charts go in `components/charts.py` and must call `apply_copper_layout()` for theming
- New pages: create in `pages/`, add to nav radio in `app.py`, add exec() route
- DuckDB connections must be read-only and closed in `finally` blocks
- Use COPPER_COLORS dict from `components/charts.py` for all color values

## Domain Terms (Use These Exactly)
- GPO = Group Purchasing Organization (Vizient, Premier, HealthTrust)
- IDN = Integrated Delivery Network (hospital system)
- ASC = Ambulatory Surgery Center
- PV/DV/TV/Access/All Play = deal structure types
- Lowest Net = invoice_price - gpo_admin_fee - rebate_amount (the true floor price)
- Price Waterfall = List → Invoice → Lowest Net → Margin decomposition
- AKS = Anti-Kickback Statute risk flag

## Database
- DuckDB file at `data/copper.duckdb` (read-only at runtime)
- 7 tables: gpos, idns, facilities, products, contracts, rebate_programs, transactions
- 5 views: v_portfolio_summary, v_price_waterfall, v_customer_performance, v_monthly_trends, v_contract_risk
- `transactions` is the fact table (30K rows) with full pricing waterfall columns

## Tech Stack
- Python 3.9, DuckDB 1.4.4, Streamlit 1.50, Plotly 6.5, Vanna AI 2.0 + Ollama (Mistral)

## Frontend Design Rules
- Dark theme: background #0E1117, text #FAFAFA, primary accent #B87333 (copper)
- NEVER use Streamlit's default bright/colorful charts — always use COPPER_COLORS
- All Plotly charts must use transparent backgrounds: paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
- Use white grid lines at 10% opacity: gridcolor="rgba(255,255,255,0.1)"
- KPI cards always appear in a single row at the top of each page using render_kpi_row()
- Use st.columns() for side-by-side layouts — never stack charts vertically when two can sit next to each other
- Separate major sections with st.markdown("---")
- Every page starts with st.title() + st.caption() describing the module
- Tables use st.dataframe() with use_container_width=True and hide_index=True
- Keep chart heights consistent within a row (both 350px or both 400px)
- Use st.expander() for secondary detail, never for primary content
- Avoid st.tabs() — use vertical scroll with section headers instead (stakeholders miss tabbed content)
- Color semantics: green (#2ECC71) = good/healthy, red (#E74C3C) = bad/critical, yellow (#F39C12) = warning, blue (#3498DB) = informational
- Format currency with $ and abbreviations: $1.2M, $450K, never raw numbers like 1234567.89
- Format percentages with 1 decimal: 23.4%, never 23.432%
