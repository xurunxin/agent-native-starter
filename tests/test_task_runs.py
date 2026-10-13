from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from agent_starter.evaluation import compare
from agent_starter.task_runs import canonical, digest, freeze_rules, import_results, usage


class TaskRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / 'repo'
        self.project.mkdir()
        self.counter = 0
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.project / 'AGENTS.md').write_bytes(b'fixture governance')
        self.skill = self.project / 'skills/fixture/SKILL.md'
        self.skill.parent.mkdir(parents=True)
        self.skill.write_bytes(b'baseline fixture rules')
        self.git('add', '.')
        self.git('commit', '-m', 'baseline')
        self.baseline = freeze_rules(self.project)
        self.skill.write_bytes(b'candidate fixture rules')
        self.git('add', '.')
        self.git('commit', '-m', 'candidate')
        self.candidate = freeze_rules(self.project)
        self.input = b'synthetic sensitive input; never an actual private repository'
        self.suite = {'schema_version': 1, 'tasks': [{'id': 'adoption-preserve', 'category': 'bootstrap',
                       'input_sha256': hashlib.sha256(self.input).hexdigest()}]}
        self.env = {'runner': 'fixture-runner', 'version': '1', 'provider': 'fixture', 'model': 'fixture-model',
                    'parameters': {'seed': 1}, 'measurement_kind': 'synthetic_fixture'}

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.project), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def results(self, snapshot, tokens=10, success=True, unknown=False):
        self.counter += 1
        run_id = 'fixture-run-' + str(self.counter)
        root = self.root / run_id
        root.mkdir()
        header = {k: snapshot[k] for k in ('source_sha', 'rules_digest', 'snapshot_digest')}
        header['dataset_digest'] = digest(self.suite)
        binding = {**header, 'task_id': 'adoption-preserve', 'run_id': run_id,
                   'input_sha256': self.suite['tasks'][0]['input_sha256']}
        usage = dict(input_tokens=tokens, output_tokens=5, total_tokens=tokens + 5, cost_usd=0.00002)
        if unknown:
            usage = {key: None for key in usage}
        status, errors = ('PASS', 0) if success else ('FAIL', 1)
        payloads = {'input': self.input, 'output': b'synthetic output; not an actual model response',
                    'verification': canonical({'binding': binding, 'status': status, 'seconds': 1.0, 'errors': errors}),
                    'usage': canonical({'binding': binding, 'environment': self.env, 'usage': usage})}
        artifacts = {}
        for name, raw in payloads.items():
            filename = name + '.json' if name in ('verification', 'usage') else name + '.txt'
            (root / filename).write_bytes(raw)
            artifacts[name] = {'path': filename, 'sha256': hashlib.sha256(raw).hexdigest()}
        result = {'schema_version': 1, **header, 'environment': deepcopy(self.env),
                  'cases': [{'id': 'adoption-preserve', 'run_id': run_id, 'input_sha256': binding['input_sha256'],
                             'status': status, 'seconds': 1.0, 'errors': errors, 'usage': usage, 'artifacts': artifacts}]}
        return result, root

    def test_same_scenario_different_frozen_rules_and_instrumented_fixture_metrics(self):
        old, a = self.results(self.baseline, success=False)
        new, b = self.results(self.candidate, tokens=20)
        baseline = import_results(self.project, self.baseline, self.suite, old, a)
        candidate = import_results(self.project, self.candidate, self.suite, new, b)
        comparison = compare(baseline, candidate)
        self.assertTrue(comparison['rules_changed'])
        self.assertFalse(comparison['implementation_changed'])
        self.assertEqual(comparison['candidate']['tokens'], 25)
        self.assertEqual(comparison['measurement_kind'], 'synthetic_fixture')
        self.assertNotIn(self.input.decode(), json.dumps(candidate))
        self.assertEqual(candidate['results_digest'], digest(new))

    def test_snapshot_source_and_rule_tampering_are_rejected(self):
        result, root = self.results(self.candidate)
        for field in ('rules_digest', 'snapshot_digest', 'source_sha'):
            modified = deepcopy(self.candidate)
            modified[field] = 'f' * len(modified[field])
            with self.assertRaises(ValueError):
                import_results(self.project, modified, self.suite, result, root)

    def test_installed_skills_metadata_references_and_engineering_are_frozen(self):
        before = freeze_rules(self.project)
        paths = ['.agents/skills/adoption/SKILL.md', '.agents/skills/adoption/agents/openai.yaml',
                 '.agents/skills/adoption/references/workflow.md', 'CLAUDE.md', 'docs/engineering.md']
        for name in paths:
            path = self.project / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('installed rule evidence', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-m', 'install project rules')
        installed = freeze_rules(self.project)
        self.assertTrue(set(paths).issubset({item['path'] for item in installed['rules_files']}))
        self.assertNotEqual(before['rules_digest'], installed['rules_digest'])
        self.assertEqual(before['implementation_digest'], installed['implementation_digest'])
        path = self.project / paths[2]
        path.write_text('changed workflow', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-m', 'change installed workflow')
        self.assertNotEqual(installed['rules_digest'], freeze_rules(self.project)['rules_digest'])

    def test_raw_artifact_tampering_and_path_escape_are_rejected(self):
        result, root = self.results(self.candidate)
        (root / 'output.txt').write_bytes(b'changed output')
        with self.assertRaises(ValueError):
            import_results(self.project, self.candidate, self.suite, result, root)
        result, root = self.results(self.candidate)
        result['cases'][0]['artifacts']['output']['path'] = '../outside.txt'
        with self.assertRaises(ValueError):
            import_results(self.project, self.candidate, self.suite, result, root)

    def test_usage_and_outcome_cannot_be_edited_without_matching_receipts(self):
        for field, value in (('status', 'FAIL'), ('seconds', 9.0), ('errors', 2)):
            result, root = self.results(self.candidate)
            result['cases'][0][field] = value
            with self.assertRaises(ValueError):
                import_results(self.project, self.candidate, self.suite, result, root)
        result, root = self.results(self.candidate)
        result['cases'][0]['usage']['cost_usd'] = 999
        with self.assertRaises(ValueError):
            import_results(self.project, self.candidate, self.suite, result, root)

    def test_cached_tokens_optional_but_never_fabricated(self):
        old = {'input_tokens': 20, 'output_tokens': 5, 'total_tokens': 25, 'cost_usd': None}
        self.assertNotIn('cached_input_tokens', usage(old))
        self.assertEqual(usage({**old, 'cached_input_tokens': 12})['cached_input_tokens'], 12)
        for invalid in (21, -1, 1.5):
            with self.assertRaises(ValueError):
                usage({**old, 'cached_input_tokens': invalid})

    def test_unknown_costs_and_token_counts_remain_unknown(self):
        result, root = self.results(self.candidate, unknown=True)
        report = import_results(self.project, self.candidate, self.suite, result, root)
        comparison = compare(report, report)
        self.assertEqual(comparison['candidate']['tokens'], 'NOT_MEASURED')
        self.assertEqual(comparison['candidate']['cost_usd'], 'NOT_MEASURED')

    def test_imported_metric_digest_detects_edits_before_comparison(self):
        result, root = self.results(self.candidate)
        report = import_results(self.project, self.candidate, self.suite, result, root)
        modified = deepcopy(report)
        modified['cases'][0]['tokens'] = 999
        with self.assertRaises(ValueError):
            compare(report, modified)

    def test_coverage_environment_and_dirty_source_require_consistency(self):
        result, root = self.results(self.candidate)
        bad = deepcopy(result)
        bad['cases'].append(deepcopy(bad['cases'][0]))
        with self.assertRaises(ValueError):
            import_results(self.project, self.candidate, self.suite, bad, root)
        bad = deepcopy(result)
        bad['environment']['model'] = 'another-model'
        with self.assertRaises(ValueError):
            import_results(self.project, self.candidate, self.suite, bad, root)
        (self.project / 'AGENTS.md').write_bytes(b'uncommitted fixture')
        with self.assertRaises(ValueError):
            freeze_rules(self.project)

    def test_not_run_must_not_claim_zero_cost_or_tokens(self):
        result, root = self.results(self.candidate, unknown=True)
        case = result['cases'][0]
        case.update(status='NOT_RUN', seconds=None, errors=None, artifacts={}, reason='not_authorized')
        report = import_results(self.project, self.candidate, self.suite, result, root)
        self.assertEqual(compare(report, report)['candidate']['measured'], 0)
        case['usage']['total_tokens'] = 0
        with self.assertRaises(ValueError):
            import_results(self.project, self.candidate, self.suite, result, root)

    def test_cli_freezes_and_imports_without_executing_a_model(self):
        result, root = self.results(self.candidate)
        paths = {'snapshot': self.candidate, 'suite': self.suite, 'results': result}
        for name, value in paths.items():
            (self.root / (name + '.json')).write_bytes(canonical(value))
        frozen = self.root / 'cli-snapshot.json'
        run = subprocess.run([sys.executable, '-m', 'agent_starter.task_runs', 'freeze', str(self.project),
                              '--output', str(frozen)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(frozen.read_text())['rules_digest'], self.candidate['rules_digest'])
        output = self.root / 'report.json'
        run = subprocess.run([sys.executable, '-m', 'agent_starter.task_runs', 'import', str(self.project),
                              '--snapshot', str(self.root / 'snapshot.json'), '--suite', str(self.root / 'suite.json'),
                              '--results', str(self.root / 'results.json'), '--artifacts', str(root), '--output', str(output)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['measurement_kind'], 'synthetic_fixture')
        self.assertTrue(output.exists())


if __name__ == '__main__':
    unittest.main()
