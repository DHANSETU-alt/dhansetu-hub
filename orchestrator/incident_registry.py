"""
ERT -- Ownership Matrix as data, not scattered if/else. Same "agents are
config, not code" philosophy as agents/*.yaml: adding an incident type or
changing an owner is a dict edit here, not a new conditional somewhere in
incident_manager.py.

Owners split into two real kinds, and this module is honest about the
difference:
  - SYSTEM owners (sentinel, governor, worker_pool, security, chrome_developer)
    have a real, checkable health signal (see ownership_engine.is_available()).
  - HUMAN-ROLE owners (Website Lead, Finance Lead, Security Lead, Customer
    Success Lead) have no presence/online-status system anywhere in this
    codebase -- there's no login system, no presence tracking. "Owner
    offline" detection for these is honestly unknown, not faked; they're
    always treated as available unless you wire up a real presence signal
    later (documented, not silently assumed away).
"""

SEVERITY_LEVELS = ("P0", "P1", "P2", "P3", "P4")

SEVERITY_LABELS = {
    "P0": "Critical Business Outage", "P1": "Website Down", "P2": "Payment Failure",
    "P3": "Performance Issue", "P4": "Minor Issue",
}

# Who gets notified per severity -- from the escalation rules spec.
SEVERITY_NOTIFY = {
    "P0": ["founder", "governor", "ert"],
    "P1": ["owner", "support_team"],
    "P2": ["auto_assign"],
    "P3": ["queue"],
    "P4": ["queue"],
}

# incident_type -> (owner, backup_owner, support_team list, default severity, is_system_owner)
OWNERSHIP_MATRIX = {
    "website_down":            {"owner": "chrome_developer", "backup": "website_builder", "support": ["sentinel", "bug_fixer", "security"], "severity": "P1", "system_owner": True},
    "ssl_failure":             {"owner": "chrome_developer", "backup": "website_builder", "support": ["security", "sentinel"], "severity": "P1", "system_owner": True},
    "security_incident":       {"owner": "security", "backup": "bug_fixer", "support": ["sentinel", "bug_fixer", "qa"], "severity": "P0", "system_owner": True},
    "payment_failure":         {"owner": "finance_lead", "backup": "finance_backup", "support": ["security", "bug_fixer"], "severity": "P2", "system_owner": False},
    "ai_model_failure":        {"owner": "ai_operations_lead", "backup": "sentinel", "support": ["sentinel"], "severity": "P1", "system_owner": False},
    "ceo_failure":             {"owner": "governor", "backup": "governor", "support": ["router_kernel"], "severity": "P0", "system_owner": True},
    "database_failure":        {"owner": "infrastructure_lead", "backup": "sentinel", "support": ["sentinel", "security"], "severity": "P0", "system_owner": False},
    "customer_complaint":      {"owner": "customer_success_lead", "backup": "knowledge", "support": ["correction_bot", "knowledge"], "severity": "P3", "system_owner": False},
    "performance_degradation": {"owner": "sentinel", "backup": "worker_pool", "support": ["worker_pool"], "severity": "P3", "system_owner": True},
    "agent_failure":           {"owner": "governor", "backup": "worker_pool", "support": ["worker_pool"], "severity": "P2", "system_owner": True},
    # From the resource/detection spec -- mapped onto the same matrix shape.
    "resource_critical":       {"owner": "sentinel", "backup": "worker_pool", "support": ["worker_pool"], "severity": "P1", "system_owner": True},
    "database_offline":        {"owner": "infrastructure_lead", "backup": "sentinel", "support": ["sentinel"], "severity": "P0", "system_owner": False},
    "ollama_offline":          {"owner": "ai_operations_lead", "backup": "sentinel", "support": ["sentinel"], "severity": "P1", "system_owner": False},
    "telegram_failure":        {"owner": "infrastructure_lead", "backup": "sentinel", "support": ["sentinel"], "severity": "P3", "system_owner": False},
    "sheets_failure":          {"owner": "infrastructure_lead", "backup": "sentinel", "support": ["sentinel"], "severity": "P3", "system_owner": False},
    "api_failure":             {"owner": "infrastructure_lead", "backup": "sentinel", "support": ["sentinel", "bug_fixer"], "severity": "P2", "system_owner": False},
    "repeated_exceptions":     {"owner": "bug_fixer", "backup": "governor", "support": ["sentinel"], "severity": "P2", "system_owner": True},
    "deployment_failure":      {"owner": "website_builder", "backup": "chrome_developer", "support": ["bug_fixer", "qa"], "severity": "P2", "system_owner": True},
}

# Rule-based lookup by a broader category, per "IF Incident Type = X -> Owner = Y".
# incident_registry.OWNERSHIP_MATRIX is the source of truth per specific
# type; this is the coarser category shortcut the spec asked for.
CATEGORY_TO_INCIDENT_TYPE = {
    "website": "website_down", "payment": "payment_failure", "security": "security_incident",
    "infrastructure": "database_failure", "agent_failure": "agent_failure", "customer_support": "customer_complaint",
}


def lookup(incident_type: str) -> dict:
    if incident_type not in OWNERSHIP_MATRIX:
        raise ValueError(f"unknown incident_type '{incident_type}' — expected one of {sorted(OWNERSHIP_MATRIX)}")
    return OWNERSHIP_MATRIX[incident_type]


def lookup_by_category(category: str) -> dict:
    incident_type = CATEGORY_TO_INCIDENT_TYPE.get(category.lower())
    if not incident_type:
        raise ValueError(f"unknown category '{category}' — expected one of {sorted(CATEGORY_TO_INCIDENT_TYPE)}")
    return lookup(incident_type)
