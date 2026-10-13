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

The snapshot reads Git objects, covering AGENTS.md, CLAUDE.md, agent-project.yaml,
docs/engineering.md and all tracked skills/ and .agents/skills/ files (including
references/metadata). It retains per-file SHA256, source SHA,
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
- usage with input_tokens, output_tokens, total_tokens and cost_usd. Optional
  cached_input_tokens is a subset of input_tokens (legacy receipts may omit it).
  Unknowns are JSON null, never invented zero. Token totals must agree when all
  counts exist, and cached_input_tokens may not exceed measured input_tokens.
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

The bounded [public workflow pilot](../evidence/2026-10-13-public-workflow/README.md)
now records two actual model requests, frozen old/new public rules, identical
scenarios and CLI usage. Each batch passed all three decision checks; this small
prompted sample shows no improvement. Monetary cost remains NOT_MEASURED.
This pilot is not a coding-task effectiveness trial; see the later observation
status below. Issue #5 stays partial. At that recorded validation, the local Windows
suite passed 61 tests, including installed .agents/skills metadata/reference coverage.
A fixture used LF hashing but Windows text output introduced CRLF; write_bytes freezes
its intended input. Server protection and independent-review acceptance remain separate.

## Repeated real implementation-task comparisons (#5 / #19)

The existing importer remains the one authoritative evidence path. Prepare actual
task implementations in **independent clean checkouts**, starting with the same
implementation base and task bytes, but two different fixed AGENTS/Skills revisions.
Pre-register the task list, tests, model, seed/parameters where supported, budget,
randomized/alternating order, and stop condition outside the project. Do not hide
failed attempts, human rescues, cache effects, or platform wait time.

Import each baseline/candidate observation as above, then compare actual repeats:

```bash
python -m agent_starter.evaluation replicates \
  --pair /evidence/old-1.json /evidence/new-1.json \
  --pair /evidence/old-2.json /evidence/new-2.json \
  --output /evidence/replicates-summary.json
```

`replicates` only accepts **observed_task_run / instrumented_task_import**
reports, checks repeated source/rule/implementation identities, rejects reused
run IDs, and requires the exact same dataset/environment/coverage. It summarizes
PASS/FAIL/NOT_RUN, actual duration, separate input/output/total/cached token usage
and measured USD (otherwise NOT_MEASURED). A single pair or any NOT_RUN case is
marked INCOMPLETE. **Even two complete pairs are observational evidence only**:
the report deliberately says `causal_effect: NOT_ESTABLISHED`; reviewers must
separately judge randomization, external correctness, prompt disclosure, rescue,
variance and repeat count before asserting generalized benefit. No model call or
provider key is ever made by this command.

## Current observation status

[Issue #25](https://github.com/xurunxin/agent-native-starter/issues/25), published
2026-10-13 at 19:17 UTC, reports one anonymous paired coding task. Both arms retained
the original project rules; A also retained an existing local Starter skill/governance
bundle, while B removed 19 Starter-origin files. This is not a no-rules control,
a latest-main trial, a Skill-only intervention, or a platform-runtime evaluation.
The summary reports poorer first-pass correctness and higher cumulative development
time for A, with both arms passing the agreed checks after repair. It does not
establish that Starter caused either difference, nor that Starter is ineffective.

The raw project, exact rule provenance, complete model identity and task artifacts
are not publicly available for independent verification. Do not fabricate snapshots,
receipts or an `instrumented_task_import` report from this summary. It is **not a
publicly fully reproducible dataset**. Token/cost data remain NOT_MEASURED. Controlled,
repeated implementation-task acceptance under #19/#5 is still incomplete; the mere
existence of this pair or passing CLI fixtures does not close either Issue.

## First-pass, review and repair observations

This is an **evaluation-only recording procedure**, not a new Agent workflow,
mandatory test checklist, result schema, automatic aggregator or model executor.
It uses the existing input/output/verification/usage artifacts and freeze/import/
compare/replicates commands. No paid runs or private-data uploads are authorized.

1. Fix the common task/code base, actual rule-file intervention, model/tool settings,
   acceptance oracle, order, repetitions and budget before running. Distinguish
   declared rule provenance from files actually present/read. Retain evidence for
   non-rule base equality: `implementation_digest` covers `agent_starter/*.py`,
   not a downstream Go/Vue codebase. Additional loaded governance documents outside
   the documented freeze list must not be claimed as covered by `rules_digest`.
2. Seal the first output before independent review/repair. Import its independently
   verified PASS/FAIL with first-stage duration and usage; preserve those artifacts.
   After repair, create a separate output/verification/receipt and import, retaining
   a local trial/checkpoint relation to the first observation. Do not edit the first
   report or reuse its usage as if it measured repair. Compare first with first and
   final with final in separate invocations; checkpoints of one trial are **not**
   extra independent replicates. Keep observation run IDs distinct.
3. In the existing verification artifact, retain checkpoint/output identity, passed/
   total oracle checks, and deduplicated findings with discovery source, severity,
   reproducer and affected checks. Separate independent review from implementer
   self-checks, tool/test discovery and verifier/environment faults. Task-level
   first-pass success is not the probe pass fraction; one defect may fail several
   probes. New post-review probes should be labeled exploratory and applied to both
   frozen arms, without silently changing the pre-registered primary denominator.
4. Record first-stage development, repair development and review/feedback wait
   separately, using consistent clock boundaries. Record active reviewer effort,
   rule-reading/document work and intervention counts only when observed. These
   sub-costs may already be included in development: do not add them twice. Unknown
   values remain null/NOT_MEASURED. Preserve per-pair results, not only pooled totals.

The importer hashes the complete verification artifact but currently validates only
its existing binding/status/seconds/errors fields. Extra checkpoint/finding/cost
fields are **not semantically validated or automatically surfaced** by compare or
replicates. Review them alongside the phase-specific reports; any future optional
metric projection belongs in the existing importer/aggregator, with narrow contract
tests, not a parallel evaluator. Do not hand-edit imported reports to add metrics.

For rule attribution, inspect available read logs, the existing one-line stage/risk
choice and the actual targeted checks. Reading a Skill is not proof of applying it;
a failed implementation alone cannot establish a missing or ignored rule. Missing
trace evidence is unknown, not noncompliance. Domain counterexamples from #25 stay
scoped task samples unless repeated evidence or serious risk supports a separately
reviewed, concise rule proposal. No global test, approval or hash pipeline is added.
