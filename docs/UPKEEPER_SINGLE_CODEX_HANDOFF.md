# Upkeeper — Single-Codex Handoff

## Founder objective

Build and deliver a real native macOS application named **Upkeeper**. It should combine a serious Mac-cleaning product with MangoDisk-style disk intelligence and an advanced AI-assisted firewall/security layer. The goal is a working product and distributable `.dmg`, not a suggestion-only plan.

## Required product scope

- Native macOS application with SwiftUI.
- Disk usage visualization/treemap.
- Large-file, duplicate-file, cache, temporary-file, and application-leftover analysis.
- Application uninstall and cleanup.
- Startup/background-item management.
- Mac health: CPU, RAM, disk, battery, and thermal information where available.
- Review-before-delete workflow, risk labels, exclusions, operation history, rollback/recovery where feasible.
- Real firewall enforcement with per-application inbound/outbound rules.
- Suspicious connection, DNS/domain, tracker, phishing, and command-and-control detection.
- Process-to-connection visibility and firewall event history.
- AI explanations and recommendations; deterministic rules plus explicit user confirmation decide enforcement.
- Offline-first behavior and privacy-preserving local storage.
- Signed and notarized `.app` and `.dmg` release.

## Security implementation requirement

Use macOS-native Network Extension and Endpoint Security/System Extension APIs. Production firewall and Endpoint Security distribution will require the correct Apple entitlements, signing identities, permissions, and developer enrollment.

## Current verified repository state

- No `Upkeeper.app` exists in the repository.
- No `.dmg` exists in the repository.
- No Upkeeper native source project currently exists.
- Existing `shakthi.db` records claim earlier Upkeeper work, but the claimed artifacts are absent and must not be treated as proof.
- Existing Python/Flask cleaner and health concepts may be reused only after inspection; they are not a substitute for the native app.

## Execution standard

The next Codex session should implement the product in the repository. Every milestone must produce inspectable artifacts and tests. Do not report completion from database status labels or prose alone.

Required release evidence:

1. `upkeeper-mac/` native project.
2. Compilable Swift sources and tests.
3. Working scanner and firewall prototypes on a real Mac.
4. Test report, including safety and false-positive tests.
5. `Upkeeper.app`.
6. `Upkeeper-<version>.dmg`.
7. SHA-256 checksum.
8. Signing/notarization results, or an explicit blocker naming the missing Apple credential/entitlement.

## First implementation target

`create native project -> build SwiftUI shell -> implement read-only disk scanner -> render treemap -> implement firewall monitor -> persist events -> add tests -> build .app -> build .dmg`

