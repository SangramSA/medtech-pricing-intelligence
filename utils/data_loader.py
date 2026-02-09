"""
COPPER POC - Data loader utility.
Cached DuckDB query functions used by all Streamlit pages.
Tenant isolation: get_current_tenant_id() and build_tenant_where() scope all data to the selected tenant.
"""

import logging
import duckdb
import pandas as pd
import streamlit as st
import os

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "copper.duckdb")


def get_current_tenant_id() -> str:
    """Return the current tenant id from session state (set by app.py tenant selector)."""
    return st.session_state.get("tenant_id", "meddevice_corp")


def build_tenant_where(extra_where: str = "", tenant_id_override: str = None) -> str:
    """Build WHERE clause that includes tenant_id; optionally append extra conditions.
    tenant_id_override: if set, use this instead of session (so cache keys include tenant).
    """
    tid = (tenant_id_override or get_current_tenant_id()).replace("'", "''")
    tenant_part = f"tenant_id = '{tid}'"
    if extra_where:
        rest = extra_where.strip().replace("WHERE ", "", 1).strip()
        return " WHERE " + tenant_part + " AND " + rest
    return " WHERE " + tenant_part


def get_connection():
    """Get a DuckDB connection. Creates a new one per call (DuckDB is fast enough)."""
    return duckdb.connect(DB_PATH, read_only=True)


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    """Execute SQL and return a DataFrame. Cached for 5 minutes."""
    logger.debug("Executing query: %s", sql[:200])
    con = get_connection()
    try:
        result = con.execute(sql).fetchdf()
        logger.debug("Query returned %d rows", len(result))
        return result
    except Exception as e:
        logger.error("Query failed: %s | SQL: %s", e, sql[:300])
        raise
    finally:
        con.close()


@st.cache_data(ttl=300)
def query_params(sql: str, params: list) -> pd.DataFrame:
    """Execute parameterized SQL (use ? placeholders) and return a DataFrame. Cached per params."""
    logger.debug("Executing parameterized query: %s | params: %s", sql[:200], params)
    con = get_connection()
    try:
        result = con.execute(sql, params).fetchdf()
        logger.debug("Parameterized query returned %d rows", len(result))
        return result
    except Exception as e:
        logger.error("Parameterized query failed: %s | SQL: %s | params: %s", e, sql[:300], params)
        raise
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_kpi(sql: str):
    """Execute SQL that returns a single scalar value."""
    logger.debug("Executing KPI query: %s", sql[:200])
    con = get_connection()
    try:
        result = con.execute(sql).fetchone()
        value = result[0] if result else 0
        logger.debug("KPI result: %s", value)
        return value
    except Exception as e:
        logger.error("KPI query failed: %s | SQL: %s", e, sql[:300])
        raise
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_kpi_params(sql: str, params: list):
    """Execute parameterized SQL that returns a single scalar value. Used for tenant-scoped KPIs."""
    logger.debug("Executing parameterized KPI query: %s | params: %s", sql[:200], params)
    con = get_connection()
    try:
        result = con.execute(sql, params).fetchone()
        value = result[0] if result else 0
        logger.debug("Parameterized KPI result: %s", value)
        return value
    except Exception as e:
        logger.error("Parameterized KPI query failed: %s | SQL: %s | params: %s", e, sql[:300], params)
        raise
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_portfolio_summary(where_clause: str = "", _tenant_id: str = None):
    tid = _tenant_id or get_current_tenant_id()
    sql = "SELECT * FROM v_portfolio_summary" + build_tenant_where(where_clause, tid)
    return query(sql)


@st.cache_data(ttl=300)
def get_price_waterfall(where_clause: str = "", _tenant_id: str = None):
    tid = _tenant_id or get_current_tenant_id()
    sql = "SELECT * FROM v_price_waterfall" + build_tenant_where(where_clause, tid)
    return query(sql)


@st.cache_data(ttl=300)
def get_customer_performance(where_clause: str = "", _tenant_id: str = None):
    tid = _tenant_id or get_current_tenant_id()
    sql = "SELECT * FROM v_customer_performance" + build_tenant_where(where_clause, tid) + " ORDER BY total_revenue DESC"
    return query(sql)


@st.cache_data(ttl=300)
def get_monthly_trends(where_clause: str = "", _tenant_id: str = None):
    tid = _tenant_id or get_current_tenant_id()
    sql = "SELECT * FROM v_monthly_trends" + build_tenant_where(where_clause, tid) + " ORDER BY year, month"
    return query(sql)


@st.cache_data(ttl=300)
def get_contract_risk(where_clause: str = "", _tenant_id: str = None):
    tid = _tenant_id or get_current_tenant_id()
    sql = "SELECT * FROM v_contract_risk" + build_tenant_where(where_clause, tid) + " ORDER BY risk_status, total_revenue DESC"
    return query(sql)


@st.cache_data(ttl=300)
def get_device_categories(_tenant_id: str = None):
    tid = _tenant_id or get_current_tenant_id()
    sql = "SELECT DISTINCT device_category FROM transactions" + build_tenant_where("", tid) + " ORDER BY device_category"
    return query(sql)["device_category"].tolist()


@st.cache_data(ttl=300)
def get_regions(_tenant_id: str = None):
    tid = _tenant_id or get_current_tenant_id()
    sql = "SELECT DISTINCT region FROM transactions" + build_tenant_where("", tid) + " ORDER BY region"
    return query(sql)["region"].tolist()


@st.cache_data(ttl=300)
def get_gpo_names(_tenant_id: str = None):
    tid = _tenant_id or get_current_tenant_id()
    sql = """
        SELECT DISTINCT g.name
        FROM gpos g
        JOIN transactions t ON g.gpo_id = t.gpo_id
        """ + build_tenant_where("", tid) + """
        ORDER BY g.name
    """
    return query(sql)["name"].tolist()


@st.cache_data(ttl=300)
def get_idn_list(_tenant_id: str = None):
    tid = _tenant_id or get_current_tenant_id()
    sql = """
        SELECT DISTINCT i.idn_id, i.name, i.tier, i.region
        FROM idns i
        JOIN transactions t ON i.idn_id = t.idn_id
        """ + build_tenant_where("", tid) + """
        ORDER BY i.name
    """
    return query(sql)
