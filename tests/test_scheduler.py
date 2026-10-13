from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest
from pathlib import Path

from agent_starter.scheduler import Scheduler, LeaseLost


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.now = 1000
        self.db = Path(self.tmp.name) / 'state.db'
        self.scheduler = Scheduler(self.db, max_parallel=2, max_attempts=2, ttl=10,
                                   clock=lambda: self.now)
        self.scheduler.event('o/r#1', 'event1', 1, True)

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
        lease = self.scheduler.claim('o/r#1', 'old')
        self.now += 11
        self.assertEqual(self.scheduler.claim('o/r#1', 'new')['status'], 'recovery_required')
        with self.assertRaises(LeaseLost):
            self.scheduler.renew('o/r#1', 'old', lease['generation'])
        observation = {name: False for name in ('branch', 'pull_request', 'process', 'verification')}
        with self.assertRaises(ValueError):
            self.scheduler.recover('o/r#1', lease['generation'], {}, self.now)
        self.assertEqual(self.scheduler.recover('o/r#1', lease['generation'], observation, self.now), 'ready')
        new = self.scheduler.claim('o/r#1', 'new')
        self.assertGreater(new['generation'], lease['generation'])
        with self.assertRaises(LeaseLost):
            self.scheduler.effect('o/r#1', 'old', lease['generation'], 'write1', {'op': 'comment'})

    def test_artifacts_block_recovery_and_retry_budget(self):
        lease = self.scheduler.claim('o/r#1', 'worker')
        self.now += 11
        evidence = dict(branch=True, pull_request=False, process=False, verification=False)
        self.assertEqual(self.scheduler.recover('o/r#1', lease['generation'], evidence, self.now), 'blocked')
        self.assertEqual(self.scheduler.claim('o/r#1', 'other')['status'], 'blocked')
        self.scheduler.unblock('o/r#1', 'maintainer', 'Reviewed branch and stopped process')
        lease = self.scheduler.claim('o/r#1', 'worker')
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
        lease = self.scheduler.claim('o/r#1', 'worker')
        self.now += 11
        with self.assertRaises(ValueError):
            self.scheduler.recover('o/r#1', lease['generation'],
                dict(branch=False, pull_request=False, process=False, verification=False), self.now - 31)

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
