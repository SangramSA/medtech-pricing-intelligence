"""
COPPER POC - Ensure DuckDB exists (for Streamlit Cloud or fresh local runs).
When DB is missing, runs the synthetic data generator once so the app can start.
"""

import os
import streamlit as st

from utils.data_loader import DB_PATH


@st.cache_resource
def ensure_data_ready():
    """Create data/copper.duckdb if missing by running the generator. Call once at app startup."""
    if os.path.exists(DB_PATH):
        return
    # Create data dirs and run generator (same DB_PATH as data_loader)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    from generators.generate_synthetic_data import main
    main()
