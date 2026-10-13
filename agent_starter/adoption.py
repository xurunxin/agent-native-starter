"""Selected project adoption: optional tooling is never mistaken for a missing requirement.

This manifest is a file-selection record, not an authorization or security policy.
"""
import json
from pathlib import Path

MANIFEST = Path('.agent-starter/adoption.json')
SCHEMA_VERSION = 1
PROFILES = ('lean', 'full')
PLATFORMS = ('github', 'gitea', 'none')
CORE = frozenset({
    'AGENTS.md', 'CLAUDE.md', 'LESSONS.md', 'agent-project.yaml',
    'docs/engineering.md', 'docs/DOCUMENTATION_POLICY.md',
    'docs/EXPERIENCE_POLICY.md', 'docs/README.md',
    '.agents/skills/implementation/SKILL.md',
    '.agents/skills/learning-loop/SKILL.md',
    '.agents/skills/review-and-merge/SKILL.md',
})
EXCLUSION_REASONS = frozenset({
    'other_platform', 'optional_platform_workflow',
    'optional_in_lean_profile', 'user_not_applicable',
})


def _detect_platform(target):
    """Only use clear local evidence; a self-hosted remote name is not a guess."""
    target = Path(target)
    github = (target / '.github').exists()
    gitea = (target / '.gitea').exists()
    if github != gitea:
        return 'github' if github else 'gitea'
    config = target / '.git' / 'config'
    if not config.is_file() or config.is_symlink() or config.stat().st_size > 128_000:
        return 'none'
    data = config.read_text(encoding='utf-8', errors='replace')
    if 'github.com' in data and 'gitea.' not in data:
        return 'github'
    # Gitea may use any hostname. Require explicit --platform when uncertain.
    return 'none'


def available(entries):
    paths = [p.as_posix() for p, _ in entries]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate bundled path')
    return set(paths)


def _reason(path, profile, platform):
    if path.startswith(('.github/', '.gitea/')):
        host = 'github' if path.startswith('.github/') else 'gitea'
        return 'other_platform' if host != platform else 'optional_platform_workflow'
    return 'optional_in_lean_profile'


def plan(entries, target, *, profile='lean', platform='auto'):
    if profile not in PROFILES or platform not in (*PLATFORMS, 'auto'):
        raise ValueError('Unsupported adoption profile or platform')
    if platform == 'auto':
        platform = _detect_platform(target)
    paths = available(entries)
    missing_core = CORE - paths
    if missing_core:
        raise ValueError('Starter bundle lacks core guidance')
    selected = []
    excluded = {}
    for path in sorted(paths):
        other_platform = ((path.startswith('.github/') and platform != 'github') or
                          (path.startswith('.gitea/') and platform != 'gitea'))
        skill = path.startswith('.agents/skills/')
        minimal_platform = (path.endswith('/ISSUE_TEMPLATE/agent_task.md') or
                            path.endswith('/PULL_REQUEST_TEMPLATE.md')) and path.startswith(
                                '.github/' if platform == 'github' else
                                '.gitea/' if platform == 'gitea' else 'never-match/')
        if not other_platform and (profile == 'full' or path in CORE or skill or minimal_platform):
            selected.append(path)
        else:
            excluded[path] = _reason(path, profile, platform)
    return {'schema_version': SCHEMA_VERSION, 'profile': profile, 'platform': platform,
            'selected': selected, 'excluded': excluded}


def parse_manifest(raw, entries):
    """Reject unknown/stale paths and attempts to exclude core guidance."""
    try:
        manifest = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ValueError('Invalid adoption manifest JSON') from None
    if not isinstance(manifest, dict) or set(manifest) != {
            'schema_version', 'profile', 'platform', 'selected', 'excluded'}:
        raise ValueError('Invalid adoption manifest schema')
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != SCHEMA_VERSION:
        raise ValueError('Unsupported adoption manifest version')
    if manifest['profile'] not in PROFILES or manifest['platform'] not in PLATFORMS:
        raise ValueError('Invalid adoption mode')
    selected, excluded = manifest['selected'], manifest['excluded']
    if (not isinstance(selected, list) or any(not isinstance(p, str) for p in selected)
            or len(selected) != len(set(selected)) or not isinstance(excluded, dict)
            or any(not isinstance(p, str) or reason not in EXCLUSION_REASONS
                   for p, reason in excluded.items())):
        raise ValueError('Invalid selected/excluded paths')
    known = available(entries)
    if (not set(selected).issubset(known) or not set(excluded).issubset(known)
            or set(selected).intersection(excluded) or not CORE.issubset(selected)):
        raise ValueError('Unknown or unsafe adoption selection')
    if any((p.startswith('.github/') and manifest['platform'] != 'github') or
           (p.startswith('.gitea/') and manifest['platform'] != 'gitea') for p in selected):
        raise ValueError('Selected templates belong to another platform')
    return manifest


def render(manifest):
    return (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')


def read(target, entries):
    """Returns None for old projects; caller chooses whether to migrate."""
    path = Path(target) / MANIFEST
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 128_000:
        raise ValueError('Invalid adoption manifest file')
    for parent in path.parents:
        if parent == Path(target):
            break
        if parent.is_symlink():
            raise ValueError('Unsafe adoption manifest parent')
    return parse_manifest(path.read_text(encoding='utf-8'), entries)
