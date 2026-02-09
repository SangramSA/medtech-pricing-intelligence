"""
Load tenant configuration from config/tenants.yaml.
Returns list of {id, name} for the tenant selector and data isolation.
"""

import os
import yaml


def _config_path():
    return os.path.join(os.path.dirname(__file__), "tenants.yaml")


def get_tenants():
    """Return list of dicts with 'id' and 'name' for each tenant, from tenants.yaml."""
    path = _config_path()
    if not os.path.exists(path):
        return [
            {"id": "meddevice_corp", "name": "MedDevice Corp"},
            {"id": "orthotech_inc", "name": "OrthoTech Inc"},
        ]
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    tenants = data.get("tenants") or {}
    return [{"id": tid, "name": t.get("name", tid)} for tid, t in tenants.items()]


def get_tenant_id_by_name(name: str) -> str:
    """Return tenant id for a display name, or first tenant id if not found."""
    tenants = get_tenants()
    for t in tenants:
        if t["name"] == name:
            return t["id"]
    return tenants[0]["id"] if tenants else "meddevice_corp"
