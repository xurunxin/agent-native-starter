import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from agent_starter.provider import Provider, Response
from agent_starter.recovery import ReadOnlyRecoveryCollector, process_identity
from agent_starter.scheduler import Scheduler


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runs = self.root / 'runs'
        self.runs.mkdir()
        self.now = 1000
        self.store = Scheduler(self.root / 'state.db', ttl=10, clock=lambda: self.now)
        self.store.event('o/r#1', 'event', 1, True)
        self.lease = self.store.claim('o/r#1', 'worker')
        self.binding = self.store.bind_execution('o/r#1', 'worker', self.lease['generation'],
            repository='o/r', api_url='https://host.test/api', branch='task/1', commit='a'*40,
            run_id='run-1', runs_root=self.runs, pid=4321, probe=lambda _: 'original-start')
        self.now += 11
        self.branches, self.prs, self.statuses, self.checks = [], [], [], []
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def provider(self):
        def transport(url, headers):
            self.calls.append(url)
            if url.endswith('/repos/o/r'):
                data = {'full_name': 'o/r', 'default_branch': 'main'}
            elif '/branches?' in url:
                data = self.branches
            elif '/pulls?' in url:
                data = self.prs
            elif '/check-runs?' in url:
                data = {'check_runs': self.checks}
            elif '/statuses?' in url:
                data = self.statuses
            else:
                return Response(403, None, {})
            return Response(200, data, {})
        return Provider('github', 'https://host.test/api', 'o/r', transport=transport)

    def collector(self, probe=lambda _: None):
        return ReadOnlyRecoveryCollector(self.provider(), self.runs, process_probe=probe, clock=lambda: self.now)

    def test_actual_provider_and_filesystem_absences_release_bound_execution(self):
        self.assertEqual(self.store.recover('o/r#1', self.lease['generation'], self.collector()), 'ready')
        self.assertTrue(any('/check-runs?' in u for u in self.calls))
        self.assertTrue(any('/branches?' in u for u in self.calls))

    def test_branch_pr_process_and_remote_checks_each_block(self):
        for component in ('branch', 'pr', 'process', 'checks'):
            with self.subTest(component=component):
                collector = self.collector(lambda _: 'original-start' if component == 'process' else None)
                self.branches = [{'name': 'task/1', 'commit': {'sha': 'a'*40}}] if component == 'branch' else []
                self.prs = [{'number': 3, 'head': {'ref': 'task/1', 'sha': 'a'*40,
                                                'repo': {'full_name': 'o/r'}}}] if component == 'pr' else []
                self.checks = [{'id': 22, 'head_sha': 'a'*40, 'status': 'completed'}] if component == 'checks' else []
                report = collector.collect(self.binding)
                self.assertTrue(any(x['state'] == 'present' for x in report['observations'].values()))
        self.assertEqual(self.store.recover('o/r#1', self.lease['generation'], self.collector()), 'blocked')

    def test_verified_artifact_bound_to_run_commit_and_generation(self):
        run = self.runs / 'run-1'
        run.mkdir()
        (run / 'result.txt').write_bytes(b'test evidence')
        record = {key: self.binding[key] for key in ('repository', 'api_url', 'branch', 'commit', 'run_id', 'generation')}
        record['artifacts'] = [{'path': 'result.txt', 'sha256': hashlib.sha256(b'test evidence').hexdigest()}]
        (run / 'verification.json').write_text(json.dumps(record), encoding='utf-8')
        report = self.collector().collect(self.binding)
        self.assertEqual(report['observations']['verification']['state'], 'present')
        record['commit'] = 'b'*40
        (run / 'verification.json').write_text(json.dumps(record), encoding='utf-8')
        self.assertEqual(self.collector().collect(self.binding)['observations']['verification']['state'], 'unknown')
        self.assertEqual(self.store.recover('o/r#1', self.lease['generation'], self.collector()), 'blocked')

    def test_identity_mismatch_denial_and_unbound_boolean_input_never_release(self):
        bad = dict(self.binding, repository='another/repo')
        report = self.collector().collect(bad)
        self.assertTrue(all(x['state'] == 'unknown' for x in report['observations'].values()))
        denied = Provider('github', 'https://host.test/api', 'o/r', transport=lambda *_: Response(403, None, {}))
        collector = ReadOnlyRecoveryCollector(denied, self.runs, clock=lambda: self.now)
        self.assertEqual(self.store.recover('o/r#1', self.lease['generation'], collector), 'blocked')
        with self.assertRaises(ValueError):
            self.store.recover('o/r#1', self.lease['generation'], dict(branch=False, pull_request=False))

    def test_pid_reuse_does_not_confuse_original_writer(self):
        report = self.collector(lambda _: 'different-start').collect(self.binding)
        self.assertEqual(report['observations']['process']['state'], 'absent')
        self.assertTrue(report['observations']['process']['pid_reused'])

    def test_unknown_execution_and_concurrent_revocation_are_not_replayed(self):
        self.store.event('o/r#2', 'another', 1, True)
        lease = self.store.claim('o/r#2', 'unregistered')
        self.now += 11
        with self.assertRaises(ValueError):
            self.store.recover('o/r#2', lease['generation'], self.collector())
        self.assertEqual(self.store.claim('o/r#2', 'new')['status'], 'recovery_required')
        def revoke(_):
            self.store.block('o/r#1', 'maintainer', 'stop during source collection')
            return None
        from agent_starter.scheduler import LeaseLost
        with self.assertRaises(LeaseLost):
            self.store.recover('o/r#1', self.lease['generation'], self.collector(revoke))
        self.assertEqual(self.store.claim('o/r#1', 'new')['status'], 'blocked')

    def test_artifact_tampering_and_remote_commit_mismatch_are_unknown(self):
        self.checks = [{'id': 22, 'head_sha': 'b'*40}]
        self.assertEqual(self.collector().collect(self.binding)['observations']['verification']['state'], 'unknown')
        self.checks = []
        run = self.runs / 'run-1'
        run.mkdir()
        (run / 'result.txt').write_bytes(b'tampered')
        record = {k: self.binding[k] for k in ('repository', 'api_url', 'branch', 'commit', 'run_id', 'generation')}
        record['artifacts'] = [{'path': 'result.txt', 'sha256': hashlib.sha256(b'original').hexdigest()}]
        (run / 'verification.json').write_text(json.dumps(record), encoding='utf-8')
        self.assertEqual(self.collector().collect(self.binding)['observations']['verification']['state'], 'unknown')

    def test_large_artifact_is_unknown_without_unbounded_reads(self):
        run = self.runs / 'run-1'
        run.mkdir()
        artifact = run / 'oversized.txt'
        with artifact.open('wb') as stream:
            stream.truncate(64 * 1024 * 1024 + 1)  # Sparse file, no bulk allocation.
        record = {k: self.binding[k] for k in ('repository', 'api_url', 'branch', 'commit', 'run_id', 'generation')}
        record['artifacts'] = [{'path': 'oversized.txt', 'sha256': '0'*64}]
        (run / 'verification.json').write_text(json.dumps(record), encoding='utf-8')
        report = self.collector().collect(self.binding)
        self.assertEqual(report['observations']['verification']['state'], 'unknown')

    def test_real_child_process_identity_is_read_only(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(15)'])
        try:
            first = process_identity(child.pid)
            self.assertIsInstance(first, str)
            self.assertEqual(process_identity(child.pid), first)
            self.assertIsNone(child.poll())
        finally:
            child.terminate()
            child.wait(timeout=10)
        self.assertIsNone(process_identity(child.pid))


if __name__ == '__main__':
    unittest.main()
