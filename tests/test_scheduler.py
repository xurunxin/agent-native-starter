from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest
from pathlib import Path

from agent_starter.scheduler import Scheduler, LeaseLost
from agent_starter.provider import Provider, Response
from agent_starter.recovery import ReadOnlyRecoveryCollector


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.now = 1000
        self.db = Path(self.tmp.name) / 'state.db'
        self.scheduler = Scheduler(self.db, max_parallel=2, max_attempts=2, ttl=10,
                                   clock=lambda: self.now)
        self.scheduler.event('o/r#1', 'event1', 1, True)
        self.runs = Path(self.tmp.name) / 'runs'
        self.runs.mkdir()
        self.branches = []

    def bound_claim(self, owner):
        lease = self.scheduler.claim('o/r#1', owner)
        self.scheduler.bind_execution('o/r#1', owner, lease['generation'],
            repository='o/r', api_url='https://host.test', branch='task/1', commit='a'*40,
            run_id='run-' + str(lease['generation']), runs_root=self.runs, pid=1234,
            probe=lambda _: 'original-start')
        return lease

    def collector(self, clock=None):
        def transport(url, _):
            if url.endswith('/repos/o/r'):
                return Response(200, {'full_name': 'o/r'}, {})
            if '/branches?' in url:
                return Response(200, self.branches, {})
            if '/check-runs?' in url:
                return Response(200, {'check_runs': []}, {})
            return Response(200, [], {})
        return ReadOnlyRecoveryCollector(Provider('github', 'https://host.test', 'o/r', transport=transport),
            self.runs, process_probe=lambda _: None, clock=clock or (lambda: self.now))

    def tearDown(self):
        self.tmp.cleanup()

    def test_concurrent_claim_has_one_owner(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda n: self.scheduler.claim('o/r#1', f'worker{n}'), range(8)))
        self.assertEqual(sum(x['status'] == 'leased' for x in results), 1)

    def test_global_concurrency_budget(self):
        for n in range(2, 9):
            self.scheduler.event(f'o/r#{n}', f'event{n}', 1, True)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda n: self.scheduler.claim(f'o/r#{n}', f'worker{n}'), range(1, 9)))
        self.assertEqual(sum(x['status'] == 'leased' for x in results), 2)

    def test_duplicate_and_out_of_order_events_do_not_resurrect_closed_task(self):
        self.assertEqual(self.scheduler.event('o/r#1', 'event1', 1, True), 'duplicate')
        self.assertEqual(self.scheduler.event('o/r#1', 'event2', 3, False), 'applied')
        self.assertEqual(self.scheduler.event('o/r#1', 'event3', 2, True), 'out_of_order')
        self.assertEqual(self.scheduler.claim('o/r#1', 'worker')['status'], 'done')
        with self.assertRaises(ValueError):
            self.scheduler.event('o/r#2', 'event1', 1, True)

    def test_expired_lease_needs_fresh_reconciliation_and_fences_old_owner(self):
        lease = self.bound_claim('old')
        self.now += 11
        self.assertEqual(self.scheduler.claim('o/r#1', 'new')['status'], 'recovery_required')
        with self.assertRaises(LeaseLost):
            self.scheduler.renew('o/r#1', 'old', lease['generation'])
        with self.assertRaises(ValueError):
            self.scheduler.recover('o/r#1', lease['generation'], {})
        self.assertEqual(self.scheduler.recover('o/r#1', lease['generation'], self.collector()), 'ready')
        new = self.scheduler.claim('o/r#1', 'new')
        self.assertGreater(new['generation'], lease['generation'])
        with self.assertRaises(LeaseLost):
            self.scheduler.effect('o/r#1', 'old', lease['generation'], 'write1', {'op': 'comment'})

    def test_artifacts_block_recovery_and_retry_budget(self):
        lease = self.bound_claim('worker')
        self.now += 11
        self.branches = [{'name': 'task/1', 'commit': {'sha': 'a'*40}}]
        self.assertEqual(self.scheduler.recover('o/r#1', lease['generation'], self.collector()), 'blocked')
        self.assertEqual(self.scheduler.claim('o/r#1', 'other')['status'], 'blocked')
        self.scheduler.unblock('o/r#1', 'maintainer', 'Reviewed branch and stopped process')
        lease = self.bound_claim('worker')
        self.scheduler.finish('o/r#1', 'worker', lease['generation'], success=False)
        self.assertEqual(self.scheduler.claim('o/r#1', 'worker')['status'], 'blocked')

    def test_idempotent_effect_and_renewal(self):
        lease = self.scheduler.claim('o/r#1', 'worker')
        again = self.scheduler.claim('o/r#1', 'worker')
        self.assertEqual(again['generation'], lease['generation'])
        self.assertEqual(again['attempts'], 1)
        self.now += 5
        self.scheduler.renew('o/r#1', 'worker', lease['generation'])
        data = {'op': 'draft_pr'}
        self.assertEqual(self.scheduler.effect('o/r#1', 'worker', lease['generation'], 'pr1', data), 'queued')
        self.assertEqual(self.scheduler.effect('o/r#1', 'worker', lease['generation'], 'pr1', data), 'duplicate')
        with self.assertRaises(ValueError):
            self.scheduler.effect('o/r#1', 'worker', lease['generation'], 'pr1', {'op': 'different'})

    def test_policy_and_recovery_observation_must_match(self):
        with self.assertRaises(ValueError):
            Scheduler(self.db, max_parallel=99)
        lease = self.bound_claim('worker')
        self.now += 11
        with self.assertRaises(ValueError):
            self.scheduler.recover('o/r#1', lease['generation'],
                                   self.collector(clock=lambda: self.now - 31))

    def test_manual_block_survives_issue_close_and_reopen(self):
        lease = self.scheduler.claim('o/r#1', 'worker')
        self.scheduler.block('o/r#1', 'maintainer', 'needs authorization')
        with self.assertRaises(LeaseLost):
            self.scheduler.renew('o/r#1', 'worker', lease['generation'])
        self.scheduler.event('o/r#1', 'close', 2, False)
        self.scheduler.event('o/r#1', 'reopen', 3, True)
        self.assertEqual(self.scheduler.claim('o/r#1', 'worker')['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
