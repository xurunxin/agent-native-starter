import subprocess
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_starter.bootstrap import initialize, doctor, upgrade


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.target = self.root / 'target'
        self.source.mkdir()
        self.target.mkdir()
        (self.source / 'AGENTS.md').write_text('new rules\n')
        (self.source / 'agent-project.yaml').write_text('project:\n  default_branch: main\n')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.target), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def test_existing_and_repeated_init_never_overwrites(self):
        (self.target / 'AGENTS.md').write_text('custom rules\n')
        r = initialize(self.target, self.source)
        self.assertEqual((self.target / 'AGENTS.md').read_text(), 'custom rules\n')
        self.assertEqual(r['conflicts'][0]['change']['old_sha256'],
                         hashlib.sha256(b'custom rules\n').hexdigest())
        self.assertEqual(r['conflicts'][0]['change']['new_sha256'],
                         hashlib.sha256(b'new rules\n').hexdigest())
        self.assertFalse(r['conflicts'][0]['change']['content_included'])
        self.assertNotIn('custom rules', json.dumps(r))
        self.assertEqual(initialize(self.target, self.source)['created'], [])

    def test_secret_in_existing_config_never_leaks_to_init_or_upgrade_reports(self):
        secret = 'private_token_very_sensitive'
        (self.target / 'agent-project.yaml').write_text('token: ' + secret + '\n')
        initial = initialize(self.target, self.source)
        self.assertNotIn(secret, json.dumps(initial))
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        self.git('add', '.')
        self.git('commit', '-m', 'config')
        proposal = upgrade(self.target, self.source, 'review-proposal')
        self.assertNotIn(secret, json.dumps(proposal))
        report = (self.target / '.agent-starter-upgrade' / 'proposal.json').read_text()
        self.assertNotIn(secret, report)

    def test_bundled_cli_installs_skills_and_hidden_templates(self):
        for _ in range(2):
            run = subprocess.run(['python', '-m', 'agent_starter', 'init', str(self.target)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(json.loads(run.stdout)['ok'])
        self.assertTrue((self.target / '.agents/skills/implementation/SKILL.md').is_file())
        self.assertTrue((self.target / '.gitea/PULL_REQUEST_TEMPLATE.md').is_file())

    def test_permission_failure_is_reported(self):
        original = Path.open
        def deny(path, *args, **kwargs):
            if path.parent == self.target and args and args[0] == 'xb':
                raise PermissionError('denied')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', deny):
            result = initialize(self.target, self.source)
        self.assertTrue(result['errors'])
        self.assertFalse((self.target / 'AGENTS.md').exists())

    def test_symlink_source_rejected(self):
        # Portable simulation covers hosts without symlink creation privileges.
        real = Path.is_symlink
        with patch.object(Path, 'is_symlink', lambda p: p.name == 'AGENTS.md' or real(p)):
            with self.assertRaises(ValueError):
                initialize(self.target, self.source)

    def test_doctor_runs_only_explicit_commands_and_reports_gaps(self):
        result = doctor(self.target, self.source, verify=[['python', '-c', 'raise SystemExit(2)']])
        self.assertIn('AGENTS.md', result['missing'])
        self.assertEqual(result['verification'][0]['exit_code'], 2)
        self.assertEqual(result['platform'], 'NOT_RUN')
        self.assertFalse(result['ok'])

    def test_upgrade_requires_clean_git_and_proposes_in_branch(self):
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.target / 'AGENTS.md').write_text('custom rules\n')
        self.git('add', '.')
        self.git('commit', '-m', 'baseline')
        result = upgrade(self.target, self.source, 'proposal')
        self.assertEqual(self.git('branch', '--show-current'), 'proposal')
        self.assertEqual((self.target / 'AGENTS.md').read_text(), 'custom rules\n')
        self.assertTrue((self.target / '.agent-starter-upgrade' / 'proposal.json').exists())
        self.assertEqual(result['status'], 'proposal_only')
        with self.assertRaises(ValueError):
            upgrade(self.target, self.source, 'other')

    def test_upgrade_rejects_dirty_tree_before_branch_creation(self):
        self.git('init', '-b', 'main')
        (self.target / 'untracked').write_text('mine')
        with self.assertRaises(ValueError):
            upgrade(self.target, self.source, 'proposal')
        self.assertEqual(self.git('branch', '--show-current'), 'main')


if __name__ == '__main__':
    unittest.main()
