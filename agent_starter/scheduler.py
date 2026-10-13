"""Controller-owned SQLite leases, fencing, event receipts and effect outbox."""
from contextlib import contextmanager
import json
import math
from pathlib import Path
import sqlite3
import time


class LeaseLost(RuntimeError):
    pass


class Scheduler:
    def __init__(self, database, *, max_parallel=2, max_attempts=3, ttl=300, clock=time.time):
        if max_parallel < 1 or max_attempts < 1 or not math.isfinite(ttl) or ttl <= 0:
            raise ValueError('Positive finite budgets are required')
        self.database = str(Path(database).resolve())
        self.clock = clock
        self.max_parallel, self.max_attempts, self.ttl = max_parallel, max_attempts, ttl
        policy = json.dumps([max_parallel, max_attempts, ttl])
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS policy (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO policy VALUES (1, ?)', (policy,))
            if db.execute('SELECT value FROM policy WHERE id=1').fetchone()['value'] != policy:
                raise ValueError('Scheduler clients must use the stored policy')
            db.execute('''CREATE TABLE IF NOT EXISTS tasks (
                task TEXT PRIMARY KEY, revision INTEGER NOT NULL, is_open INTEGER NOT NULL,
                state TEXT NOT NULL, owner TEXT, generation INTEGER NOT NULL DEFAULT 0,
                expires REAL NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0,
                reason TEXT NOT NULL DEFAULT '')''')
            db.execute('CREATE TABLE IF NOT EXISTS receipts (event TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            db.execute('''CREATE TABLE IF NOT EXISTS effects (
                task TEXT, key TEXT, generation INTEGER NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(task, key))''')
            db.execute('''CREATE TABLE IF NOT EXISTS audit (
                task TEXT, actor TEXT, reason TEXT, observed REAL)''')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def now(self):
        value = self.clock()
        if not math.isfinite(value):
            raise ValueError('Invalid clock')
        return value

    def event(self, task, event_id, revision, is_open):
        """Canonical snapshot supplied by a trusted reconciler, NOT raw webhook state."""
        if not task or not event_id or type(revision) is not int or revision < 0 or type(is_open) is not bool:
            raise ValueError('Invalid canonical event')
        payload = json.dumps([task, revision, is_open])
        with self.transaction() as db:
            old = db.execute('SELECT payload FROM receipts WHERE event=?', (event_id,)).fetchone()
            if old:
                if old['payload'] != payload:
                    raise ValueError('Delivery identifier collision')
                return 'duplicate'
            db.execute('INSERT INTO receipts VALUES (?, ?)', (event_id, payload))
            row = db.execute('SELECT * FROM tasks WHERE task=?', (task,)).fetchone()
            if row and revision <= row['revision']:
                return 'out_of_order'
            if not row:
                db.execute('INSERT INTO tasks(task, revision, is_open, state) VALUES (?, ?, ?, ?)',
                           (task, revision, int(is_open), 'ready' if is_open else 'done'))
            elif not is_open or not row['is_open']:
                # Closing/reopening revokes the prior writer immediately.
                state = 'blocked' if row['state'] == 'blocked' else ('ready' if is_open else 'done')
                db.execute('''UPDATE tasks SET revision=?, is_open=?, state=?, owner=NULL,
                    expires=0, generation=generation+1 WHERE task=?''',
                    (revision, int(is_open), state, task))
            else:
                db.execute('UPDATE tasks SET revision=? WHERE task=?', (revision, task))
            return 'applied'

    def claim(self, task, owner):
        if not owner:
            raise ValueError('Logical owner identity is required')
        with self.transaction() as db:
            now = self.now()
            row = db.execute('SELECT * FROM tasks WHERE task=?', (task,)).fetchone()
            if not row:
                return {'status': 'unknown_task'}
            if row['state'] == 'leased':
                if row['expires'] <= now:
                    return {'status': 'recovery_required'}
                if row['owner'] == owner:
                    return {**dict(row), 'status': 'leased'}
                return {'status': 'busy'}
            if row['state'] != 'ready':
                return {'status': row['state']}
            if row['attempts'] >= self.max_attempts:
                db.execute("UPDATE tasks SET state='blocked', reason='retry_budget' WHERE task=?", (task,))
                return {'status': 'blocked'}
            active = db.execute("SELECT COUNT(*) FROM tasks WHERE state='leased' AND expires>?", (now,)).fetchone()[0]
            if active >= self.max_parallel:
                return {'status': 'concurrency_limit'}
            db.execute('''UPDATE tasks SET state='leased', owner=?, generation=generation+1,
                expires=?, attempts=attempts+1, reason='' WHERE task=?''', (owner, now + self.ttl, task))
            return {**dict(db.execute('SELECT * FROM tasks WHERE task=?', (task,)).fetchone()), 'status': 'leased'}

    def _owned(self, db, task, owner, generation):
        row = db.execute('SELECT * FROM tasks WHERE task=?', (task,)).fetchone()
        if not row or row['state'] != 'leased' or row['owner'] != owner or row['generation'] != generation or row['expires'] <= self.now():
            raise LeaseLost('Lease is expired, revoked or owned by another writer')
        return row

    def renew(self, task, owner, generation):
        with self.transaction() as db:
            self._owned(db, task, owner, generation)
            db.execute('UPDATE tasks SET expires=? WHERE task=?', (self.now() + self.ttl, task))

    def effect(self, task, owner, generation, key, payload):
        """Atomically queue one intent per idempotency key. No external write is made."""
        if not key:
            raise ValueError('Idempotency key required')
        data = json.dumps(payload, sort_keys=True, allow_nan=False)
        with self.transaction() as db:
            self._owned(db, task, owner, generation)
            old = db.execute('SELECT payload FROM effects WHERE task=? AND key=?', (task, key)).fetchone()
            if old:
                if old['payload'] != data:
                    raise ValueError('Idempotency key reused with another payload')
                return 'duplicate'
            db.execute('INSERT INTO effects VALUES (?, ?, ?, ?)', (task, key, generation, data))
            return 'queued'

    def finish(self, task, owner, generation, *, success):
        if type(success) is not bool:
            raise ValueError('Completion must be a boolean')
        with self.transaction() as db:
            row = self._owned(db, task, owner, generation)
            state = 'done' if success else ('blocked' if row['attempts'] >= self.max_attempts else 'ready')
            db.execute('UPDATE tasks SET state=?, owner=NULL, expires=0 WHERE task=?', (state, task))

    def recover(self, task, generation, observations, observed_at):
        """Only fresh, complete controller reconciliation can release an expired lease."""
        expected = {'branch', 'pull_request', 'process', 'verification'}
        if set(observations) != expected or any(type(value) is not bool for value in observations.values()):
            raise ValueError('Reconcile branch, PR, process and verification before takeover')
        with self.transaction() as db:
            now = self.now()
            if not math.isfinite(observed_at) or not 0 <= now - observed_at <= 30:
                raise ValueError('Recovery observation must be fresh')
            row = db.execute('SELECT * FROM tasks WHERE task=?', (task,)).fetchone()
            if not row or row['state'] != 'leased' or row['generation'] != generation or row['expires'] > now:
                raise LeaseLost('Recovery no longer matches the expired lease')
            state = 'blocked' if any(observations.values()) else 'ready'
            db.execute('''UPDATE tasks SET state=?, owner=NULL, expires=0, generation=generation+1,
                reason=? WHERE task=?''', (state, 'recovery_artifacts' if state == 'blocked' else '', task))
            return state

    def block(self, task, actor, reason):
        if not actor or not reason:
            raise ValueError('Operator identity and reason required')
        with self.transaction() as db:
            db.execute("UPDATE tasks SET state='blocked', owner=NULL, expires=0, generation=generation+1, reason=? WHERE task=?", (reason, task))
            db.execute('INSERT INTO audit VALUES (?, ?, ?, ?)', (task, actor, reason, self.now()))

    def unblock(self, task, actor, reason, *, reset_budget=False):
        if not actor or not reason:
            raise ValueError('Operator identity and reconciliation reason required')
        with self.transaction() as db:
            row = db.execute('SELECT * FROM tasks WHERE task=?', (task,)).fetchone()
            if not row or row['state'] != 'blocked' or not row['is_open']:
                raise ValueError('Only an open blocked task may be resumed')
            db.execute("UPDATE tasks SET state='ready', reason='', attempts=? WHERE task=?",
                       (0 if reset_budget else row['attempts'], task))
            db.execute('INSERT INTO audit VALUES (?, ?, ?, ?)', (task, actor, reason, self.now()))
