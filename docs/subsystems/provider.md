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
| Checks, Rulesets, Actions compatibility | Not implemented | Not implemented |
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

Validation: `python -m unittest discover -s tests -p test_provider.py -v`.
Mock transport tests cover both platforms, pagination, budgets, errors, credentials,
and repeated unsupported mutations. Live Gitea and authenticated adapter calls are
NOT_RUN; deployed instance versions and scopes still need operator verification.

API references: [GitHub pagination](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api),
[GitHub retry guidance](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api),
[Gitea API usage](https://docs.gitea.com/development/api-usage/).
