from copy import deepcopy
import unittest

from agent_starter.review import assess


def fixture():
    current = dict(repository='o/r', pr=1, implementer='implementer-session', head='a'*40,
                   base='b'*40, tree='c'*40, draft=False, paths=['README.md'],
                   paths_complete=True, policy_digest='d'*64)
    review = dict(repository='o/r', pr=1, reviewer='reviewer-session', head=current['head'],
                  base=current['base'], tree=current['tree'], policy_digest=current['policy_digest'],
                  decision='approve', gaps=[], artifacts=['e'*64])
    verification = dict(head=current['head'], base=current['base'], tree=current['tree'], gaps=[],
                        checks=[dict(name='validate', producer='trusted-ci', conclusion='success',
                                     artifact='e'*64)])
    policy = dict(auto_merge=False, reviewers=['reviewer-session'], humans=['maintainer'],
                  required_checks={'validate': 'trusted-ci'}, digest=current['policy_digest'])
    server = dict(pr_required=True, no_force_push=True, no_delete=True, required_checks=True,
                  independent_approval=True, stale_approval_dismissal=True, code_owner_review=True,
                  strict_base=True, bypass_audited=True, enforced=True)
    authorization = dict(issuer='maintainer', repository='o/r', pr=1,
                         head=current['head'], base=current['base'], tree=current['tree'],
                         policy_digest=current['policy_digest'])
    return current, review, verification, policy, server, authorization


class ReviewTests(unittest.TestCase):
    def test_low_risk_evidence_protocol_positive_case(self):
        self.assertTrue(assess(*fixture())['eligible'])

    def test_every_version_change_invalidates_old_evidence(self):
        for field in ('head', 'base', 'tree', 'policy_digest'):
            data = list(fixture())
            data[0][field] = 'f' * len(data[0][field])
            self.assertFalse(assess(*data)['eligible'], field)

    def test_no_self_approval_or_unknown_reviewer(self):
        for identity in ('implementer-session', 'random'):
            data = list(fixture())
            data[1]['reviewer'] = identity
            self.assertFalse(assess(*data)['eligible'])

    def test_failed_missing_or_forged_check_blocks(self):
        for change in ({'conclusion': 'failure'}, {'producer': 'unknown'}, {'artifact': ''}, {'artifact': 'f'*64}):
            data = list(fixture())
            data[2]['checks'][0].update(change)
            self.assertFalse(assess(*data)['eligible'])
        data = list(fixture())
        data[2]['checks'] = []
        self.assertFalse(assess(*data)['eligible'])

    def test_protection_unknown_draft_and_auto_merge_block(self):
        for index, field in ((4, 'enforced'), (4, 'bypass_audited'), (4, 'strict_base')):
            data = list(fixture())
            data[index][field] = False
            self.assertFalse(assess(*data)['eligible'])
        data = list(fixture())
        data[0]['draft'] = True
        self.assertFalse(assess(*data)['eligible'])
        data = list(fixture())
        data[3]['auto_merge'] = True
        self.assertFalse(assess(*data)['eligible'])

    def test_sensitive_paths_require_bound_human_review(self):
        for path in ('AGENTS.md', '.github/workflows/ci.yml', 'skills/implementation/SKILL.md',
                     'agent_starter/review.py', 'template/AGENTS.md'):
            data = list(fixture())
            data[0]['paths'] = [path]
            self.assertIn('human_review_required', assess(*data)['blockers'])
            data[1]['human_review'] = deepcopy(data[5])
            self.assertTrue(assess(*data)['eligible'])

    def test_missing_authorization_incomplete_paths_and_gaps_block(self):
        data = list(fixture())
        data[5] = None
        self.assertFalse(assess(*data)['eligible'])
        for index, field, value in ((0, 'paths_complete', False), (1, 'gaps', ['NOT_RUN']),
                                    (2, 'gaps', ['missing integration']), (0, 'paths', ['../AGENTS.md'])):
            data = list(fixture())
            data[index][field] = value
            self.assertFalse(assess(*data)['eligible'])

    def test_no_schema_defaults_can_turn_absent_evidence_into_success(self):
        self.assertFalse(assess({}, {}, {}, {}, {}, None)['eligible'])
        data = list(fixture())
        data[3]['required_checks'] = {}
        self.assertFalse(assess(*data)['eligible'])
        data = list(fixture())
        data[3]['humans'] = None
        self.assertFalse(assess(*data)['eligible'])


if __name__ == '__main__':
    unittest.main()
