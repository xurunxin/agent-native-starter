#!/usr/bin/env bash
# Optional: seed six roadmap Issues in an existing public repository. Idempotent by exact title.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="xurunxin/agent-native-starter"
command -v gh >/dev/null || { echo 'ERROR: gh CLI required.' >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo 'ERROR: gh auth login required.' >&2; exit 1; }
gh repo view "$REPO" >/dev/null || { echo "ERROR: Cannot find $REPO" >&2; exit 1; }
if ! gh label list --repo "$REPO" --limit 100 --json name --jq '.[].name' | grep -Fxq 'roadmap'; then
  gh label create roadmap --repo "$REPO" --color '2563FF' --description 'Roadmap and planned capabilities'
fi
titles=(
  '[Phase 1] GitHub / Gitea Provider 与能力检测'
  '[Phase 1] 安全的 init / doctor / upgrade 初始化器'
  '[Phase 2] 可信租约和幂等调度'
  '[Phase 2] 独立审查、SHA 证据和安全合并门禁'
  '[Phase 3] Skills 评测和经验晋升'
  '[Governance] 选择开源许可证与贡献策略'
)
files=(
  '01-provider.md' '02-init-doctor-upgrade.md' '03-lease-scheduler.md'
  '04-review-merge.md' '05-learning-evals.md' '06-license-policy.md'
)
for i in "${!titles[@]}"; do
  title="${titles[$i]}"
  if gh issue list --repo "$REPO" --state all --limit 500 --json title --jq '.[].title' | grep -Fxq "$title"; then
    echo "SKIP (exists): $title"
  else
    gh issue create --repo "$REPO" --title "$title" --body-file "$ROOT/docs/proposed-issues/${files[$i]}" --label roadmap
  fi
done
