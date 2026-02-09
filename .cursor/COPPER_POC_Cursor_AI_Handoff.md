# COPPER POC — Complete Codebase Summary for Cursor AI

> **Purpose of this document:** Give Cursor AI (or any coding assistant) the complete context needed to continue building, debugging, and enhancing this project. It covers domain knowledge, architecture decisions, every file in the codebase with explanations, known issues, and a prioritized list of what to build next.

---

## 1. What Is This Project?

**COPPER** (Comprehensive Pricing & Performance Excellence Resource) is a proof-of-concept for a MedTech pricing intelligence platform. It's being built for **Intellicent Analytics**, a startup creating a multi-tenant SaaS product for medical device manufacturers.

The POC demonstrates that a solo data engineer can build a working pricing intelligence dashboard with AI-powered natural language querying over a weekend, using lightweight tools (DuckDB, Streamlit, Vanna AI).

**The audience is dual-purpose:**
1. **Intellicent stakeholders** — non-technical product/business people who need to see that the data architecture approach works and delivers real value
2. **The builder (Sangram)** — validating the data architecture approach before committing to a production stack

---

## 2. MedTech Pricing Domain — Essential Knowledge

This domain knowledge is critical for writing correct code. Every SQL query, data model decision, and UI label must use these terms correctly.

### Key Players (Customer Hierarchy)

```
GPO (Group Purchasing Organization)
 └── IDN (Integrated Delivery Network / Hospital System)
      └── Facility (Hospital, ASC, Clinic)
```

- **GPO**: Vizient, Premier, HealthTrust, Intalere, HPG. They negotiate contracts on behalf of member hospitals and charge 1-3% admin fees to the vendor.
- **IDN**: Hospital systems like HCA, CommonSpirit. They have multiple facilities. Our data model has ~60 IDNs with 2-180 facilities each (log-normal distribution — a few giants, many small).
- **ASC**: Ambulatory Surgery Centers. Outpatient, price-sensitive, simpler deals.
- **Vendor**: The medical device manufacturer — this is Intellicent's customer. COPPER serves vendors, not hospitals.

### Pricing Waterfall (Most Important Concept)

This is the single most critical visualization in the app. Every pricing director knows this chart.

```
List Price              $10,000   (manufacturer's suggested price)
  - Contract Discount    -$2,000   (negotiated based on deal structure)
  = Invoice Price         $8,000   (what appears on the invoice)
  - GPO Admin Fee          -$200   (1-3% paid to GPO)
  - Rebates                -$300   (post-sale performance payments)
  = Lowest Net Price      $7,500   (true floor price — "pocket price")
  - Unit Cost             -$3,500   (manufacturer's cost)
  = Margin                 $4,000   (what the vendor keeps)
```

**In the database:** `lowest_net_price = invoice_price - gpo_admin_fee - rebate_amount` and `margin = lowest_net_price - unit_cost`.

### Deal Structures

| Structure | Market Share | Discount Level | Description |
|-----------|-------------|----------------|-------------|
| **PV** (Primary Vendor) | 80%+ | Highest (20-28%) | Single supplier dominates |
| **DV** (Dual Vendor) | 40-60% | Medium (15-23%) | Two suppliers split share |
| **TV** (TriVendor) | ~30% | Lower (12-20%) | Three suppliers compete |
| **Access** | No commitment | Low (5-13%) | Base pricing, no volume promise |
| **All Play** | Open | Lowest (3-10%) | Open competition |

### Rebate Types

| Type | Trigger | Range | Orientation |
|------|---------|-------|-------------|
| **Volume** | Units/dollars exceed threshold | 2-5% | Can be offensive or defensive |
| **Loyalty** | Market share stays above threshold | 1-3% | Usually defensive |
| **Bundle** | Purchasing across product categories | 1-2% | Usually offensive |
| **Growth** | Year-over-year volume increase | 0.5-1.5% | Always offensive |

- **Offensive rebate**: Rewards growth above baseline
- **Defensive rebate**: Rewards maintaining current performance

### Compliance (Must Not Ignore)

