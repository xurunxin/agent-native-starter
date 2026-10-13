import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_starter.bootstrap import initialize, doctor


class AdoptionProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'target'

    def tearDown(self):
        self.tmp.cleanup()

    def manifest_path(self):
        return self.root / '.agent-starter/adoption.json'

    def test_default_lean_preview_is_nonwriting_and_installs_guidance(self):
        preview = initialize(self.root, dry_run=True)
        self.assertFalse(self.root.exists())
        self.assertEqual(preview['adoption']['profile'], 'lean')
        self.assertEqual(preview['adoption']['platform'], 'none')
        self.assertIn('docs/EXPERIENCE_POLICY.md', preview['would_create'])
        self.assertIn('.agent-starter/adoption.json', preview['would_create'])
        self.assertIn('.github/workflows/policy.yml', preview['adoption']['excluded'])
        self.assertNotIn('.github/workflows/policy.yml', preview['would_create'])
        installed = initialize(self.root)
        self.assertTrue(installed['ok'])
        self.assertTrue((self.root / '.agents/skills/learning-loop/SKILL.md').is_file())
        self.assertTrue((self.root / 'AGENTS.md').is_file())
        self.assertTrue((self.root / 'LESSONS.md').is_file())
        self.assertFalse((self.root / '.github/workflows/policy.yml').exists())
        self.assertEqual(initialize(self.root)['created'], [])
        status = doctor(self.root)
        self.assertNotIn('.github/workflows/policy.yml', status['missing'])
        self.assertIn('.github/workflows/policy.yml', status['adoption']['excluded'])
        self.assertIn('verification_NOT_RUN', status['gaps'])
        self.assertFalse(status['ok'])

    def test_full_gitea_selection_and_deleted_selected_file(self):
        init = initialize(self.root, profile='full', platform='gitea')
        self.assertTrue(init['ok'])
        self.assertTrue((self.root / '.gitea/PULL_REQUEST_TEMPLATE.md').is_file())
        self.assertFalse((self.root / '.github/PULL_REQUEST_TEMPLATE.md').exists())
        self.assertTrue((self.root / 'scripts/policy_check.py').is_file())
        (self.root / '.gitea/PULL_REQUEST_TEMPLATE.md').unlink()
        status = doctor(self.root)
        self.assertIn('.gitea/PULL_REQUEST_TEMPLATE.md', status['missing'])
        self.assertNotIn('.github/PULL_REQUEST_TEMPLATE.md', status['missing'])
        self.assertEqual(status['adoption']['profile'], 'full')
        self.assertIn('.github/PULL_REQUEST_TEMPLATE.md', status['adoption']['excluded'])
        self.assertFalse(status['ok'])

    def test_github_lean_does_not_create_ci_and_gitea_files(self):
        r = initialize(self.root, platform='github')
        self.assertTrue(r['ok'])
        self.assertTrue((self.root / '.github/PULL_REQUEST_TEMPLATE.md').exists())
        self.assertTrue((self.root / '.github/ISSUE_TEMPLATE/agent_task.md').exists())
        self.assertFalse((self.root / '.github/workflows/policy.yml').exists())
        self.assertFalse((self.root / '.gitea/PULL_REQUEST_TEMPLATE.md').exists())
        self.assertEqual(json.loads(self.manifest_path().read_text())['platform'], 'github')

    def test_auto_detects_only_unambiguous_existing_platform(self):
        (self.root / '.gitea').mkdir(parents=True)
        result = initialize(self.root)
        self.assertEqual(result['adoption']['platform'], 'gitea')
        self.assertTrue((self.root / '.gitea/PULL_REQUEST_TEMPLATE.md').is_file())

    def test_broken_manifest_and_unknown_path_fail_closed(self):
        initialize(self.root)
        original = json.loads(self.manifest_path().read_text())
        for mutate in (
            lambda o: o.update(schema_version=999),
            lambda o: o['excluded'].update({'never-existed.md': 'mistake'}),
            lambda o: o['excluded'].update({'.github/workflows/policy.yml': 'unsafe custom text'}),
            lambda o: (o['selected'].remove('AGENTS.md'),
                       o['excluded'].update({'AGENTS.md': 'cannot bypass core'})),
        ):
            doc = json.loads(json.dumps(original))
            mutate(doc)
            self.manifest_path().write_text(json.dumps(doc))
            report = doctor(self.root)
            self.assertIn('invalid_adoption_manifest', report['gaps'])
            self.assertFalse(report['ok'])
            with self.assertRaises(ValueError):
                initialize(self.root)
        self.manifest_path().write_text(json.dumps(original))
        self.assertEqual(initialize(self.root)['created'], [])

    def test_manual_reviewed_exclusion_preserves_manifest_without_reformatting(self):
        initialize(self.root, profile='full', platform='github')
        manifest = json.loads(self.manifest_path().read_text())
        chosen = '.github/workflows/policy.yml'
        manifest['selected'].remove(chosen)
        manifest['excluded'][chosen] = 'user_not_applicable'
        # Deliberately choose noncanonical formatting. An init cannot rewrite it.
        original = json.dumps(manifest, separators=(',', ':'))
        self.manifest_path().write_text(original)
        (self.root / chosen).unlink()
        again = initialize(self.root)
        self.assertTrue(again['ok'])
        self.assertEqual(self.manifest_path().read_text(), original)
        report = doctor(self.root)
        self.assertNotIn(chosen, report['missing'])
        self.assertEqual(report['adoption']['excluded'][chosen], 'user_not_applicable')

    def test_profile_change_requires_explicit_review_and_has_no_side_effect(self):
        initialize(self.root)
        original = self.manifest_path().read_bytes()
        with self.assertRaises(ValueError):
            initialize(self.root, profile='full')
        self.assertEqual(self.manifest_path().read_bytes(), original)
        self.assertFalse((self.root / 'scripts/policy_check.py').exists())

    def test_existing_project_preserves_agreement_and_does_not_export_secret(self):
        self.root.mkdir()
        secret = 'do_not_leak_secret'
        (self.root / 'AGENTS.md').write_text('keep ' + secret)
        (self.root / '.github').mkdir()
        (self.root / '.github/workflows').mkdir()
        (self.root / '.github/workflows/ci.yml').write_text('custom')
        result = initialize(self.root, dry_run=True)
        self.assertEqual(result['adoption']['platform'], 'github')
        self.assertEqual(result['created'], [])
        self.assertIn('AGENTS.md', [x['path'] for x in result['conflicts']])
        self.assertNotIn(secret, json.dumps(result))
        result = initialize(self.root)
        self.assertFalse(result['ok'])  # Human review must integrate original AGENTS.
        self.assertEqual((self.root / 'AGENTS.md').read_text(), 'keep ' + secret)
        self.assertEqual((self.root / '.github/workflows/ci.yml').read_text(), 'custom')
        self.assertNotIn(secret, json.dumps(result))

    def test_cli_full_explicit_and_legacy_doctor(self):
        result = subprocess.run(
            [sys.executable, '-m', 'agent_starter', 'init', str(self.root),
             '--profile', 'full', '--platform', 'gitea', '--dry-run'],
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['adoption']['profile'], 'full')
        self.assertFalse(self.root.exists())
        self.root.mkdir()
        report = doctor(self.root)
        self.assertEqual(report['adoption']['status'], 'legacy_no_manifest')
        self.assertTrue(report['missing'])


if __name__ == '__main__':
    unittest.main()
