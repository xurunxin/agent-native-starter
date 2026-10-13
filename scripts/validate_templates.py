#!/usr/bin/env python3
"""Zero-dependency checks for bundled skills/template structure.

This script does NOT attest to live GitHub/Gitea branch protection or CI outcomes.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILLS = [
    'project-bootstrap', 'issue-orchestrator', 'implementation',
    'review-and-merge', 'learning-loop',
    'repository-consolidation', 'documentation-curation',
]
REQUIRED = [
    'README.md', 'RESEARCH.md', 'CONTRIBUTING.md', 'SECURITY.md',
    'AGENTS.md', 'agent-project.yaml', 'docs/ROADMAP.md',
    'template/AGENTS.md', 'template/agent-project.yaml',
    'template/docs/engineering.md', 'template/docs/DOCUMENTATION_POLICY.md',
    'template/docs/README.md', 'docs/DOCUMENTATION_POLICY.md', 'docs/README.md',
    'docs/EXPERIENCE_POLICY.md', 'template/docs/EXPERIENCE_POLICY.md',
    'agent_starter/adoption.py',
    'template/.github/ISSUE_TEMPLATE/agent_task.md',
    'template/.github/PULL_REQUEST_TEMPLATE.md',
    'template/.github/workflows/policy.yml',
    'template/.gitea/ISSUE_TEMPLATE/agent_task.md',
    'template/.gitea/PULL_REQUEST_TEMPLATE.md',
    'template/scripts/policy_check.py',
]
errors = [f'Missing: {p}' for p in REQUIRED if not (ROOT / p).is_file()]
for skill in SKILLS:
    path = ROOT / 'skills' / skill / 'SKILL.md'
    if not path.is_file():
        errors.append(f'Missing: {path.relative_to(ROOT)}')
        continue
    data = path.read_text(encoding='utf-8')
    if not data.startswith('---\n') or f'name: {skill}' not in data:
        errors.append(f'Invalid skill frontmatter: {skill}')
    if '## 安全底线' not in data or '## 强制输出' not in data:
        errors.append(f'Incomplete skill policy: {skill}')
for cfg in [ROOT / 'agent-project.yaml', ROOT / 'template' / 'agent-project.yaml']:
    if not cfg.is_file():
        continue
    data = cfg.read_text(encoding='utf-8')
    for snippet in ['auto_merge: false', 'auto_release: false', 'verify_head_sha: true', 'require_isolated_worktree: true']:
        if snippet not in data:
            errors.append(f'Unsafe baseline in {cfg.relative_to(ROOT)}: {snippet}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print('PASS: starter structure and baseline policies present (static checks only).')
