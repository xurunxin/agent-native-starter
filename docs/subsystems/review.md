# Review and integration evidence (#4)

`agent_starter/review.py:assess` is a pure protocol checker. It neither authenticates
records nor stores approvals nor merges PRs. A trusted controller must collect all
inputs independently of the PR, protect the reviewer/human identity registry and
verify artifact hashes. Never accept an `approved: true` file, policy list or identity
string supplied by an implementer as trusted authorization. Logical reviewer identity
must be a separate execution session from the implementer. Hosted approval roles
are an additional server requirement, not replaced by logical identity separation.

Inputs:

| Record | Required binding / contents |
|---|---|
| Current snapshot | repository, PR number, implementer identity, head/base SHA, integration tree SHA, policy digest, draft, complete changed paths |
| Independent review | same target/version/policy binding, registered reviewer, approve decision, artifact SHA256 list, explicit empty gaps |
| Verification | same head/base/tree, named successful checks with trusted producer and artifact SHA256, explicit empty gaps |
| Trusted policy | digest, auto_merge=false, reviewer/human registry, nonempty required check→producer map |
| Effective server policy | PR, no force/delete, required checks, independent/code owner/stale approval controls, strict base, enforced=true and audited bypass |
| Human merge authorization | issuer from trusted registry and same target/head/base/tree/policy binding |

Any head/base/integration-tree/policy change invalidates the prior review and merge
authorization. Rerun integration verification on the current trusted base and obtain
new approval. Missing/failed/ambiguous checks and producer mismatches block; skipped
or NOT_RUN evidence cannot be promoted to success. Auto-merge remains disabled.
Required server booleans are **observed control-plane evidence**, not claims from
repository configuration. A nonempty bypass list must be assessed against the owner
approved policy before the controller can set bypass_audited=true.

Sensitive paths are centrally listed in `SENSITIVE`, including rules, workflows,
templates, Skills, security/engineering policy, scripts and the protocol checker.
They require a separate version-bound human review record. The normal merge
authorization alone is not proof that sensitive changes were reviewed. New governance
entry points must be added to the trusted policy during maintainer review. No test
failure permits downgrading the policy or merging with older evidence.

Example: `tests/test_review.py:fixture` provides a complete synthetic low-risk README
change. `test_low_risk_evidence_protocol_positive_case` exercises the eligible case;
the remaining tests change head/base/tree/policy, spoof reviewer/check producer,
remove server/authorization evidence and introduce a sensitive path. These are
offline protocol tests, **not** a live PR/server enforcement acceptance record.

Validation: `python -m unittest discover -s tests -p test_review.py -v`.
Live protected-branch rejection, independent hosted review, integration merge and
authorized merge remain NOT_RUN pending Issue #7 and owner authorization. Use the
docs-only Draft PR for #7 as the live low-risk acceptance vehicle, collect its exact
head/base/check evidence, and retain the refusal/approval results after policy setup.
There is no automated merge API or side-effect dispatcher in this implementation.
