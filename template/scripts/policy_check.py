#!/usr/bin/env python3
"""Static installed-template checks. Not a substitute for hosted branch protection."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
required = ['AGENTS.md', 'agent-project.yaml', 'docs/engineering.md', 'LESSONS.md',
            'docs/DOCUMENTATION_POLICY.md', 'docs/EXPERIENCE_POLICY.md']
errors = []
adoption_path = root / '.agent-starter/adoption.json'
platform = 'github'  # Legacy full install without a selection manifest.
if adoption_path.exists():
    try:
        record = json.loads(adoption_path.read_text(encoding='utf-8'))
        if record.get('schema_version') != 1 or record.get('platform') not in (
                'github', 'gitea', 'none'):
            raise ValueError('Unsupported manifest')
        platform = record['platform']
    except (ValueError, OSError, TypeError, AttributeError):
        errors.append('Invalid adoption manifest')
required.append('docs/subsystems/README.md')
if platform in ('github', 'gitea'):
    required.append(f'.{platform}/PULL_REQUEST_TEMPLATE.md')
errors.extend(f'Missing file: {item}' for item in required if not (root / item).is_file())
config = (root / 'agent-project.yaml').read_text(encoding='utf-8') if (root / 'agent-project.yaml').is_file() else ''
for fragment in ('auto_merge: false', 'auto_release: false', 'require_isolated_worktree: true',
                 'verify_head_sha: true'):
    if fragment not in config:
        errors.append(f'Unsafe/missing policy: {fragment}')
if 'CHANGE_ME' in config:
    print('WARNING: fill project configuration placeholders')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print('PASS: static policy check only. Verify live CI and protected branch independently.')
