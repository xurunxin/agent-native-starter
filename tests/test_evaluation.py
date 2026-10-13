import unittest

from agent_starter.evaluation import compare, validate_lesson, promotion


def run(success=True, tokens=None):
    return {'dataset_digest': 'a'*64, 'environment': {'runner': 'unittest', 'python': '3.13'},
            'rules_digest': 'b'*64, 'implementation_digest': 'c'*64, 'source_sha': 'd'*40, 'source_dirty': False,
            'cases': [{'id': 'case1', 'category': 'init', 'status': 'PASS' if success else 'FAIL',
                       'seconds': 1.0, 'tokens': tokens, 'cost_usd': None}]}


class EvaluationTests(unittest.TestCase):
    def test_same_cases_compare_success_errors_and_unknown_costs(self):
        r = compare(run(False), run())
        self.assertEqual(r['baseline']['success_rate'], 0)
        self.assertEqual(r['candidate']['success_rate'], 1)
        self.assertEqual(r['baseline']['error_rate'], 1)
        self.assertEqual(r['candidate']['tokens'], 'NOT_MEASURED')
        self.assertEqual(r['candidate']['cost_usd'], 'NOT_MEASURED')
        self.assertFalse(r['rules_changed'])

    def test_dirty_or_unknown_source_cannot_be_compared_as_clean(self):
        for dirty in (True, None):
            candidate = run()
            candidate['source_dirty'] = dirty
            with self.assertRaises(ValueError):
                compare(run(), candidate)
        candidate = run()
        del candidate['source_dirty']
        with self.assertRaises(ValueError):
            compare(run(), candidate)

    def test_incomparable_runs_are_rejected(self):
        for field, value in (('dataset_digest', 'x'), ('environment', {'runner': 'other'})):
            candidate = run()
            candidate[field] = value
            with self.assertRaises(ValueError):
                compare(run(), candidate)
        candidate = run()
        candidate['cases'][0]['id'] = 'another'
        with self.assertRaises(ValueError):
            compare(run(), candidate)

    def test_not_run_excluded_and_missing_metrics_never_zero(self):
        a, b = run(tokens=10), run(tokens=20)
        for report in (a, b):
            report['cases'].append({'id': 'live-gate', 'category': 'governance', 'status': 'NOT_RUN',
                                    'seconds': None, 'tokens': None, 'cost_usd': None})
        result = compare(a, b)
        self.assertEqual(result['candidate']['measured'], 1)
        self.assertEqual(result['candidate']['tokens'], 20)
        self.assertEqual(result['candidate']['not_run'], ['live-gate'])

    def test_invalid_results_and_duplicate_ids_rejected(self):
        for field, value in (('tokens', -1), ('seconds', float('nan')), ('status', 'maybe')):
            candidate = run()
            candidate['cases'][0][field] = value
            with self.assertRaises(ValueError):
                compare(run(), candidate)
        candidate = run()
        candidate['cases'].append(candidate['cases'][0])
        with self.assertRaises(ValueError):
            compare(run(), candidate)

    def test_lesson_requires_root_cause_evidence_reproduction_and_scope(self):
        lesson = dict(root_cause='missing effective server protection', evidence=['issue#7'],
                      reproduction=['read rulesets and branch protection'], scope='GitHub main',
                      prevention='verify effective policy', checks=['live-gate'],
                      observed='2026-10-13', review_after='2027-01-13')
        self.assertEqual(validate_lesson(lesson), [])
        self.assertEqual(promotion(lesson, compare(run(False), run()), security_boundary=True),
                         'human_review_required')
        self.assertEqual(promotion(lesson, compare(run(False), run())), 'draft_pr_required')
        del lesson['root_cause']
        self.assertIn('root_cause', validate_lesson(lesson))
        self.assertEqual(promotion(lesson, compare(run(False), run())), 'insufficient_evidence')


if __name__ == '__main__':
    unittest.main()
