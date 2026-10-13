# Read-only recovery collection (#3)

`agent_starter/recovery.py:ReadOnlyRecoveryCollector` collects sources for
`Scheduler.recover`. The old four-boolean observation API is removed; unregistered
tasks are never automatically recovered or replayed.

The trusted launcher registers an immutable identity while its lease is live:

```python
binding = scheduler.bind_execution(
    task, owner, lease['generation'], repository='owner/repo',
    api_url='https://api.github.com', branch='task/issue-1', commit=commit_sha,
    run_id=run_id, runs_root=controller_runs_directory, pid=writer_pid)
collector = ReadOnlyRecoveryCollector(provider, controller_runs_directory)
# After expiration, called explicitly by the controller:
decision = scheduler.recover(task, lease['generation'], collector)
```

Registration binds repository/API origin, branch, full commit SHA, run ID, lease
generation, trusted run-registry directory and native PID/start identity. It cannot
be changed within a generation. The directory/database must be controlled by the
trusted launcher outside PR worktrees; this library does not grant OS permissions.

Actual collection:

| Source | Read and binding |
|---|---|
| Repository/branch | Provider verifies repository full_name/API origin, exhausts paginated branch listing, retains observed branch head and expected-commit match |
| PR | Provider exhausts open/closed PR listing and retains matching source repository/ref/number/head SHA; hidden/deleted matching head identity is unknown |
| Process | Windows Get-Process StartTime ticks, or Linux boot ID plus `/proc` start ticks; a recycled PID is distinguished from the registered writer |
| Verification | Provider reads exact-commit statuses and GitHub Check Runs, retaining check-run IDs and checking head SHA; trusted local run manifest and artifact bytes are hashed |

Native process checks are read-only. The code deliberately never uses `os.kill`
as a Windows liveness probe. Unsupported hosts or denied source reads are unknown.
Gitea Checks/Actions collection is explicitly unimplemented; Gitea recovery therefore
blocks for manual reconciliation instead of silently treating missing CI evidence
as absence. GitHub Check Run pagination uses the `check_runs` wrapper contract.

Local evidence is stored under `<runs_root>/<run_id>/verification.json`. It must
contain repository, api_url, branch, commit, run_id and generation matching the
registered execution, plus a nonempty `artifacts` list of `{path, sha256}`. The
collector hashes artifact bytes in bounded 1 MiB chunks (maximum 64 MiB per
artifact), refuses escaped paths/links, and retains
the manifest hash. A run directory with partial files still counts as present;
malformed, mismatched or altered evidence becomes unknown. No verification file
is executed and no source API is mutated.

Collection runs outside the SQLite write lock. Recovery then rechecks expired
generation/ownership and requires the entire collection to be <=30s old. Any
present or unknown source blocks; only four collected absences release to ready.
The exact identity-bound evidence and decision are retained in `recovery_audit`.
Concurrent closure/blocking/reassignment prevents applying old collection results.

Scope: the collector verifies registered writer processes and named local/remote
artifacts. A launcher must register/control every possible writer; arbitrary child
processes, unknown branches or hidden external systems are not safely inventoried
by a PID check. This is an explicit reconciliation tool, not an autonomous runner,
remote write dispatcher, distributed snapshot or guarantee of exactly-once effects.
Do not replay an unknown task. Effective branch protection is still pending #7.

Validation: `python -m unittest discover -s tests -p test_recovery.py -v` uses the
real Provider with mock paginated API data, actual SQLite/filesystem artifacts and
a real owned short-lived process. It covers identity/digest mismatches, PID reuse,
denial, stale/unregistered recovery and revocation during collection. Live Gitea
and multi-host/child-process inventory remain NOT_RUN.
