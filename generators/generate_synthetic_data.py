"""
COPPER POC - Synthetic MedTech Pricing Data Generator
Generates realistic medical device pricing data including:
- GPOs, IDNs, Facilities (customer hierarchy)
- Products by device category
- Contracts with deal structures (PV/DV/TV/Access)
- Transactions with full pricing waterfall
- Rebate programs and accruals
"""

import duckdb
import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import os

fake = Faker()
Faker.seed(42)
np.random.seed(42)

# ─── Configuration ───────────────────────────────────────────────────────────

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
RAW_DIR = os.path.join(OUTPUT_DIR, "raw")
TRANSFORMED_DIR = os.path.join(OUTPUT_DIR, "transformed")
DB_PATH = os.path.join(OUTPUT_DIR, "copper.duckdb")

TENANT_IDS = ["meddevice_corp", "orthotech_inc"]  # Multi-tenant for isolation demo

# Real GPO names (public knowledge)
GPOS = [
    {"gpo_id": "GPO-001", "name": "Vizient", "admin_fee_pct": 0.03, "member_count": 4800},
    {"gpo_id": "GPO-002", "name": "Premier", "admin_fee_pct": 0.025, "member_count": 4100},
    {"gpo_id": "GPO-003", "name": "HealthTrust", "admin_fee_pct": 0.02, "member_count": 1800},
    {"gpo_id": "GPO-004", "name": "Intalere", "admin_fee_pct": 0.015, "member_count": 1200},
    {"gpo_id": "GPO-005", "name": "HPG", "admin_fee_pct": 0.02, "member_count": 800},
]

DEVICE_CATEGORIES = {
    "Orthopedic Implants": {"price_range": (500, 15000), "products": [
        "Total Knee System", "Total Hip System", "Spinal Fusion Rod",
        "Shoulder Arthroplasty Kit", "Trauma Plate Set", "ACL Reconstruction Kit",
    ]},
    "Cardiovascular": {"price_range": (1000, 30000), "products": [
        "Drug-Eluting Stent", "Pacemaker Dual Chamber", "Heart Valve Prosthesis",
        "Ablation Catheter", "Guidewire Set", "Angioplasty Balloon",
    ]},
    "Surgical Instruments": {"price_range": (50, 2000), "products": [
        "Laparoscopic Stapler", "Electrosurgical Generator", "Suture Kit Premium",
        "Trocar Set", "Clip Applier", "Vessel Sealing Device",
    ]},
    "Consumables": {"price_range": (5, 200), "products": [
        "Surgical Drape Pack", "Wound Closure Strip", "Hemostatic Agent",
        "Irrigation Solution", "Skin Prep Kit", "Adhesive Bandage Box",
    ]},
}

DEAL_STRUCTURES = ["PV", "DV", "TV", "Access", "All Play"]
DEAL_STRUCTURE_WEIGHTS = [0.25, 0.30, 0.15, 0.20, 0.10]

REGIONS = ["Northeast", "Southeast", "Midwest", "West", "Southwest"]
STATES_BY_REGION = {
    "Northeast": ["NY", "NJ", "PA", "CT", "MA"],
    "Southeast": ["FL", "GA", "NC", "VA", "TN"],
    "Midwest": ["IL", "OH", "MI", "IN", "WI"],
    "West": ["CA", "WA", "OR", "CO", "AZ"],
    "Southwest": ["TX", "OK", "NM", "LA", "AR"],
}


def generate_idns(n=60):
    """Generate Integrated Delivery Networks with realistic size distribution."""
    idns = []
    # Log-normal distribution: few large systems, many small ones
    sizes = np.random.lognormal(mean=2.5, sigma=0.8, size=n).astype(int)
    sizes = np.clip(sizes, 2, 180)

    idn_names = set()
    for i in range(n):
        # Generate unique health system name
        while True:
            name_style = np.random.choice(["city", "saint", "regional", "memorial"])
            if name_style == "city":
                name = f"{fake.city()} Health System"
            elif name_style == "saint":
                name = f"St. {fake.first_name()} Medical Center"
            elif name_style == "regional":
                name = f"{fake.last_name()} Regional Health"
            else:
                name = f"{fake.city()} Memorial Healthcare"
            if name not in idn_names:
                idn_names.add(name)
                break

        region = np.random.choice(REGIONS)
        gpo = np.random.choice(GPOS, p=[0.35, 0.30, 0.15, 0.12, 0.08])

        idns.append({
            "idn_id": f"IDN-{i+1:03d}",
            "name": name,
            "gpo_id": gpo["gpo_id"],
            "facility_count": int(sizes[i]),
            "annual_spend": int(sizes[i] * np.random.uniform(2_000_000, 8_000_000)),
            "region": region,
            "state": np.random.choice(STATES_BY_REGION[region]),
            "tier": "Large" if sizes[i] > 30 else ("Medium" if sizes[i] > 10 else "Small"),
        })
    return pd.DataFrame(idns)


