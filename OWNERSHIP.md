# Ownership

**Owner: codex** — dhansetuhub.in app

Agreed by the founder on 2026-09-21: Claude builds only blackboxops.co.in; Codex builds only
dhansetuhub.in. Either agent may READ anything and may AUDIT the other's live site, but only the
owner commits here.

If you are not the owner:
- Do not edit, commit or deploy from this folder.
- Raise what you found in `~/GVC_INC_OS/ACTIVE_MISSION.md` and let the owner act.

Why: on 2026-09-19 two agents edited the same Worker config within minutes of each other. The second
deploy narrowed the site route and blackboxops.co.in served 403 to every visitor until it was caught.

Enforcement: `.git/hooks/pre-commit` refuses commits unless `GVC_AGENT` matches the owner.
Claude runs with `GVC_AGENT=claude`, Codex with `GVC_AGENT=codex`.
