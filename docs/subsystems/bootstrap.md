# Safe initializer (#2)

Run from the starter checkout with Python 3.12+:

```bash
python -m agent_starter init /path/to/project
python -m agent_starter doctor /path/to/project --verify "python scripts/policy_check.py"
python -m agent_starter doctor /path/to/project --provider github --api-url https://api.github.com --repository owner/repo
python -m agent_starter upgrade /path/to/project --branch agent-starter/upgrade
```

`agent_starter/bootstrap.py` owns the behavior; `__main__.py` is the JSON CLI.
`init` installs all bundled template files and Skills into `.agents/skills/`.
It uses exclusive creation, leaves identical files alone, and returns unified diffs
for conflicts without replacing them. Each permission/filesystem error is reported
by path and error class. Partial initialization can be retried: existing files are
still never overwritten. Exit 1 means conflicts/gaps; exit 2 means invalid invocation
or a filesystem/Git failure. No credentials are read or platform settings changed.

`doctor` checks file presence, placeholders and static safe-default lines (not a full
YAML parser), compares the configured default branch with provider metadata or
`origin/HEAD`, and reports read capability gaps. Without platform access the result
is explicitly NOT_RUN. It never claims read access proves server merge enforcement.
It runs only caller-supplied `--verify` commands, without a shell, with a 60s timeout;
it records exit codes and omits potentially sensitive command output. Do not use
this option for untrusted project code on a controller with credentials. YAML
verification commands are not automatically executed; supply the trusted command
explicitly. Missing commands are NOT_RUN, not success.

`upgrade` requires a clean repository root and a new branch. It writes only
`.agent-starter-upgrade/proposal.json` with base SHA and diffs. Custom governance,
workflows and other installed files are untouched. Review each diff, apply selected
changes and commit on this branch, then open a Draft PR using the normal platform
workflow. No PR mutation is attempted by the initializer. Existing reports cannot
be overwritten. Workflow/policy changes still require a trusted maintainer's review.

Source symlinks and target symlinks/junctions are refused. The controller and project
filesystem must be trusted: this is not an OS sandbox against hostile concurrent
filesystem replacement. Gitea Actions is never generated from GitHub Actions; the
bundled platform templates retain their existing separate roles.

Validation: `python -m unittest discover -s tests -p test_bootstrap.py -v` creates
temporary repositories and exercises conflicts, repeated calls, denied writes,
verification failure, link rejection, clean-tree checks and proposal branches.
