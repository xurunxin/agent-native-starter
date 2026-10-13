import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from agent_starter.bootstrap import initialize


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = self.root / 'project'

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_project_preview_does_not_create_target_and_installs_discoverable_skill(self):
        preview = initialize(self.target, dry_run=True)
        self.assertFalse(self.target.exists())
        self.assertEqual(preview['created'], [])
        self.assertIn('.agents/skills/project-bootstrap/agents/openai.yaml', preview['would_create'])
        self.assertIn('.github/workflows/policy.yml', preview['would_create'])
        applied = initialize(self.target)
        self.assertTrue(applied['ok'])
        self.assertTrue((self.target / '.agents/skills/project-bootstrap/references/workflow.md').is_file())
        self.assertEqual(initialize(self.target)['created'], [])

    def test_existing_project_preserves_user_files_and_never_exports_secret(self):
        self.target.mkdir()
        secret = 'synthetic_private_value_do_not_export'
        keep = {'AGENTS.md': ('user rules ' + secret).encode(),
                'LICENSE': b'user-chosen-license', 'app.py': b'print("user goal")',
                '.github/workflows/policy.yml': ('user CI ' + secret).encode()}
        for name, data in keep.items():
            path = self.target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        subprocess.run(['git', 'init', '-b', 'main', str(self.target)], check=True, capture_output=True)
        before = {p.relative_to(self.target).as_posix(): p.read_bytes()
                  for p in self.target.rglob('*') if p.is_file() and '.git' not in p.relative_to(self.target).parts}
        result = initialize(self.target, dry_run=True)
        after = {p.relative_to(self.target).as_posix(): p.read_bytes()
                 for p in self.target.rglob('*') if p.is_file() and '.git' not in p.relative_to(self.target).parts}
        self.assertEqual(before, after)
        self.assertTrue(result['conflicts'])
        self.assertNotIn(secret, json.dumps(result))
        initialize(self.target)
        for name, data in keep.items():
            self.assertEqual((self.target / name).read_bytes(), data)
        repeated = initialize(self.target)
        self.assertEqual(repeated['created'], [])
        self.assertNotIn(secret, json.dumps(repeated))

    def test_cli_preview_is_nonmutating_and_reports_directory_conflict(self):
        run = subprocess.run([sys.executable, '-m', 'agent_starter', 'init', str(self.target), '--dry-run'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(json.loads(run.stdout)['dry_run'])
        self.assertFalse(self.target.exists())
        self.target.mkdir()
        (self.target / '.github').write_bytes(b'not a directory')
        result = initialize(self.target, dry_run=True)
        self.assertTrue(result['errors'])
        self.assertEqual((self.target / '.github').read_bytes(), b'not a directory')


if __name__ == '__main__':
    unittest.main()