def generate_facilities(idns_df):
    """Generate individual facilities under each IDN."""
    facilities = []
    fac_id = 1
    for _, idn in idns_df.iterrows():
        n_facilities = idn["facility_count"]
        for j in range(n_facilities):
            fac_type = np.random.choice(
                ["Hospital", "ASC", "Clinic"],
                p=[0.5, 0.3, 0.2]
            )
            facilities.append({
                "facility_id": f"FAC-{fac_id:05d}",
                "idn_id": idn["idn_id"],
                "name": f"{idn['name']} - {fake.city()} {fac_type}",
                "facility_type": fac_type,
                "bed_count": np.random.randint(50, 800) if fac_type == "Hospital" else (
                    np.random.randint(4, 20) if fac_type == "ASC" else 0
                ),
                "state": idn["state"],
                "region": idn["region"],
            })
            fac_id += 1
    return pd.DataFrame(facilities)


def generate_products():
    """Generate product catalog with pricing tiers."""
    products = []
    prod_id = 1
    for category, config in DEVICE_CATEGORIES.items():
        low, high = config["price_range"]
        for product_name in config["products"]:
            list_price = round(np.random.uniform(low, high), 2)
            products.append({
                "product_id": f"PROD-{prod_id:03d}",
                "name": product_name,
                "category": category,
                "list_price": list_price,
                "cost": round(list_price * np.random.uniform(0.25, 0.45), 2),
                "sku": f"SKU-{fake.bothify('??-####').upper()}",
            })
            prod_id += 1
    return pd.DataFrame(products)


def generate_contracts(idns_df, products_df, n=150):
    """Generate contracts with deal structures and pricing terms."""
    contracts = []
    start_base = datetime(2023, 1, 1)

    for i in range(n):
        idn = idns_df.sample(1).iloc[0]
        structure = np.random.choice(DEAL_STRUCTURES, p=DEAL_STRUCTURE_WEIGHTS)
        category = np.random.choice(list(DEVICE_CATEGORIES.keys()))
        start_date = start_base + timedelta(days=np.random.randint(0, 540))
        duration_months = np.random.choice([12, 24, 36], p=[0.3, 0.5, 0.2])
        end_date = start_date + timedelta(days=int(duration_months) * 30)

        # Market share commitment based on deal structure
        if structure == "PV":
            market_share_commitment = round(np.random.uniform(0.80, 0.95), 2)
        elif structure == "DV":
            market_share_commitment = round(np.random.uniform(0.40, 0.60), 2)
        elif structure == "TV":
            market_share_commitment = round(np.random.uniform(0.25, 0.35), 2)
        else:
            market_share_commitment = 0.0

        # Base discount based on structure + IDN size
        size_factor = {"Large": 0.08, "Medium": 0.04, "Small": 0.0}[idn["tier"]]
        structure_discount = {"PV": 0.20, "DV": 0.15, "TV": 0.12, "Access": 0.05, "All Play": 0.03}
        base_discount = structure_discount[structure] + size_factor + np.random.normal(0, 0.02)
        base_discount = round(np.clip(base_discount, 0.02, 0.40), 3)

        # Status
        now = datetime(2025, 1, 15)
        if end_date < now:
            status = np.random.choice(["Expired", "Renewed"], p=[0.4, 0.6])
        elif start_date > now:
            status = "Pending"
        else:
            status = "Active"

        contracts.append({
            "contract_id": f"CTR-{i+1:04d}",
            "tenant_id": np.random.choice(TENANT_IDS),
            "idn_id": idn["idn_id"],
            "gpo_id": idn["gpo_id"],
            "deal_structure": structure,
            "device_category": category,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "duration_months": duration_months,
            "base_discount_pct": base_discount,
            "market_share_commitment": market_share_commitment,
            "status": status,
            "annual_volume_target": int(np.random.uniform(100, 5000)),
            "safe_harbor_compliant": True,
            "aks_risk_flag": np.random.choice(["Low", "Medium", "High"], p=[0.7, 0.25, 0.05]),
        })
    return pd.DataFrame(contracts)


