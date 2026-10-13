"""Non-overwriting initialization and branch-only upgrade proposals."""
import hashlib
import json
from pathlib import Path
import re
import subprocess


BUNDLE = Path(__file__).resolve().parents[1] / 'template'


def files(source):
    source = Path(source).resolve()
    if not source.is_dir() or not any(source.iterdir()):
        raise ValueError('Template source must be a nonempty directory')
    for path in sorted(source.rglob('*')):
        if path.is_symlink() or path.is_junction():
            raise ValueError('Template symlinks are prohibited')
        if path.is_file():
            yield path.relative_to(source), path.read_bytes()
    if source == BUNDLE:
        skills = BUNDLE.parent / 'skills'
        for path in sorted(skills.rglob('*')):
            if path.is_symlink() or path.is_junction():
                raise ValueError('Skill links are prohibited')
            if path.is_file():
                yield Path('.agents/skills') / path.relative_to(skills), path.read_bytes()


def destination(root, relative):
    path = root / relative
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink() or part.is_junction():
            raise ValueError('Target symlinks/junctions are prohibited')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Target escapes project root')
    return path


def difference(relative, old, new):
    """Do not export existing project contents to CLI output or proposal.json.

    A pre-existing governance/CI file may contain a credential. Content diffs
    are intentionally left for a trusted human reviewing the local files.
    """
    return {'old_sha256': hashlib.sha256(old).hexdigest(),
            'new_sha256': hashlib.sha256(new).hexdigest(),
            'content_included': False}


def initialize(target, source=BUNDLE):
    target = Path(target).resolve()
    # Validate the whole source first, before creating target files.
    entries = list(files(source))
    target.mkdir(parents=True, exist_ok=True)
    result = {'created': [], 'unchanged': [], 'conflicts': [], 'errors': []}
    for relative, data in entries:
        try:
            path = destination(target, relative)
            if path.exists():
                old = path.read_bytes()
                if old == data:
                    result['unchanged'].append(relative.as_posix())
                else:
                    result['conflicts'].append({'path': relative.as_posix(),
                                                'change': difference(relative, old, data)})
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(data)
            result['created'].append(relative.as_posix())
        except (OSError, ValueError) as e:
            # Paths are useful, OS exception text may contain sensitive content.
            result['errors'].append({'path': relative.as_posix(), 'code': type(e).__name__})
    result['ok'] = not result['conflicts'] and not result['errors']
    return result


def git(target, *args):
    result = subprocess.run(['git', '-C', str(target), *args], capture_output=True,
                            text=True, timeout=30)
    if result.returncode:
        raise ValueError('Git operation failed: ' + args[0])
    return result.stdout.strip()


def doctor(target, source=BUNDLE, *, verify=(), provider=None):
    target = Path(target).resolve()
    expected = list(files(source))
    result = {'missing': [], 'default_branch': None, 'verification': [],
              'platform': 'NOT_RUN', 'gaps': []}
    for relative, _ in expected:
        try:
            if not destination(target, relative).is_file():
                result['missing'].append(relative.as_posix())
        except ValueError:
            result['gaps'].append('unsafe_target:' + relative.as_posix())
    config = destination(target, Path('agent-project.yaml'))
    text = config.read_text(encoding='utf-8') if config.is_file() else ''
    if 'CHANGE_ME' in text or 'owner/repo' in text:
        result['gaps'].append('unconfigured_template')
    for value in ('auto_merge: false', 'auto_release: false', 'verify_head_sha: true',
                  'require_isolated_worktree: true'):
        if not re.search(r'^\s*' + re.escape(value) + r'\s*(?:#.*)?$', text, re.MULTILINE):
            result['gaps'].append('missing_safe_default:' + value)
    if provider is not None:
        from .provider import ProviderError
        result['platform'] = {name: provider.capability(name) for name in
                              ('issues', 'pull_requests', 'protection')}
        try:
            result['default_branch'] = provider.repository()['default_branch']
        except (ProviderError, KeyError, TypeError):
            result['gaps'].append('default_branch_unknown')
        if any(value != 'supported' for value in result['platform'].values()):
            result['gaps'].append('platform_capability_gap')
    else:
        try:
            result['default_branch'] = git(target, 'symbolic-ref', 'refs/remotes/origin/HEAD').removeprefix('refs/remotes/origin/')
        except ValueError:
            result['gaps'].append('remote_default_branch_unknown')
        result['gaps'].append('platform_NOT_RUN')
    configured = re.search(r'^\s+default_branch:\s*([^\s#]+)', text, re.MULTILINE)
    if configured and result['default_branch'] and configured[1] != result['default_branch']:
        result['gaps'].append('default_branch_mismatch')
    for command in verify:
        if not command:
            raise ValueError('Verification command must be nonempty')
        try:
            # Explicit caller opt-in; no commands from YAML or Issue text are executed.
            run = subprocess.run(command, cwd=target, capture_output=True, timeout=60)
            result['verification'].append({'command': command, 'exit_code': run.returncode})
        except (OSError, subprocess.TimeoutExpired):
            result['verification'].append({'command': command, 'exit_code': None})
    if not verify:
        result['gaps'].append('verification_NOT_RUN')
    result['ok'] = not result['missing'] and not result['gaps'] and all(
        x['exit_code'] == 0 for x in result['verification'])
    return result


def upgrade(target, source=BUNDLE, branch='agent-starter/upgrade'):
    target = Path(target).resolve()
    if git(target, 'rev-parse', '--show-toplevel').lower() != str(target).replace('\\', '/').lower():
        raise ValueError('Target must be the Git repository root')
    if git(target, 'status', '--porcelain'):
        raise ValueError('Upgrade requires a clean working tree')
    git(target, 'check-ref-format', '--branch', branch)
    if branch in ('main', 'master') or branch == git(target, 'branch', '--show-current'):
        raise ValueError('Use a new proposal branch')
    changes = []
    for relative, data in files(source):
        path = destination(target, relative)
        old = path.read_bytes() if path.exists() else b''
        if old != data:
            changes.append({'path': relative.as_posix(), 'change': difference(relative, old, data)})
    report_path = destination(target, Path('.agent-starter-upgrade/proposal.json'))
    if report_path.exists():
        raise ValueError('Existing upgrade report must not be overwritten')
    # Only the proposal report is written; governance and project customizations stay intact.
    result = {'status': 'proposal_only', 'branch': branch,
              'base_sha': git(target, 'rev-parse', 'HEAD'), 'changes': changes}
    git(target, 'switch', '-c', branch)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    return result
