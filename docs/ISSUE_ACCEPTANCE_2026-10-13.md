# 2026-10-13 Issue acceptance

The user authorized closing Issues after verifying their original requirements and
landing targets. This record separates core library contracts from production
platform/service claims.

Fixed landed source: `840cdeeac87d0668bac6b169b5dd989c56cf784e`.
[Main CI](https://github.com/xurunxin/agent-native-starter/actions/runs/38341997626)
is a successful push run for this exact SHA, with 51 executed Python tests and
three static checks. The logs were read, including real owned process probes,
artifact checks and secret-safe bootstrap reporting.

| Issue | Result | Fixed acceptance evidence / remaining scope |
|---|---|---|
| #1 | Closed, completed | [acceptance comment](https://github.com/xurunxin/agent-native-starter/issues/1#issuecomment-6138041135); read contracts and dual-platform mock tests. The original criteria allow explicit unimplemented methods. Full writes/live Gitea are not claimed. |
| #2 | Closed, completed | [acceptance comment](https://github.com/xurunxin/agent-native-starter/issues/2#issuecomment-6138055054); exclusive creation, hash-only conflict reporting, gap-aware doctor, branch-only upgrade proposals, temporary-project/idempotency/denied-write tests. |
| #3 | Closed, completed | [acceptance comment](https://github.com/xurunxin/agent-native-starter/issues/3#issuecomment-6138057035); atomic lease/fencing/receipt/budget protocol and actual identity-bound Provider/OS/artifact recovery collector. No claim of a resident webhook server, dispatcher or multi-host process inventory. |
| #4 | Open, partial | Pure review protocol is landed; effective protected branch, independent hosted reviewer and live negative/positive gate acceptance remain missing. |
| #5 | Open, partial | Offline contract baselines are landed. [Draft #15](https://github.com/xurunxin/agent-native-starter/pull/15) adds frozen-rule and instrumented result import; actual model task effectiveness/token/cost trials remain NOT_RUN/NOT_MEASURED. |
| #7 | Open, blocked | The policy proposal is documentation, not applied Settings. Owner policy approval, eligible independent reviewer, bypass audit and live rejection/authorized success still required. |

#6 was already closed for the landed MIT license decision and was not reprocessed.
Issue closure does not authorize server changes, merge, publication or credential
expansion.

[Draft #14](https://github.com/xurunxin/agent-native-starter/pull/14) contains the
requested installable Codex Skill and init preview supplement. The installable
package is `skills/project-bootstrap/`; the README one-sentence prompt points to
a verified immutable Skill revision containing the same Skill/CLI implementation.
The new Skill is normally discoverable, preserves existing project rules/code/CI/
license, and does not install globally or imply merge/server-policy permissions.

Validation of the supplements is separate from landed-source acceptance:
- Skill/preview commit `571b5ea618257f55e3f698766c03b1180c2e20cf`:
  [CI](https://github.com/xurunxin/agent-native-starter/actions/runs/38343743347),
  54 tests and three static checks passed; three new isolated adoption cases.
- Instrumented import commit `29288f08441ec66d77a2c504531bc005566c29a5`:
  [CI](https://github.com/xurunxin/agent-native-starter/actions/runs/38344594357),
  60 tests and three static checks passed; nine new synthetic mechanism cases.
- Final head updates require their own CI; previous head evidence is not reused
  as validation of new code or integration trees.
- Local quick_validate.py and new local tests: NOT_RUN. The original executor
  rejects the original task directory at process startup with os error 267. Its
  unfinished local README merge has not been overwritten, reset or deleted.
- No paid model API, real private repository data or global installation was used.
