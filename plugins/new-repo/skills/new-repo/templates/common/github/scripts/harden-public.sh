#!/usr/bin/env bash
# Apply the public-repo rules: secret scanning with push protection, and protect main
# (PR required, security checks required, enforced for admins, no force push or delete).
# These features are free on public repos only, so private repos are left alone.
#
#   harden-public.sh [owner/repo]          apply the rules if the repo is public
#   harden-public.sh --check [owner/repo]  print a warning if the repo is public but unprotected
#
# Used by .github/workflows/public-hardening.yml, the Claude SessionStart hook and /new-repo.
set -euo pipefail

CHECK=false
if [ "${1:-}" = "--check" ]; then CHECK=true; shift; fi
R="${1:-${GITHUB_REPOSITORY:-}}"
if [ -z "$R" ]; then
  R=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null) || exit 0
fi

PRIVATE=$(gh api "repos/$R" -q .private 2>/dev/null) || { $CHECK && exit 0; echo "Can't read $R" >&2; exit 1; }
if [ "$PRIVATE" = "true" ]; then
  $CHECK || echo "$R is private; the public-repo rules are not applied."
  exit 0
fi

if $CHECK; then
  if ! gh api "repos/$R/branches/main/protection" >/dev/null 2>&1; then
    echo "WARNING: $R is public but main is not protected (no required PRs or security checks)."
    echo "Tell the user, and offer to run: bash .github/scripts/harden-public.sh"
  fi
  exit 0
fi

echo "Applying public-repo rules to $R"

gh api -X PATCH "repos/$R" --input - >/dev/null <<'JSON'
{"security_and_analysis": {
  "secret_scanning": {"status": "enabled"},
  "secret_scanning_push_protection": {"status": "enabled"}}}
JSON
echo "  secret scanning and push protection: on"

gh api -X PUT "repos/$R/branches/main/protection" --input - >/dev/null <<'JSON'
{
  "required_status_checks": {"strict": true, "contexts": ["codeql-analysis", "dependency-review"]},
  "enforce_admins": true,
  "required_pull_request_reviews": {"dismiss_stale_reviews": true, "required_approving_review_count": 0},
  "restrictions": null,
  "required_conversation_resolution": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
echo "  main protected: PR required, checks [codeql-analysis, dependency-review], enforced for admins"
