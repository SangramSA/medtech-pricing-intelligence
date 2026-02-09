"""
COPPER POC - Sidebar filter components.
"""

import streamlit as st
from utils.data_loader import get_device_categories, get_regions, get_gpo_names, get_current_tenant_id


def render_filters():
    """Render sidebar filters and return selected values (tenant-scoped)."""
    st.sidebar.markdown("### 🔍 Filters")
    tid = get_current_tenant_id()

    categories = ["All"] + get_device_categories(_tenant_id=tid)
    selected_category = st.sidebar.selectbox("Device Category", categories)

    regions = ["All"] + get_regions(_tenant_id=tid)
    selected_region = st.sidebar.selectbox("Region", regions)

    gpos = ["All"] + get_gpo_names(_tenant_id=tid)
    selected_gpo = st.sidebar.selectbox("GPO", gpos)

    structures = ["All", "PV", "DV", "TV", "Access", "All Play"]
    selected_structure = st.sidebar.selectbox("Deal Structure", structures)

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "⏱️ **Data Freshness**<br>"
        "<span style='color: #2ECC71;'>● Live</span> — Refreshed 2 min ago",
        unsafe_allow_html=True,
    )

    return {
        "category": selected_category,
        "region": selected_region,
        "gpo": selected_gpo,
        "structure": selected_structure,
    }


def build_where_clause(
    filters: dict,
    table_alias: str = "",
    use_gpo_name: bool = False,
    include_keys: list = None,
) -> str:
    """Build a SQL WHERE clause from filter selections.
    use_gpo_name: if True, use gpo_name = 'X' (for views like v_customer_performance);
    if False, use gpo_id IN (SELECT gpo_id FROM gpos WHERE name = 'X') for transactions.
    include_keys: if set, only include these filter dimensions ('category', 'region', 'structure', 'gpo').
    """
    prefix = f"{table_alias}." if table_alias else ""
    allowed = set(include_keys) if include_keys is not None else {"category", "region", "structure", "gpo"}
    clauses = []

    if "category" in allowed and filters["category"] != "All":
        clauses.append(f"{prefix}device_category = '{filters['category']}'")
    if "region" in allowed and filters["region"] != "All":
        clauses.append(f"{prefix}region = '{filters['region']}'")
    if "structure" in allowed and filters["structure"] != "All":
        clauses.append(f"{prefix}deal_structure = '{filters['structure']}'")
    if "gpo" in allowed and filters["gpo"] != "All":
        gpo_val = filters["gpo"].replace("'", "''")  # escape single quotes
        if use_gpo_name:
            clauses.append(f"{prefix}gpo_name = '{gpo_val}'")
        else:
            clauses.append(f"{prefix}gpo_id IN (SELECT gpo_id FROM gpos WHERE name = '{gpo_val}')")

    if clauses:
        return " WHERE " + " AND ".join(clauses)
    return ""