def generate_rebate_programs(contracts_df):
    """Generate rebate programs attached to contracts."""
    rebates = []
    rebate_id = 1
    rebate_types = {
        "Volume": {"range": (0.02, 0.05), "trigger": "units_threshold"},
        "Loyalty": {"range": (0.01, 0.03), "trigger": "market_share_threshold"},
        "Bundle": {"range": (0.01, 0.02), "trigger": "cross_category_purchase"},
        "Growth": {"range": (0.005, 0.015), "trigger": "yoy_volume_increase"},
    }

    for _, contract in contracts_df.iterrows():
        # Each contract gets 1-3 rebate programs
        n_rebates = np.random.choice([1, 2, 3], p=[0.3, 0.5, 0.2])
        selected_types = np.random.choice(
            list(rebate_types.keys()), size=n_rebates, replace=False
        )
        for rtype in selected_types:
            config = rebate_types[rtype]
            pct = round(np.random.uniform(*config["range"]), 3)
            rebates.append({
                "rebate_id": f"REB-{rebate_id:04d}",
                "contract_id": contract["contract_id"],
                "rebate_type": rtype,
                "rebate_pct": pct,
                "trigger_type": config["trigger"],
                "trigger_threshold": round(np.random.uniform(0.5, 0.9), 2),
                "orientation": np.random.choice(["Offensive", "Defensive"], p=[0.4, 0.6]),
                "earned": np.random.choice([True, False], p=[0.65, 0.35]),
            })
            rebate_id += 1
    return pd.DataFrame(rebates)


def generate_transactions(contracts_df, products_df, idns_df, n=30000):
    """Generate transaction records with full pricing waterfall."""
    transactions = []
    active_contracts = contracts_df[contracts_df["status"].isin(["Active", "Renewed"])]

    if len(active_contracts) == 0:
        active_contracts = contracts_df.head(50)

    for i in range(n):
        contract = active_contracts.sample(1).iloc[0]
        # Pick a product from the contract's device category
        cat_products = products_df[products_df["category"] == contract["device_category"]]
        if len(cat_products) == 0:
            cat_products = products_df.sample(1)
        product = cat_products.sample(1).iloc[0]

        idn = idns_df[idns_df["idn_id"] == contract["idn_id"]].iloc[0]

        # Transaction date within contract period
        start = pd.to_datetime(contract["start_date"])
        end = pd.to_datetime(contract["end_date"])
        delta = (end - start).days
        if delta <= 0:
            delta = 365
        txn_date = start + timedelta(days=np.random.randint(0, delta))

        # Pricing waterfall
        list_price = product["list_price"]
        quantity = int(np.random.lognormal(mean=1.5, sigma=1.0))
        quantity = max(1, min(quantity, 200))

        # Invoice price = list price * (1 - base_discount)
        invoice_price = round(list_price * (1 - contract["base_discount_pct"]), 2)

        # GPO admin fee
        gpo = next(g for g in GPOS if g["gpo_id"] == contract["gpo_id"])
        gpo_fee = round(invoice_price * gpo["admin_fee_pct"], 2)

        # Rebate estimate (sum of potential rebates)
        rebate_pct = round(np.random.uniform(0.01, 0.06), 3)
        rebate_amount = round(invoice_price * rebate_pct, 2)

        # Lowest net = invoice - gpo fee - rebates
        lowest_net = round(invoice_price - gpo_fee - rebate_amount, 2)

        # Cost and margin
        unit_cost = product["cost"]
        margin = round(lowest_net - unit_cost, 2)
        margin_pct = round(margin / lowest_net * 100, 1) if lowest_net > 0 else 0

        # Total discount from list
        total_discount_pct = round(1 - (lowest_net / list_price), 3) if list_price > 0 else 0

        transactions.append({
            "transaction_id": f"TXN-{i+1:06d}",
            "tenant_id": contract["tenant_id"],
            "contract_id": contract["contract_id"],
            "idn_id": contract["idn_id"],
            "gpo_id": contract["gpo_id"],
            "product_id": product["product_id"],
            "transaction_date": txn_date.strftime("%Y-%m-%d"),
            "quantity": quantity,
            "list_price": list_price,
            "invoice_price": invoice_price,
            "gpo_admin_fee": gpo_fee,
            "rebate_amount": rebate_amount,
            "lowest_net_price": lowest_net,
            "unit_cost": unit_cost,
            "margin": margin,
            "margin_pct": margin_pct,
            "total_discount_pct": total_discount_pct,
            "deal_structure": contract["deal_structure"],
            "device_category": contract["device_category"],
            "region": idn["region"],
            "idn_tier": idn["tier"],
            "quarter": f"Q{((txn_date.month - 1) // 3) + 1} {txn_date.year}",
            "year": txn_date.year,
            "month": txn_date.month,
        })

    return pd.DataFrame(transactions)


