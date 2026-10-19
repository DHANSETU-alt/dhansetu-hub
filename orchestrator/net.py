"""
Bridges Python's SSL verification to the OS-native trust store, if the
`truststore` package is installed. Optional, best-effort -- never a hard
dependency, never weakens verification (it still verifies, just against
the OS store instead of Python's bundled certifi one).

Why this exists: found live, not theoretical. Testing the Telegram
integration in this session, `curl` reached api.telegram.org fine but
Python's urllib failed with CERTIFICATE_VERIFY_FAILED against the same
host -- the local network path intercepts HTTPS with a certificate that
macOS's system trust store (which curl uses) trusts, but Python's bundled
cert store doesn't. This is not a one-off quirk of this dev sandbox: the
identical failure mode ("curl works, Python doesn't") is one of the most
common support issues for anyone running Python behind a corporate
SSL-inspecting proxy (Zscaler and similar) -- exactly the kind of network
a founder's managed work laptop might be on. Fixing it here once removes
an otherwise very confusing failure for Telegram, Google Sheets, and
Claude escalation alike.
"""
_enabled = False


def enable_system_trust():
    global _enabled
    if _enabled:
        return
    try:
        import truststore
        truststore.inject_into_ssl()
        _enabled = True
    except ImportError:
        pass  # optional -- falls back to Python's default (certifi) verification
