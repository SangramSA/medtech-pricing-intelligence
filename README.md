# 🏥 COPPER POC

**Comprehensive Pricing & Performance Excellence Resource**

A MedTech pricing intelligence proof-of-concept built with DuckDB, Streamlit, and Vanna AI.

## Quick Start

```bash
# 1. Clone and enter the project
cd copper-poc

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate synthetic data
python generators/generate_synthetic_data.py

# 5. Set OpenAI key (for AI Assistant page)
export OPENAI_API_KEY="sk-..."  # Windows: set OPENAI_API_KEY=sk-...

# 6. Launch the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## What's Inside

| Page | Module | Description |
|------|--------|-------------|
| 🏠 Home | — | Platform overview and module descriptions |
| 📊 Portfolio | Drive | Price waterfall, margin trends, customer concentration, risk dashboard |
| 🔍 Customer Intel | Discover | IDN drill-down: contracts, pricing analysis, rebate programs |
| 🤖 AI Assistant | — | Natural language querying via Vanna AI + DuckDB |
| ⚙️ Architecture | — | Data pipeline diagram, tech stack, data model |

## Tech Stack

- **DuckDB** — Columnar analytics engine (zero-config, reads Parquet natively)
- **Streamlit** — Interactive dashboard framework (pure Python)
- **Vanna AI** — RAG-based text-to-SQL with auto-visualization
- **Plotly** — Waterfall charts, treemaps, gauges
- **Faker + NumPy** — Synthetic MedTech pricing data generation

## Data Model

```
GPOs (5) → IDNs (60) → Facilities (~800)
                ↓
         Contracts (150) → Rebate Programs (~300)
                ↓
         Transactions (30,000) ← Products (24)
```

Each transaction includes the full pricing waterfall:
**List Price → Contract Discount → GPO Admin Fee → Rebates → Lowest Net → Cost → Margin**

## AI Assistant

The AI Assistant uses Vanna AI trained on:
- Schema DDL for all 7 tables
- MedTech pricing domain documentation
- 10 example question-SQL pairs

Example questions:
- "What is the total revenue by device category?"
- "Which customers have the lowest margins?"
- "Show the price waterfall for orthopedic implants"
- "How many contracts are at risk?"
- "Which GPO gives us the best margins?"

**Note:** Requires `OPENAI_API_KEY` environment variable. The AI Assistant page
works without it — it just shows the example questions instead of the live chat.

## Project Structure

```
copper-poc/
├── app.py                          # Streamlit entrypoint + page router
├── .streamlit/config.toml          # Copper-branded dark theme
├── pages/
│   ├── 02_portfolio.py             # Drive module dashboard
│   ├── 03_customer_intel.py        # Discover module drill-down
│   ├── 04_ai_assistant.py          # Vanna AI chat interface
│   └── 05_architecture.py          # Architecture visualization
├── data/
│   ├── raw/                        # Generated CSVs (source system simulation)
│   ├── transformed/                # (Reserved for dbt models)
│   └── copper.duckdb               # Analytical database
├── generators/
│   └── generate_synthetic_data.py  # Faker + NumPy data generators
├── components/
│   ├── charts.py                   # Reusable Plotly chart functions
│   ├── kpi_cards.py                # Metric card wrappers
│   └── filters.py                  # Sidebar filter components
├── config/
│   ├── tenants.yaml                # Multi-tenant configuration
│   └── metrics.yaml                # KPI definitions
├── utils/
│   └── data_loader.py              # Cached DuckDB query functions
├── requirements.txt
└── README.md
```