def load_into_duckdb(gpos_df, idns_df, facilities_df, products_df,
                     contracts_df, rebates_df, transactions_df):
    """Load all DataFrames into DuckDB and create analytical views."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    con = duckdb.connect(DB_PATH)

    # Register and persist tables
    tables = {
        "gpos": gpos_df,
        "idns": idns_df,
        "facilities": facilities_df,
        "products": products_df,
        "contracts": contracts_df,
        "rebate_programs": rebates_df,
        "transactions": transactions_df,
    }

    for name, df in tables.items():
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
        print(f"  ✓ Created table '{name}' with {len(df):,} rows")

    # ─── Analytical Views ────────────────────────────────────────────────

    # Portfolio summary by device category (includes tenant_id for isolation)
    con.execute("""
        CREATE VIEW v_portfolio_summary AS
        SELECT
            tenant_id,
            device_category,
            deal_structure,
            COUNT(DISTINCT contract_id) AS contract_count,
            COUNT(*) AS transaction_count,
            ROUND(SUM(invoice_price * quantity), 2) AS total_revenue,
            ROUND(AVG(margin_pct), 1) AS avg_margin_pct,
            ROUND(AVG(total_discount_pct) * 100, 1) AS avg_discount_pct,
            ROUND(SUM(margin * quantity), 2) AS total_margin
        FROM transactions
        GROUP BY tenant_id, device_category, deal_structure
    """)

    # Price waterfall aggregation
    con.execute("""
        CREATE VIEW v_price_waterfall AS
        SELECT
            tenant_id,
            device_category,
            ROUND(AVG(list_price), 2) AS avg_list_price,
            ROUND(AVG(list_price - invoice_price), 2) AS avg_contract_discount,
            ROUND(AVG(gpo_admin_fee), 2) AS avg_gpo_fee,
            ROUND(AVG(rebate_amount), 2) AS avg_rebate,
            ROUND(AVG(lowest_net_price), 2) AS avg_lowest_net,
            ROUND(AVG(margin), 2) AS avg_margin,
            ROUND(AVG(unit_cost), 2) AS avg_cost
        FROM transactions
        GROUP BY tenant_id, device_category
    """)

    # Customer (IDN) performance
    con.execute("""
        CREATE VIEW v_customer_performance AS
        SELECT
            t.tenant_id,
            t.idn_id,
            i.name AS idn_name,
            i.tier AS idn_tier,
            i.region,
            g.name AS gpo_name,
            COUNT(DISTINCT t.contract_id) AS active_contracts,
            COUNT(*) AS transaction_count,
            ROUND(SUM(t.invoice_price * t.quantity), 2) AS total_revenue,
            ROUND(AVG(t.margin_pct), 1) AS avg_margin_pct,
            ROUND(AVG(t.total_discount_pct) * 100, 1) AS avg_discount_pct,
            ROUND(SUM(t.margin * t.quantity), 2) AS total_margin
        FROM transactions t
        JOIN idns i ON t.idn_id = i.idn_id
        JOIN gpos g ON t.gpo_id = g.gpo_id
        GROUP BY t.tenant_id, t.idn_id, i.name, i.tier, i.region, g.name
    """)

    # Monthly trends
    con.execute("""
        CREATE VIEW v_monthly_trends AS
        SELECT
            tenant_id,
            year,
            month,
            quarter,
            device_category,
            COUNT(*) AS transactions,
            ROUND(SUM(invoice_price * quantity), 2) AS revenue,
            ROUND(AVG(margin_pct), 1) AS avg_margin_pct,
            ROUND(AVG(total_discount_pct) * 100, 1) AS avg_discount_pct
        FROM transactions
        GROUP BY tenant_id, year, month, quarter, device_category
        ORDER BY year, month
    """)

    # Contract risk assessment
    con.execute("""
        CREATE VIEW v_contract_risk AS
        SELECT
            c.tenant_id,
            c.contract_id,
            i.name AS idn_name,
            c.deal_structure,
            c.device_category,
            c.status,
            c.market_share_commitment,
            c.base_discount_pct,
            c.aks_risk_flag,
            c.end_date,
            COUNT(t.transaction_id) AS transaction_count,
            ROUND(AVG(t.margin_pct), 1) AS avg_margin_pct,
            ROUND(SUM(t.invoice_price * t.quantity), 2) AS total_revenue,
            CASE
                WHEN c.aks_risk_flag = 'High' THEN 'Critical'
                WHEN AVG(t.margin_pct) < 15 THEN 'At Risk'
                WHEN c.base_discount_pct > 0.30 THEN 'Watch'
                ELSE 'Healthy'
            END AS risk_status
        FROM contracts c
        JOIN idns i ON c.idn_id = i.idn_id
        LEFT JOIN transactions t ON c.contract_id = t.contract_id
        GROUP BY c.tenant_id, c.contract_id, i.name, c.deal_structure, c.device_category,
                 c.status, c.market_share_commitment, c.base_discount_pct,
                 c.aks_risk_flag, c.end_date
    """)

    print(f"\n  ✓ Created 5 analytical views")
    print(f"  ✓ Database saved to {DB_PATH}")

    con.close()


def main():
    """Generate all synthetic data and load into DuckDB."""
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(TRANSFORMED_DIR, exist_ok=True)

    print("🏥 COPPER POC - Generating synthetic MedTech pricing data\n")

    print("1. Generating GPOs...")
    gpos_df = pd.DataFrame(GPOS)
    print(f"   {len(gpos_df)} GPOs")

    print("2. Generating IDNs...")
    idns_df = generate_idns(60)
    print(f"   {len(idns_df)} IDNs")

    print("3. Generating facilities...")
    facilities_df = generate_facilities(idns_df)
    print(f"   {len(facilities_df):,} facilities")

    print("4. Generating products...")
    products_df = generate_products()
    print(f"   {len(products_df)} products")

    print("5. Generating contracts...")
    contracts_df = generate_contracts(idns_df, products_df, 150)
    print(f"   {len(contracts_df)} contracts")

    print("6. Generating rebate programs...")
    rebates_df = generate_rebate_programs(contracts_df)
    print(f"   {len(rebates_df)} rebate programs")

    print("7. Generating transactions...")
    transactions_df = generate_transactions(contracts_df, products_df, idns_df, 30000)
    print(f"   {len(transactions_df):,} transactions")

    # Save as CSV (raw layer)
    print("\n8. Saving CSV files (raw layer)...")
    gpos_df.to_csv(os.path.join(RAW_DIR, "gpos.csv"), index=False)
    idns_df.to_csv(os.path.join(RAW_DIR, "idns.csv"), index=False)
    facilities_df.to_csv(os.path.join(RAW_DIR, "facilities.csv"), index=False)
    products_df.to_csv(os.path.join(RAW_DIR, "products.csv"), index=False)
    contracts_df.to_csv(os.path.join(RAW_DIR, "contracts.csv"), index=False)
    rebates_df.to_csv(os.path.join(RAW_DIR, "rebate_programs.csv"), index=False)
    transactions_df.to_csv(os.path.join(RAW_DIR, "transactions.csv"), index=False)
    print("   ✓ Saved to data/raw/")

    # Load into DuckDB
    print("\n9. Loading into DuckDB...")
    load_into_duckdb(gpos_df, idns_df, facilities_df, products_df,
                     contracts_df, rebates_df, transactions_df)

    print("\n✅ Data generation complete!")
    print(f"   Database: {DB_PATH}")
    print(f"   Raw CSVs: {RAW_DIR}/")


if __name__ == "__main__":
    main()
