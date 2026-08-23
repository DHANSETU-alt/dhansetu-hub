"""
Owner / Family / Guest identity — Phase v4. Passphrase-based, same
"manual entry, changes frequently, never stored" pattern as Telegram/
Sheets credentials: env var or CLI flag, checked fresh every call, never
written to a config file.

Unknown/no passphrase always resolves to "guest" -- fail toward the least
privilege, not the most.
"""
import os

IDENTITIES = ("owner", "family", "guest")

# Which identity may trigger which action category. Deliberately coarse --
# 5 categories, not a permission per command. Owner: everything. Family:
# read-only status + Buddy. Guest: Buddy only.
PERMISSIONS = {
    "owner": {"finance", "security", "admin", "status", "buddy"},
    "family": {"status", "buddy"},
    "guest": {"buddy"},
}


def identify(passphrase: str = None) -> str:
    owner_pass = os.environ.get("SHAKTHI_OWNER_PASSPHRASE")
    family_pass = os.environ.get("SHAKTHI_FAMILY_PASSPHRASE")

    if passphrase and owner_pass and passphrase == owner_pass:
        return "owner"
    if passphrase and family_pass and passphrase == family_pass:
        return "family"
    return "guest"


def allowed(identity: str, action_category: str) -> bool:
    return action_category in PERMISSIONS.get(identity, set())