- **Safe Harbor**: Rebate terms must be pre-established in the contract. Can't adjust criteria after the fact.
- **Anti-Kickback Statute (AKS)**: Prohibits payments to influence purchasing outside contracted terms. Our data has `aks_risk_flag` (Low/Medium/High).
- **Price Erosion**: Aggressive discounting creates new floor prices that cascade.

### COPPER Platform Modules

| Module | Purpose | POC Status |
|--------|---------|------------|
| **Discover** | Pre-deal intelligence: customer health, deal history, competitive landscape | ✅ Implemented (Customer Intel page) |
| **Build** | Deal construction: pricing recommendations, guardrails, compliance checks | ❌ Not built |
| **Monitor** | Active deal tracking: performance vs targets, at-risk alerts, next-best-actions | ❌ Not built |
| **Drive** | Portfolio dashboards: margin trends, revenue analysis, customer concentration | ✅ Implemented (Portfolio page) |
| **Optimize** | Opportunity identification: margin recovery, bundling, renegotiation candidates | ❌ Not built |

---

## 3. Tech Stack

| Layer | Tool | Version | Purpose |
|-------|------|---------|---------| 
| **Database** | DuckDB | 1.4.4 | Columnar analytics, zero-config |
| **Frontend** | Streamlit | 1.50.0 | Multi-page Python dashboard app |
| **Charts** | Plotly | 6.5.2 | Interactive visualizations |
| **AI/NLQ** | Vanna AI | 2.0.2 | RAG-based text-to-SQL with Ollama backend |
| **LLM** | Ollama + Mistral | local | Local LLM for text-to-SQL |
| **Vector Store** | ChromaDB | 1.4.1 | Stores Vanna's training embeddings |
| **Data Gen** | Faker + NumPy | — | Synthetic MedTech pricing data |

---

## 4. Project Structure

```
copper-poc/
├── app.py                              # Main entrypoint + page router
├── .streamlit/config.toml              # Copper-branded dark theme
├── requirements.txt                    # Python dependencies
├── data/
│   ├── raw/                            # Generated CSVs (simulates source systems)
│   └── copper.duckdb                   # Analytical database with tables + views
├── generators/
│   └── generate_synthetic_data.py      # Data generator (run once)
├── components/
│   ├── charts.py                       # All Plotly chart functions
│   ├── kpi_cards.py                    # KPI metric card wrappers
│   └── filters.py                      # Sidebar filter components
├── config/
│   ├── tenants.yaml                    # Multi-tenant config (not yet wired)
│   └── metrics.yaml                    # KPI definitions (not yet wired)
├── utils/
│   └── data_loader.py                  # Cached DuckDB query functions
└── pages/
    ├── 02_portfolio.py                 # Drive module — portfolio dashboards
    ├── 03_customer_intel.py            # Discover module — customer drill-down
    ├── 04_ai_assistant.py              # Vanna AI chat interface
    └── 05_architecture.py              # Architecture diagrams
```

---

## 5. File-by-File Code Explanation

### `app.py` — Main Entrypoint
Configures Streamlit page, renders sidebar (branding, tenant selector, navigation), routes to pages using `exec(open(...).read())`. Tenant selector is UI-only — switching tenants doesn't filter data yet.

### `generators/generate_synthetic_data.py` — Data Generator
Run first: `python generators/generate_synthetic_data.py`. Generates 7 tables (gpos, idns, facilities, products, contracts, rebate_programs, transactions), saves CSVs to `data/raw/`, loads into DuckDB, creates 5 analytical views.

### `utils/data_loader.py` — Data Access Layer
Cached DuckDB query functions with `@st.cache_data(ttl=300)`. Each function opens read-only connection and closes in `finally` block. Add new query functions here.

### `components/charts.py` — Plotly Chart Library
All charts use `COPPER_COLORS` dict and `apply_copper_layout()`. Key charts: render_waterfall (centerpiece), render_margin_trend (with alert bands), render_customer_treemap, render_risk_gauge, render_revenue_by_category, render_deal_structure_pie, render_region_map.

### `components/kpi_cards.py` — Metric Cards
Wraps `st.metric()`. `render_kpi_row()` creates equal-width columns. Helpers: `format_currency()`, `format_number()`.

