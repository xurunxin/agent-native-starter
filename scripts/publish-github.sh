#!/usr/bin/env bash
# Publish the local starter to a NEW public GitHub repo owned by xurunxin.
# Does not change GitHub branch-protection or release settings.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REPO="xurunxin/agent-native-starter"
if ! command -v gh >/dev/null 2>&1; then
  echo 'ERROR: Install GitHub CLI (gh) and authenticate using: gh auth login' >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo 'ERROR: Run gh auth login first.' >&2
  exit 1
fi
LOGIN="$(gh api user --jq .login)"
if [[ "$LOGIN" != "xurunxin" ]]; then
  echo "ERROR: GitHub CLI authenticated as $LOGIN, expected xurunxin." >&2
  exit 1
fi
if gh repo view "$REPO" >/dev/null 2>&1; then
  echo "ERROR: $REPO already exists; exiting without modifying it." >&2
  exit 1
fi
python3 scripts/policy_check.py
python3 scripts/validate_templates.py
python3 template/scripts/policy_check.py
if [ -d .git ]; then
  if [ -n "$(git remote -v)" ]; then
    echo 'ERROR: A git remote already exists; inspect it manually.' >&2
    exit 1
  fi
  if [ -n "$(git log --pretty='%H' -1 2>/dev/null || true)" ]; then
    echo 'ERROR: Existing git history. Use manual gh repo create flow.' >&2
    exit 1
  fi
else
  git init -b main
fi
if ! git config user.name >/dev/null || ! git config user.email >/dev/null; then
  echo 'ERROR: Set git config user.name and user.email, then rerun this script.' >&2
  exit 1
fi
git add -A
git commit -m 'chore: bootstrap agent-native engineering starter'
gh repo create "$REPO"   --public   --description 'Agent-native software engineering skills, project templates and GitHub/Gitea governance'   --source . --remote origin --push
printf '\nCreated: https://github.com/%s\n' "$REPO"
printf 'NEXT: Configure branch protection and required CI as docs/GITHUB_SETUP.md describes.\n'
