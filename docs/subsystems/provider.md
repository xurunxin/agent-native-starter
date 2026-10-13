# Provider contract (#1)

`agent_starter/provider.py` is a Python 3.12+ standard-library read adapter. Pass an
explicit HTTPS API root (`https://api.github.com` or `https://gitea.example/api/v1`)
and `owner/repo`. It never reads tokens from the environment or persists them.
Use a minimally scoped read-only token only in a trusted control process; the
`trusted=False` constructor rejects credentials. This flag is a caller contract,
not a sandbox: do not place *any* credential in a runner executing untrusted PR code.

| Contract | GitHub | Gitea |
|---|---|---|
| Repository / default branch | REST repository | REST repository |
| Issues / PRs / comments | Paginated reads | Paginated reads |
| Commit statuses | `/commits/{sha}/statuses` | `/statuses/{sha}` |
| Branch / protection | Classic protection read | Branch protection read |
| Check Runs (read, exact commit) | Paginated `check_runs` wrapper | Explicitly not implemented |
| Active branch rules + ruleset listing | Read only, including inherited rules | Not implemented |
| Actions compatibility | Not implemented | Not implemented |
| Issue/PR/comment/status/branch/protection writes | `not_implemented` | `not_implemented` |

Writes use `mutate(operation, payload)` and always fail before transport, including
calls with an idempotency key. Callers must never translate this into a successful
no-op or a weaker platform operation. Read retries are safe and bounded (default 3,
max 5); mutations are neither attempted nor retried. No merge/release API exists.
Raw provider JSON is returned so platform-specific fields are not silently mapped
to guarantees they do not provide. The scheduler must reconcile those fields in a
trusted controller; webhook bodies alone cannot establish ownership or approval.

`capability()` probes observed read access and returns `supported`, `denied`,
`unknown`, or `not_implemented`. A 404 cannot distinguish absence from hidden data;
it remains unknown. Read access never implies write/admin permission. Authentication,
permission, absence, conflict, invalid request, rate limit, transient server failure,
transport and malformed response errors have stable `ProviderError.code` values.
Errors omit response bodies and URLs to avoid credential leakage.

Pagination consumes Link headers, with Gitea X-PageCount fallback; cycles, foreign
origins and page-budget exhaustion fail closed. GET rate limits (429, or GitHub
403 with retry metadata) and 5xx retries respect bounded Retry-After values; a wait
over 60 seconds is returned to the caller instead of retrying early. Redirects are
disabled to prevent forwarding authorization to another host.

`branches()` enumerates branches so recovery does not mistake a hidden 404 for
absence; `checks(sha)` supplies exact-commit GitHub Check Runs to the recovery
collector. Neither API implies write authority.

Validation: `python -m unittest discover -s tests -p test_provider.py -v`.
Mock transport tests cover both platforms, pagination, budgets, errors, credentials,
and repeated unsupported mutations. Live Gitea and authenticated adapter calls are
NOT_RUN; deployed instance versions and scopes still need operator verification.

API references: [GitHub pagination](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api),
[GitHub retry guidance](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api),
[Gitea API usage](https://docs.gitea.com/development/api-usage/).

## Read-only branch-governance evidence (#7)

GitHub `rulesets()` lists repository/inherited rulesets, whereas
`active_branch_rules('main')` reads **active rules that apply specifically to
that branch** from `GET /repos/{owner}/{repo}/rules/branches/main`. The latter
excludes disabled/evaluate-only rulesets. Classic branch protection remains a
separate `protection('main')` call. The helper
`protection_observation('main')` combines the two as an explicit **observation**:
`classic: unknown` on 403/404, list of active rule types if accessible,
`live_negative_positive_tests: NOT_RUN`, `server_gate_verified: false`.

It never labels a branch safe because CI passed or because a ruleset was listed;
it cannot authenticate bypass roles, independently approved reviewers or rejected
push/merge operations. Gitea ruleset methods deliberately return not_implemented.
Run from an explicitly authorized trusted controller with ordinary read-only
repository access; no new token, write request or server settings mutation is
performed. GitHub documentation:
[Get rules for a branch](https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch).

Actual account-level rule enforcement/bypass inventory remains open in Issue #7.
