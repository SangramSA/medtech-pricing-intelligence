"""
COPPER POC - Data loader utility.
Cached DuckDB query functions used by all Streamlit pages.
"""

import duckdb
import pandas as pd
import streamlit as st
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "copper.duckdb")


def get_connection():
    """Get a DuckDB connection. Creates a new one per call (DuckDB is fast enough)."""
    return duckdb.connect(DB_PATH, read_only=True)


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    """Execute SQL and return a DataFrame. Cached for 5 minutes."""
    con = get_connection()
    try:
        result = con.execute(sql).fetchdf()
        return result
    finally:
        con.close()


@st.cache_data(ttl=300)
def query_params(sql: str, params: list) -> pd.DataFrame:
    """Execute parameterized SQL (use ? placeholders) and return a DataFrame. Cached per params."""
    con = get_connection()
    try:
        result = con.execute(sql, params).fetchdf()
        return result
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_kpi(sql: str):
    """Execute SQL that returns a single scalar value."""
    con = get_connection()
    try:
        result = con.execute(sql).fetchone()
        return result[0] if result else 0
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_portfolio_summary(where_clause: str = ""):
    sql = "SELECT * FROM v_portfolio_summary"
    if where_clause:
        sql += " " + where_clause
    return query(sql)


@st.cache_data(ttl=300)
def get_price_waterfall(where_clause: str = ""):
    sql = "SELECT * FROM v_price_waterfall"
    if where_clause:
        sql += " " + where_clause
    return query(sql)


@st.cache_data(ttl=300)
def get_customer_performance(where_clause: str = ""):
    sql = "SELECT * FROM v_customer_performance"
    if where_clause:
        sql += " " + where_clause
    sql += " ORDER BY total_revenue DESC"
    return query(sql)


@st.cache_data(ttl=300)
def get_monthly_trends(where_clause: str = ""):
    sql = "SELECT * FROM v_monthly_trends"
    if where_clause:
        sql += " " + where_clause
    sql += " ORDER BY year, month"
    return query(sql)


@st.cache_data(ttl=300)
def get_contract_risk(where_clause: str = ""):
    sql = "SELECT * FROM v_contract_risk"
    if where_clause:
        sql += " " + where_clause
    sql += " ORDER BY risk_status, total_revenue DESC"
    return query(sql)


@st.cache_data(ttl=300)
def get_device_categories():
    return query("SELECT DISTINCT device_category FROM transactions ORDER BY device_category")["device_category"].tolist()


@st.cache_data(ttl=300)
def get_regions():
    return query("SELECT DISTINCT region FROM transactions ORDER BY region")["region"].tolist()


@st.cache_data(ttl=300)
def get_gpo_names():
    return query("SELECT DISTINCT name FROM gpos ORDER BY name")["name"].tolist()


@st.cache_data(ttl=300)
def get_idn_list():
    return query("""
        SELECT idn_id, name, tier, region
        FROM idns
        ORDER BY name
    """)
