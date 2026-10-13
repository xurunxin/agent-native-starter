import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from agent_starter.evaluation import compare, compare_replicates, validate_lesson, promotion
from agent_starter.task_runs import digest


def run(success=True, tokens=None):
    return {'dataset_digest': 'a'*64, 'environment': {'runner': 'unittest', 'python': '3.13'},
            'rules_digest': 'b'*64, 'implementation_digest': 'c'*64, 'source_sha': 'd'*40, 'source_dirty': False,
            'cases': [{'id': 'case1', 'category': 'init', 'status': 'PASS' if success else 'FAIL',
                       'seconds': 1.0, 'tokens': tokens, 'cost_usd': None}]}

def observed(arm, index, success=True, *, kind='observed_task_run', implementation='c'*64):
    case = {'id': 'task', 'category': 'implementation', 'run_id': f'{arm}-{index}',
            'input_sha256': 'f'*64, 'status': 'PASS' if success else 'FAIL',
            'seconds': 4.0, 'errors': 0 if success else 1,
            'usage': {'input_tokens': 20, 'cached_input_tokens': 8,
                      'output_tokens': 5, 'total_tokens': 25, 'cost_usd': None},
            'tokens': 25, 'cost_usd': None}
    report = {
        'source_sha': ('a' if arm == 'baseline' else 'b')*40,
        'source_dirty': False, 'dataset_digest': 'd'*64,
        'rules_digest': ('a' if arm == 'baseline' else 'b')*64,
        'implementation_digest': implementation,
        'environment': {'runner': 'trusted-runner', 'measurement_kind': kind,
                        'model': 'same-model', 'parameters': {}},
        'evidence_kind': 'instrumented_task_import',
        'cases': [case]
    }
    report['report_digest'] = digest(report)
    return report


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

    def test_actual_paired_trials_report_observations_without_causal_claims(self):
        pairs = [(observed('baseline', i, success=False), observed('candidate', i))
                 for i in (1, 2)]
        report = compare_replicates(pairs)
        self.assertEqual(report['status'], 'RECORDED')
        self.assertEqual(report['paired_trials'], 2)
        self.assertEqual(report['baseline']['failed'], 2)
        self.assertEqual(report['candidate']['passed'], 2)
        self.assertEqual(report['candidate']['usage']['cached_input_tokens'], 16)
        self.assertEqual(report['candidate']['usage']['cost_usd'], 'NOT_MEASURED')
        self.assertEqual(report['causal_effect'], 'NOT_ESTABLISHED')

    def test_paired_trials_do_not_treat_single_run_as_complete(self):
        result = compare_replicates([(observed('baseline', 1), observed('candidate', 1))])
        self.assertEqual(result['status'], 'INCOMPLETE')

    def test_duplicate_or_incomparable_trials_are_rejected(self):
        one = (observed('baseline', 1), observed('candidate', 1))
        with self.assertRaises(ValueError):
            compare_replicates([one, one])
        for altered in (
            observed('candidate', 2, kind='synthetic_fixture'),
            observed('candidate', 2, implementation='e'*64),
            observed('candidate', 2),
        ):
            candidate = altered
            if candidate['environment']['measurement_kind'] == 'observed_task_run' and (
                    candidate['implementation_digest'] == 'c'*64):
                candidate['rules_digest'] = 'e'*64
                candidate['report_digest'] = digest({k: v for k, v in candidate.items()
                                                     if k != 'report_digest'})
            with self.assertRaises(ValueError):
                compare_replicates([one, (observed('baseline', 2), candidate)])

    def test_replicates_cli_reads_only_explicit_reports_and_keeps_output(self):
        with tempfile.TemporaryDirectory() as root:
            paths = []
            for index in (1, 2):
                pair = []
                for arm in ('baseline', 'candidate'):
                    file = Path(root) / f'{arm}-{index}.json'
                    file.write_text(json.dumps(observed(arm, index)), encoding='utf-8')
                    pair.append(file)
                paths.extend(pair)
            output = Path(root) / 'summary.json'
            command = [sys.executable, '-m', 'agent_starter.evaluation', 'replicates']
            for left, right in (paths[:2], paths[2:]):
                command += ['--pair', str(left), str(right)]
            command += ['--output', str(output)]
            run = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(output.read_text())['status'], 'RECORDED')
            again = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(again.returncode, 0)  # exclusive output is immutable

    def test_offline_contract_results_cannot_be_counted_as_actual_trials(self):
        with self.assertRaises(ValueError):
            compare_replicates([(run(), run())])
        with self.assertRaises(ValueError):
            compare_replicates([(observed('baseline', 1, kind='synthetic_fixture'),
                                 observed('candidate', 1, kind='synthetic_fixture'))])

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
