---
name: vanna-training
description: Add training data to improve Vanna AI SQL generation accuracy
---

# Add Vanna Training Data

When improving the AI Assistant's accuracy:

## Where to Edit
Edit `pages/04_ai_assistant.py` inside the `setup_vanna()` function.

## Three Types of Training Data

### 1. Schema DDL (for new tables/views)
```python
vn.train(ddl="""CREATE TABLE table_name (
    col1 VARCHAR, col2 DOUBLE
) -- Description of what this table contains""")
```

### 2. Domain documentation (for terminology)
```python
vn.train(documentation="GPO admin fees are typically 1-3% of invoice price, paid by the vendor to the GPO.")
```

### 3. Question-SQL pairs (highest impact on accuracy)
```python
vn.train(
    question="What is the total revenue by device category?",
    sql="SELECT device_category, ROUND(SUM(invoice_price * quantity), 2) AS total_revenue FROM transactions GROUP BY device_category ORDER BY total_revenue DESC"
)
```

## Rules
- SQL must be valid DuckDB SQL. Test in DuckDB CLI first.
- Always use ROUND() for numeric outputs
- Always add ORDER BY for sorted results
- Use table aliases (t, i, g, p, c, r) for JOINs
- After adding training data, user must restart the Streamlit app to clear @st.cache_resource

## Available Tables
gpos, idns, facilities, products, contracts, rebate_programs, transactions

## Available Views
v_portfolio_summary, v_price_waterfall, v_customer_performance, v_monthly_trends, v_contract_risk
