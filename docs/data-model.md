# COPPER POC — Data Model

Entity-relationship diagram for the MedTech pricing intelligence database (DuckDB).

## Entity relationship diagram

```mermaid
erDiagram
    gpos ||--o{ idns : "members"
    idns ||--o{ facilities : "owns"
    idns ||--o{ contracts : "has"
    gpos ||--o{ contracts : "negotiates"
    contracts ||--o{ rebate_programs : "has"
    contracts ||--o{ transactions : "generates"
    products ||--o{ transactions : "sold_in"
    idns ||--o{ transactions : "via_contract"

    gpos {
        varchar gpo_id PK
        varchar name
        double admin_fee_pct
        int member_count
    }

    idns {
        varchar idn_id PK
        varchar name
        varchar gpo_id FK
        int facility_count
        bigint annual_spend
        varchar region
        varchar state
        varchar tier
    }

    facilities {
        varchar facility_id PK
        varchar idn_id FK
        varchar name
        varchar facility_type
        int bed_count
        varchar state
        varchar region
    }

    products {
        varchar product_id PK
        varchar name
        varchar category
        double list_price
        double cost
        varchar sku
    }

    contracts {
        varchar contract_id PK
        varchar tenant_id
        varchar idn_id FK
        varchar gpo_id FK
        varchar deal_structure
        varchar device_category
        date start_date
        date end_date
        int duration_months
        double base_discount_pct
        double market_share_commitment
        varchar status
        int annual_volume_target
        boolean safe_harbor_compliant
        varchar aks_risk_flag
    }

    rebate_programs {
        varchar rebate_id PK
        varchar contract_id FK
        varchar rebate_type
        double rebate_pct
        varchar trigger_type
        double trigger_threshold
        varchar orientation
        boolean earned
    }

    transactions {
        varchar transaction_id PK
        varchar tenant_id
        varchar contract_id FK
        varchar idn_id FK
        varchar gpo_id FK
        varchar product_id FK
        date transaction_date
        int quantity
        double list_price
        double invoice_price
        double gpo_admin_fee
        double rebate_amount
        double lowest_net_price
        double unit_cost
        double margin
        double margin_pct
        double total_discount_pct
        varchar deal_structure
        varchar device_category
        varchar region
        varchar idn_tier
        varchar quarter
        int year
        int month
    }
```

## Hierarchy (conceptual)

```
GPO (Group Purchasing Organization)
 └── IDN (Integrated Delivery Network / Hospital System)
      └── Facility (Hospital, ASC, Clinic)

Vendor (tenant) → Contracts → Transactions
Products → Transactions
Contracts → Rebate Programs
```

## Analytical views (derived)

| View | Purpose |
|------|---------|
| `v_portfolio_summary` | Revenue, margin, contract count by device_category, deal_structure (and tenant_id) |
| `v_price_waterfall` | Avg list, discount, GPO fee, rebate, lowest net, cost, margin by device_category (and tenant_id) |
| `v_customer_performance` | Per-IDN revenue, margin, contract count (and tenant_id) |
| `v_monthly_trends` | Monthly revenue, margin, discount by device_category (and tenant_id) |
| `v_contract_risk` | Per-contract risk status, revenue, margin (and tenant_id) |

All views are built from `transactions` and/or `contracts` and include `tenant_id` for multi-tenant isolation.
