"""Pure fail-closed evidence protocol. Never authenticates users or merges a PR."""
from fnmatch import fnmatchcase
import re


SENSITIVE = ('AGENTS.md', 'agent-project.yaml', 'SECURITY.md', 'skills/**', 'scripts/**',
             '.github/**', '.gitea/**', 'template/**', 'docs/engineering.md',
             'agent_starter/**', 'docs/adr/**', 'docs/proposals/**',
             'docs/proposed-issues/**', 'docs/GOVERNANCE_ACCEPTANCE.md',
             'docs/GITHUB_SETUP.md', 'docs/ROADMAP.md', 'docs/subsystems/review.md')
SERVER_FIELDS = ('pr_required', 'no_force_push', 'no_delete', 'required_checks',
                 'independent_approval', 'stale_approval_dismissal', 'code_owner_review',
                 'strict_base', 'bypass_audited', 'enforced')


def digest(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[0-9a-f]{64}', value))


def bound(record, current, *, include_target=True):
    fields = ('head', 'base', 'tree', 'policy_digest')
    if include_target:
        fields += ('repository', 'pr')
    return isinstance(record, dict) and all(record.get(f) == current.get(f) and
                                           current.get(f) is not None for f in fields)


def assess(current, review, verification, policy, server, authorization=None):
    """Inputs must come from authenticated trusted collection, never a PR JSON file."""
    blockers = []
    if not all(isinstance(x, dict) for x in (current, review, verification, policy, server)):
        return {'eligible': False, 'blockers': ['invalid_schema']}
    if any(not isinstance(policy.get(name), list) or
           any(not isinstance(x, str) or not x for x in policy[name]) for name in ('reviewers', 'humans')):
        return {'eligible': False, 'blockers': ['invalid_identity_registry']}
    for field in ('head', 'base', 'tree'):
        if not isinstance(current.get(field), str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', current[field]):
            blockers.append('invalid_' + field)
    if not digest(current.get('policy_digest')) or current.get('policy_digest') != policy.get('digest'):
        blockers.append('policy_changed_or_unknown')
    if not isinstance(current.get('repository'), str) or not current.get('repository') or type(current.get('pr')) is not int or current['pr'] <= 0:
        blockers.append('invalid_target')
    if current.get('draft') is not False:
        blockers.append('draft_or_unknown')
    if policy.get('auto_merge') is not False:
        blockers.append('auto_merge_not_authorized')
    identity = review.get('reviewer')
    if not isinstance(current.get('implementer'), str) or not current.get('implementer') or not isinstance(identity, str) or not identity or identity == current.get('implementer') or identity not in policy.get('reviewers', []):
        blockers.append('independent_reviewer_required')
    if not bound(review, current) or review.get('decision') != 'approve':
        blockers.append('review_missing_or_stale')
    if review.get('gaps') != []:
        blockers.append('review_gaps')
    artifacts = review.get('artifacts')
    if not isinstance(artifacts, list) or not artifacts or not all(digest(x) for x in artifacts):
        blockers.append('review_artifacts_missing')
    # Verification must be tied to this exact repository/PR and policy revision,
    # not merely to reusable head/base/tree SHAs.
    if not bound(verification, current):
        blockers.append('verification_missing_or_stale')
    if verification.get('gaps') != []:
        blockers.append('verification_gaps')
    required = policy.get('required_checks')
    checks = verification.get('checks')
    if not isinstance(required, dict) or not required or not isinstance(checks, list) or any(
            not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in required.items()):
        blockers.append('checks_policy_or_evidence_missing')
    else:
        for name, producer in required.items():
            matching = [c for c in checks if isinstance(c, dict) and c.get('name') == name]
            if len(matching) != 1 or matching[0].get('producer') != producer or matching[0].get('conclusion') != 'success' or not digest(matching[0].get('artifact')) or not isinstance(artifacts, list) or matching[0].get('artifact') not in artifacts:
                blockers.append('check_failed_or_untrusted:' + name)
    if not all(server.get(name) is True for name in SERVER_FIELDS):
        blockers.append('server_policy_unverified')
    humans = policy.get('humans', [])
    if not bound(authorization, current) or authorization.get('issuer') not in humans:
        blockers.append('human_merge_authorization_required')
    paths = current.get('paths')
    if current.get('paths_complete') is not True or not isinstance(paths, list) or not paths:
        blockers.append('changed_paths_incomplete')
    else:
        for path in paths:
            if not isinstance(path, str) or not path or '\\' in path or path.startswith('/') or ':' in path or any(p in ('', '.', '..') for p in path.split('/')):
                blockers.append('invalid_changed_path')
                continue
            if any(fnmatchcase(path, pattern) for pattern in SENSITIVE):
                human = review.get('human_review')
                if not bound(human, current) or human.get('issuer') not in humans:
                    blockers.append('human_review_required')
    return {'eligible': not blockers, 'blockers': sorted(set(blockers))}
