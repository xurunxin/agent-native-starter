# Instrumented task result import (#5)

`agent_starter/task_runs.py` provides a standard result-import path for actual task
runners. It does not execute tasks, call a model, install SDKs or calculate guessed
prices. The existing unittest/LICENSE suite remains an offline contract baseline;
its coverage cannot demonstrate better Skill or Agent effectiveness.

## Freeze a source rule bundle
Use a clean trusted Git checkout. Evidence outputs must be outside the source tree
and are exclusively created. Freeze each baseline/candidate at its full fixed SHA:

```bash
python -m agent_starter.task_runs freeze "/trusted/project" --output "/evidence/baseline-rules.json"
python -m agent_starter.task_runs freeze "/trusted/project" --revision FULL_COMMIT_SHA --output "/evidence/candidate-rules.json"
```

The snapshot reads Git objects, covering AGENTS.md, agent-project.yaml and all tracked
Skills files (including references/metadata). It retains per-file SHA256, source SHA,
rules digest, implementation digest and snapshot digest without exporting rule text.
Import recomputes this snapshot from the named Git commit; dirty/unknown source or
altered snapshots are rejected. Different rule bundles can be compared without
confusing changed runtime implementation with changed instructions.

## Standard normalization adapter contract
An operator-trusted runner exports JSON and artifacts; the importer reads data only.
A suite has `schema_version: 1` and `tasks`, each with a unique `id`, `category`
and `input_sha256` for the exact scenario bytes. Its canonical JSON SHA256 is the
dataset digest. Keep task IDs, input bytes, categories and measured coverage the
same across baseline/candidate.

Results have `schema_version: 1`, source_sha, rules_digest, snapshot_digest,
dataset_digest, environment and cases. Environment explicitly contains runner,
version, provider, model, numeric generation parameters and measurement_kind.
Use `synthetic_fixture` for mechanism fixtures and `observed_task_run` only for
actual measured tasks; comparisons require identical environments and print the kind.

Each case supplies:
- id, unique run_id, input_sha256, PASS/FAIL/NOT_RUN, seconds, errors.
- usage with input_tokens, output_tokens, total_tokens and cost_usd. Unknowns are
  JSON null, never invented zero. Token totals must agree when all counts exist.
- artifacts mapping input/output/verification/usage to {path, sha256} under the
  explicit trusted artifact directory. Input bytes must match the frozen scenario.
- The verification artifact is JSON containing binding, status, seconds and errors.
  The usage artifact contains binding, environment and the identical usage values.

Both artifact bindings contain source_sha, rules_digest, snapshot_digest,
dataset_digest, task_id, run_id and input_sha256. The importer reads actual bytes
and checks hashes, scope, outcome/usage consistency and exact identity. It rejects
path escape, links, missing evidence, >1 MiB artifacts, duplicate/incomplete coverage
and invalid or edited metrics. A NOT_RUN case instead supplies a reason, empty
artifacts and null duration/errors/usage, and cannot claim an outcome or cost.

An adapter should normalize measured provider usage or an explicit trusted cost
record; it must not infer unmeasured USD from token counts. No provider adapter or
paid execution is invoked here. Model responses, verification content and receipts
stay in the operator's evidence directory; the exported report retains fingerprints,
numeric observations and metadata only.

```bash
python -m agent_starter.task_runs import "/trusted/project" --snapshot "/evidence/rules.json" --suite "/evidence/suite.json" --results "/evidence/results.json" --artifacts "/evidence/run-artifacts" --output "/evidence/report.json"
python -m agent_starter.evaluation compare "/evidence/baseline-report.json" "/evidence/candidate-report.json"
```

Reports freeze source/rules/scenario identities, artifact fingerprints, full usage,
results digest and report digest. The existing comparator refuses edited imported
reports, mismatched environment/coverage and dirty source; it identifies synthetic
versus observed measurements. Hash consistency is not cryptographic producer
authentication or a semantic oracle: trust the runner/evidence storage and review
its task verifier. A malicious producer could fabricate mutually consistent files.
These reports do not approve merges or promote policy automatically.

## Actual validation and remaining acceptance
`python -m unittest discover -s tests -p test_task_runs.py -v` uses two actual
committed synthetic rule versions and the same frozen scenario, with generated
output/verification/usage artifacts. Tests cover import/CLI, non-null fixture metrics,
unknown preservation, changed rules, hashes, source/runner binding, edited reports,
duplicate coverage, dirty source, NOT_RUN and path escape. No model SDK/network call
or real private repository data is used. Fixture rates/token/cost values are only
test data; they are not empirical effectiveness or spending.

Real Agent/model task runs, instruction-effect experiments and measured real token/
cost comparisons remain NOT_RUN/NOT_MEASURED. Issue #5 stays partial until that
evidence exists. Local execution is NOT_RUN while the original executor directory
fails with error 267; CI on the exact supplement commit provides separate test evidence.