### `components/filters.py` — Sidebar Filters
4 selectboxes (Category, Region, GPO, Deal Structure). `build_where_clause()` converts to SQL WHERE. Known issue: GPO filter not wired.

### `pages/02_portfolio.py` — Drive Module
Layout: KPI row → Price Waterfall → Margin Trend + Revenue by Category → Deal Structure + Region → Customer Treemap → Risk Dashboard. Known issue: filters only apply to KPI cards, not charts.

### `pages/03_customer_intel.py` — Discover Module
IDN selector → Customer KPIs → Contract portfolio table → Deal structure/risk charts → Pricing analysis → Recent transactions → Rebate programs. Uses f-string SQL (fine for POC).

### `pages/04_ai_assistant.py` — Vanna AI Chat
Uses Ollama (Mistral) + ChromaDB. Trained on 6 DDL statements, 6 documentation strings, 10 Q&A pairs. Graceful degradation if Ollama isn't running. No auto-visualization (security concern CVE-2024-5565).

### `pages/05_architecture.py` — Architecture Visualization
Graphviz pipeline + ER diagrams, tech stack tables, multi-tenancy options, AI integration points.

### `config/tenants.yaml` and `config/metrics.yaml`
Not yet wired. TODO: config loader to drive KPIs and tenant branding.

---

## 6. Database Schema Reference

```sql
CREATE TABLE gpos (gpo_id VARCHAR PK, name, admin_fee_pct DOUBLE, member_count INT);
CREATE TABLE idns (idn_id VARCHAR PK, name, gpo_id FK, facility_count, annual_spend, region, state, tier);
CREATE TABLE facilities (facility_id VARCHAR PK, idn_id FK, name, facility_type, bed_count, state, region);
CREATE TABLE products (product_id VARCHAR PK, name, category, list_price DOUBLE, cost DOUBLE, sku);
CREATE TABLE contracts (contract_id VARCHAR PK, idn_id FK, gpo_id FK, deal_structure, device_category, start_date, end_date, duration_months, base_discount_pct, market_share_commitment, status, annual_volume_target, safe_harbor_compliant BOOL, aks_risk_flag);
CREATE TABLE rebate_programs (rebate_id VARCHAR PK, contract_id FK, rebate_type, rebate_pct DOUBLE, trigger_type, trigger_threshold, orientation, earned BOOL);
CREATE TABLE transactions (transaction_id VARCHAR PK, contract_id FK, idn_id FK, gpo_id FK, product_id FK, transaction_date, quantity, list_price, invoice_price, gpo_admin_fee, rebate_amount, lowest_net_price, unit_cost, margin, margin_pct, total_discount_pct, deal_structure, device_category, region, idn_tier, quarter, year, month);
```

Views: v_portfolio_summary, v_price_waterfall, v_customer_performance, v_monthly_trends, v_contract_risk.

---

## 7. Known Issues and TODOs

### Bugs
1. GPO filter not wired in `build_where_clause()`
2. Filters only apply to KPI cards, not charts
3. Tenant selector is cosmetic — no data isolation
4. SQL injection via f-strings in Customer Intel
5. `list[dict]` type hint requires Python 3.9+

### Features to Build (Prioritized)
**High:** Wire config files, make filters work on all charts, add tenant isolation, test Ollama AI Assistant
**Medium:** Build Monitor module, Build Optimize module, add auto-viz to AI, add data export, add date range filter
**Lower:** Build Build module, native multi-page routing, dbt models, authentication, deploy to Streamlit Cloud

---

## 8. How to Run

```bash
cd /Users/sangram/Personal_Projects/copper-poc
source .venv/bin/activate
python generators/generate_synthetic_data.py  # if needed
streamlit run app.py
# For AI: install Ollama, ollama pull mistral, restart app
```

---

## 9. Key Code Patterns

**New chart:** Add to `components/charts.py`, call `apply_copper_layout()`, use `COPPER_COLORS`.
**New query:** Add to `utils/data_loader.py` with `@st.cache_data(ttl=300)`.
**New page:** Create `pages/0X_name.py`, add to nav radio + exec() in `app.py`.
**Vanna training:** In `setup_vanna()`: `vn.train(ddl=...)`, `vn.train(documentation=...)`, `vn.train(question=..., sql=...)`.
