# Main protection acceptance record (#7, prerequisite for #4)

Status: **OWNER_APPROVAL_REQUIRED / LIVE_ACCEPTANCE_NOT_RUN**. This document and
the JSON proposal do not apply settings. No direct push to main, force push,
branch deletion, merge, invitation or new credential was attempted.

## Read-only observations, 2026-10-13 UTC

| Check | Observed evidence |
|---|---|
| Main baseline | `61158b3ae0da3b571053427d67a7028605face86` |
| Repository | Public, default branch `main` |
| Rulesets | `gh api repos/xurunxin/agent-native-starter/rulesets` → `[]` |
| Classic protection | `gh api repos/xurunxin/agent-native-starter/branches/main/protection` → HTTP 404 `Branch not protected` |
| Main CI | `validate`: success, [job evidence](https://github.com/xurunxin/agent-native-starter/actions/runs/38336729311/job/115098383230) |
| Check producer | GitHub Actions, slug `github-actions`, app ID `15368` from check-run API |
| Collaborators | `xurunxin`, admin; no other collaborator returned by the authenticated API |
| Existing CODEOWNERS | owner `@xurunxin` for AGENTS/config/workflows/scripts/Skills/templates/engineering |

These successful owner-level reads provide stronger evidence than the earlier
integration 403. A future 403 must be treated as unknown, not absent protection.
Ruleset inheritance and effective actor bypass must be rechecked after setup.

## Concrete proposed policy

[`proposals/main-protection.json`](proposals/main-protection.json) is a proposed
classic branch protection request for **main only**. It requires up-to-date
`validate` from the observed Actions app, one independent approval, stale approval
dismissal, approval of the latest push, code owner review, and resolved discussions.
It prohibits force push/deletion and applies requirements to admins. Proposed PR
bypass users/teams/apps are empty. It does not lock the branch or change merge
strategy. No organization-only push restrictions are proposed for this personal repo.
API field reference: [GitHub branch protection](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection).

Owner decisions required before applying:

1. Approve this exact policy (especially `enforce_admins`, one independent reviewer
   and no PR bypass allowances), or provide a reviewed replacement.
2. Designate a trusted independent reviewer with sufficient repository permission.
   The current sole collaborator cannot approve their own PR. Existing CODEOWNERS
   also need an owner-approved independent reviewer for sensitive changes. Proposed
   additional ownership paths: `/agent_starter/` and `/evals/`; do not substitute a
   guessed username or silently permit self-review.
3. Audit all owner/maintainer/App administrative rights and bypass allowances from
   the effective rules. Admins can change settings even when merge bypass is
   disabled; record that administrative power separately. Installed App permissions
   and any inherited policy are not fully inventoried here (NOT_RUN).

Do not request a new persistent token. Use the current authorized owner session;
if its management permission is insufficient, stop and report the specific action.
Re-read settings immediately before a write to avoid overwriting a concurrent
policy change. Prefer a reviewed Ruleset instead if the owner selects it.

## Live low-risk PR procedure — all pending

The docs-only Draft PR containing this record is the acceptance vehicle. It starts
on the recorded main baseline and adds no executable workflow. Before testing any
merge action, the owner must explicitly authorize the test and its safe outcome;
there is no general auto-merge authorization for this repository.

| Case | Required retained evidence | Result |
|---|---|---|
| Applied policy | Exact effective rule response, observed_at, approved policy digest, actor/bypass audit | NOT_RUN |
| Missing approval | Non-draft PR with successful exact-head CI remains blocked by required review | NOT_RUN |
| Failed required check | Independently approved low-risk revision with deliberately failing validate remains blocked | NOT_RUN |
| Stale approval | New head or base/integration tree invalidates prior review/verification | NOT_RUN |
| Authorized positive path | Fresh current SHA/tree evidence, independent approval, all checks and explicit owner merge authorization | NOT_RUN |
| Force/delete controls | Effective configuration and owner-approved safe server rejection test (never mutate main speculatively) | NOT_RUN |

A Draft PR being unmergeable proves draft state, not protection enforcement. Do not
use a merge request as a negative test unless the failure condition is independently
confirmed and the owner has authorized the possibility of a successful merge.
Record each PR number, head/base/integration tree, check producer/result, reviewer
identity, artifact digest, missing evidence and server refusal response. Keep Phase 0
and Issue #7 open until effective controls and the required live outcomes are verified.

## Implementation review queue

No runtime PR is merged; each is a single Issue-focused draft. Integrate in dependency
order and rerun tests on the latest main/integration tree after each authorized merge.

| Issue | Reviewable delivery | Remaining acceptance |
|---|---|---|
| #1 | [PR #8](https://github.com/xurunxin/agent-native-starter/pull/8): read Provider/error contracts | Mutations explicitly unimplemented; live Gitea NOT_RUN |
| #2 | [PR #9](https://github.com/xurunxin/agent-native-starter/pull/9), depends #8: safe init/doctor/upgrade | Hosted settings never changed; upgrades are reviewable diff proposals |
| #3 | [PR #10](https://github.com/xurunxin/agent-native-starter/pull/10), depends #9: atomic leases and fenced intents | Controller service/webhook/remote dispatcher integration not provided |
| #4 | [PR #11](https://github.com/xurunxin/agent-native-starter/pull/11), depends #10: version-bound review protocol | Live server enforcement and independent approved PR acceptance blocked on #7 |
| #5 | [PR #12](https://github.com/xurunxin/agent-native-starter/pull/12), depends #11: evaluations/lessons | Real LLM instruction-effect/token/cost measurements NOT_RUN/NOT_MEASURED |

Runtime candidate validation: 37 standard-library tests pass on Windows Python
3.13.15, plus the three static starter checks. Pre-implementation targeted tests
failed to import missing runtime modules. See each PR for exact head/base SHAs and
its commands. These are implementation evidence, not independent approval.
