# Trusted leases and event handling (#3)

`agent_starter/scheduler.py` is a controller library, not an autonomous agent runner
or webhook HTTP service. SQLite is the authoritative local state; labels/comments
are never locks. A single trusted controller must own the database on a local disk
(not NFS), keep it outside PR worktrees, and deny untrusted code access using OS
permissions. All controller clients must use the same stored concurrency/retry/TTL
policy; mismatched clients are rejected. Backup the closed database before changes.

`event(task, delivery_id, revision, is_open)` accepts a **canonical repository
snapshot fetched by a trusted reconciler**. Verify webhook signatures and use
provider-prefixed delivery IDs; refetch Issue state with Provider before calling.
Do not pass webhook/Issue text as authorization. Revisions are controller-normalized
monotonic integers; equal or older revisions are out_of_order. Duplicate deliveries
are duplicate; reusing an ID for different content is an error. Closing/reopening
revokes prior generations. Completing local work does not close hosted Issues.

`claim()` atomically checks one owner per task, the global live-lease limit and
attempt budget under `BEGIN IMMEDIATE`. Same-owner retries return the same lease
without extending it or consuming an attempt. Every renewal/effect/finish requires
owner plus generation and an unexpired lease. Old owners fail with `LeaseLost`.
`effect()` persists an idempotent intent outbox: same key/content is duplicate;
same key/different content is rejected. It does **not** perform remote writes.
Provider mutations remain unsupported. A future dispatcher must validate the
current fence, reconcile existing remote artifacts and address ambiguous network
results before each write; this library does not promise exactly-once external APIs.

Expired leases are never automatically reclaimed. `recover()` requires fresh
(<=30s), generation-bound observations of branch, PR, execution process and
verification artifacts. Unknown/incomplete observations fail. Any existing artifact
blocks for manual reconciliation; only four checked absences release the task.
The trusted controller is responsible for gathering these observations. Fencing
the store cannot kill an old OS process; all writes must remain mediated and remote
branch protection must still apply. Use a synchronized controller clock; significant
clock rollback requires stopping work and reconciling leases.

`block()` immediately revokes a writer. `unblock()` requires an operator identity
and reason, records an audit entry, and preserves attempts unless the operator
explicitly resets the budget. Retry exhaustion blocks; nothing retries forever.
To use repository policy, pass the configured `max_parallel_tasks` and
`max_attempts_per_task` explicitly; this module does not parse YAML or grant roles.

Validation: `python -m unittest discover -s tests -p test_scheduler.py -v`.
Tests race eight threads with separate SQLite connections, verify one owner and the
global limit, replay/reorder events, fence an expired writer, block existing recovery
artifacts, enforce budgets, and reject conflicting idempotency keys. Live webhook
delivery, external writes, process termination and multi-host storage are NOT_RUN.
