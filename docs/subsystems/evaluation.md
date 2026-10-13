# Skills evaluation and lesson promotion (#5)

`agent_starter/evaluation.py` owns the observation/comparison contract.
`evals/tasks.json` uses actual starter Issue requirements, classified into governance,
Provider, bootstrap, scheduler and review. The closed MIT license task (#6) is a
positive baseline control; unresolved live protection (#7) is a manual NOT_RUN case.
Test inputs are reproducible adversarial scenarios derived from these project tasks,
not transcripts of an LLM completing a task.

```bash
python -m agent_starter.evaluation run --project /clean/baseline --suite evals/tasks.json --output /tmp/baseline.json
python -m agent_starter.evaluation run --project /clean/candidate --suite evals/tasks.json --output /tmp/candidate.json
python -m agent_starter.evaluation compare /tmp/baseline.json /tmp/candidate.json
python -m unittest discover -s tests -p test_evaluation.py -v
```

Review the suite and evaluated code before running it in an isolated environment
without write credentials. The evaluator executes unittest code, with no shell and
a 60s subprocess timeout. It is not a sandbox. Output files are exclusively created
so earlier evidence is not silently replaced. Observations include dataset digest,
source SHA/dirty status, rule/implementation digests, environment, case source,
outcome, duration and test-output hash. Missing runtime tests are FAIL with the
reason `implementation_missing`; manual tests are NOT_RUN. Zero discovered tests
cannot pass.

Comparison requires both reports to come from clean committed revisions, plus the
same dataset, environment, task IDs, categories and measured coverage. It reports success rate and error rate (fraction of failing scenarios),
category counts, wall-clock duration, measured tokens and monetary cost. Absent
cost/token data is NOT_MEASURED, never zero. NOT_RUN cases are listed and excluded
from rates; unequal coverage is rejected. Hashes identify evidence, not signatures.

## Initial recorded baseline

`evals/baseline.json`: clean `61158b3ae0da3b571053427d67a7028605face86`.
`evals/candidate.json`: clean `913c22aec1a6ec68907d49bdcf86c7bd5bf521ba`.
`evals/comparison.json` contains the actual comparison under the same interpreter/OS.
Baseline passes 1/7 observed cases (license); the six runtime scenarios are absent.
Candidate passes 7/7. Live protected-main is NOT_RUN in both. The baseline's tiny
duration is an absence check, not workload execution: these timings do not support
claims of speed/cost improvement. Rule digests are identical; implementation digests
differ. This measures newly compiled enforcement contracts, **not** improved prompt
or Skill effectiveness. LLM runs comparing changed instructions, token consumption,
API spend and statistical quality are NOT_RUN and need real instrumented task runs.

`validate_lesson()` requires root cause, evidence, reproduction, scope, prevention,
checks, observed date and review date. `promotion()` returns insufficient_evidence,
draft_pr_required or human_review_required. It never writes policy, modifies Skills
or expands Agent permissions. Security boundary changes require trusted owner review;
ordinary rule changes still require a Draft PR, independent review and comparable
task evidence. A higher score alone does not authorize promotion.

The LESSONS entry documents the observed #7 gap with reproducible read-only checks.
It is proposed evidence; no effective platform policy has been changed by this work.
