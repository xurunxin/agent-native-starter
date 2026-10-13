"""Read-only, execution-bound recovery evidence; unknown sources never mean absent."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from .provider import ProviderError


FIELDS = ('repository', 'api_url', 'branch', 'commit', 'run_id', 'generation')


def process_identity(pid):
    """Return start identity or confirmed absence. Never use os.kill on Windows."""
    if type(pid) is not int or pid <= 0:
        raise ValueError('Invalid registered process PID')
    if os.name == 'nt':
        script = ('try { $p = Get-Process -Id ' + str(pid) + ' -ErrorAction Stop; '
                  '[string]$p.StartTime.ToUniversalTime().Ticks } catch { '
                  "if ($_.FullyQualifiedErrorId -like 'NoProcessFoundForGivenId*') { 'ABSENT' } else { exit 2 } }")
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, text=True, timeout=10,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        value = result.stdout.strip()
        if result.returncode:
            raise ValueError('Process identity query denied or failed')
        if value == 'ABSENT':
            return None
        if not value.isdigit():
            raise ValueError('Process start identity is unavailable')
        return 'windows-ticks:' + value
    if Path('/proc').is_dir():
        try:
            stat = Path(f'/proc/{pid}/stat').read_text()
        except FileNotFoundError:
            return None
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        return 'linux-start:' + boot + ':' + stat.rpartition(')')[2].split()[19]
    raise ValueError('Native process identity is unsupported on this host')


def safe_path(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Artifact path escapes trusted run directory')
    path = root / relative
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink() or part.is_junction():
            raise ValueError('Recovery artifact links are prohibited')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Artifact outside trusted run directory')
    return path


class ReadOnlyRecoveryCollector:
    def __init__(self, provider, runs_root, *, process_probe=process_identity, clock=time.time):
        self.provider = provider
        self.runs_root = Path(runs_root).resolve()
        self.process_probe, self.clock = process_probe, clock

    def _local_verification(self, binding):
        if str(self.runs_root) != binding['runs_root'] or not self.runs_root.is_dir() or self.runs_root.is_symlink() or self.runs_root.is_junction() or self.runs_root.resolve() != self.runs_root:
            raise ValueError('Trusted run registry root is unavailable or mismatched')
        run = safe_path(self.runs_root, binding['run_id'])
        if not run.exists():
            return {'state': 'absent', 'local_run': binding['run_id']}
        if not run.is_dir():
            raise ValueError('Invalid run registry entry')
        manifest = safe_path(run, 'verification.json')
        if not manifest.exists():
            return {'state': 'present' if any(run.iterdir()) else 'absent', 'local_run': binding['run_id'],
                    'manifest': 'missing'}
        if manifest.stat().st_size > 1024 * 1024:
            raise ValueError('Verification manifest exceeds budget')
        manifest_bytes = manifest.read_bytes()
        record = json.loads(manifest_bytes)
        if not isinstance(record, dict) or any(record.get(k) != binding[k] for k in FIELDS):
            raise ValueError('Verification manifest identity mismatch')
        artifacts = record.get('artifacts')
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError('Verification artifacts missing')
        verified = []
        for artifact in artifacts:
            expected = artifact['sha256']
            path = safe_path(run, artifact['path'])
            if not re.fullmatch(r'[0-9a-f]{64}', expected) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('Verification artifact digest mismatch')
            verified.append({'path': artifact['path'], 'sha256': expected})
        return {'state': 'present', 'local_run': binding['run_id'], 'artifacts': verified,
                'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest()}

    def collect(self, binding):
        started = self.clock()
        observations = {}
        def observe(name, callback):
            try:
                observations[name] = callback()
            except (ProviderError, OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, subprocess.TimeoutExpired):
                observations[name] = {'state': 'unknown', 'reason': 'source_failed_or_identity_mismatch'}
        try:
            repository = self.provider.repository()
            if repository['full_name'].casefold() != binding['repository'].casefold() or self.provider.api_url != binding['api_url']:
                raise ValueError('Repository/API origin mismatch')
        except (ProviderError, KeyError, TypeError, ValueError, AttributeError):
            observations = {k: {'state': 'unknown', 'reason': 'repository_identity_unverified'}
                            for k in ('branch', 'pull_request', 'process', 'verification')}
            return {'binding': binding, 'started_at': started, 'observed_at': self.clock(), 'observations': observations}
        def branch():
            branches = self.provider.branches()
            if any(not isinstance(b.get('name'), str) for b in branches):
                raise ValueError('Incomplete branch enumeration')
            matches = [b for b in branches if b['name'] == binding['branch']]
            if not matches:
                return {'state': 'absent', 'ref': binding['branch']}
            commit = matches[0].get('commit', {})
            head = commit.get('sha', commit.get('id'))
            if not head:
                raise ValueError('Branch commit identity unavailable')
            return {'state': 'present', 'ref': binding['branch'], 'head_sha': head,
                    'expected_commit_matches': head == binding['commit']}
        def prs():
            matches = []
            for pr in self.provider.pull_requests('all'):
                head = pr['head']
                if head['ref'] != binding['branch']:
                    continue
                # Deleted/hidden head repository is ambiguous, never evidence of absence.
                if head['repo']['full_name'].casefold() == binding['repository'].casefold():
                    matches.append({'number': pr['number'], 'head_sha': head['sha']})
            return {'state': 'present' if matches else 'absent', 'pull_requests': matches}
        def process():
            current = self.process_probe(binding['pid'])
            if current is not None and (not isinstance(current, str) or not current):
                raise ValueError('Process observation is not a verified native identity')
            same = current == binding['process_start']
            return {'state': 'present' if same else 'absent', 'pid': binding['pid'],
                    'registered_start': binding['process_start'], 'observed_start': current,
                    'pid_reused': current is not None and not same}
        def verification():
            local = self._local_verification(binding)
            statuses = self.provider.statuses(binding['commit'])
            checks = self.provider.checks(binding['commit'])
            if any(c.get('head_sha') != binding['commit'] or type(c.get('id')) is not int for c in checks):
                raise ValueError('Remote check/run commit identity mismatch')
            remote = {'commit': binding['commit'], 'status_ids': [s['id'] for s in statuses],
                      'check_run_ids': [c['id'] for c in checks]}
            return {**local, 'state': 'present' if statuses or checks or local['state'] == 'present' else 'absent',
                    'remote': remote}
        observe('branch', branch)
        observe('pull_request', prs)
        observe('process', process)
        observe('verification', verification)
        return {'binding': binding, 'started_at': started, 'observed_at': self.clock(), 'observations': observations}
