#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
failures=0

pass() { echo "PASS $1"; }
fail() { echo "FAIL $1"; failures=$((failures + 1)); }

branch="$(git branch --show-current)"
if [[ -n "$(git status --porcelain)" ]]; then fail "working tree is dirty"; else pass "working tree clean"; fi
if [[ "$branch" == "main" || "$branch" == "master" ]]; then fail "release branch is $branch"; else pass "release branch $branch"; fi
if [[ -s .next/BUILD_ID ]]; then pass "production build artifact exists"; else fail "production build artifact missing"; fi

if git grep -n -I -E 'rzp_live_[A-Za-z0-9]+|sk_live_[A-Za-z0-9]+|SUPABASE_SERVICE_ROLE_KEY=ey' -- ':!package-lock.json' >/tmp/dhansetu-release-secret-scan.out 2>/dev/null; then
  fail "live secret pattern found"
else
  pass "no live secret pattern committed"
fi

if [[ -n "${BASE_URL:-}" ]]; then
  base="${BASE_URL%/}"
  for route in / /smartbudget /tools /api/health /api/smartbudget; do
    code="$(curl -ksS -o /dev/null -w '%{http_code}' "$base$route")"
    if [[ "$route" == "/api/smartbudget" ]]; then
      [[ "$code" == "401" ]] && pass "live $route unauthenticated boundary" || fail "live $route expected 401, got $code"
    else
      [[ "$code" == "200" ]] && pass "live $route 200" || fail "live $route expected 200, got $code"
    fi
  done
else
  echo "INFO BASE_URL not set; live probes skipped"
fi

if (( failures > 0 )); then
  echo "Release readiness: $failures gate(s) failed" >&2
  exit 1
fi
echo "Release readiness: all configured gates passed"
