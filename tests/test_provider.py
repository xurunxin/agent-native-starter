import unittest

from agent_starter.provider import Provider, ProviderError, Response


class Fake:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers):
        self.calls.append((url, headers))
        return self.responses.pop(0)


class ProviderTests(unittest.TestCase):
    def make(self, kind, *responses, **kwargs):
        fake = Fake(*responses)
        return Provider(kind, 'https://host.test/api', 'o/r', transport=fake,
                        sleep=lambda _: None, **kwargs), fake

    def test_both_pagination_and_issue_pr_filter(self):
        for kind in ('github', 'gitea'):
            with self.subTest(kind=kind):
                p, f = self.make(kind,
                    Response(200, [{'number': 1}, {'number': 9, 'pull_request': {}}],
                             {'link': '<https://host.test/api/repos/o/r/issues?page=2>; rel="next"'}),
                    Response(200, [{'number': 2}], {}))
                self.assertEqual([x['number'] for x in p.issues()], [1, 2])
                self.assertEqual(len(f.calls), 2)

    def test_retry_budget_rate_limit_and_server_error(self):
        for kind in ('github', 'gitea'):
            p, f = self.make(kind, Response(429, {}, {'retry-after': '0'}),
                            Response(503, {}, {}), Response(200, {'default_branch': 'main'}, {}))
            self.assertEqual(p.repository()['default_branch'], 'main')
            self.assertEqual(len(f.calls), 3)
            p, f = self.make(kind, *[Response(429, {}, {})] * 3)
            with self.assertRaises(ProviderError) as ctx:
                p.repository()
            self.assertEqual(ctx.exception.code, 'rate_limited')
            self.assertEqual(len(f.calls), 3)

    def test_denied_and_missing_are_not_supported(self):
        for kind in ('github', 'gitea'):
            p, _ = self.make(kind, Response(200, {'default_branch': 'main'}, {}),
                            Response(403, {'message': 'secret'}, {}))
            self.assertEqual(p.capability('protection'), 'denied')
            p, _ = self.make(kind, Response(200, {'default_branch': 'main'}, {}), Response(404, {}, {}))
            self.assertEqual(p.capability('protection'), 'unknown')

    def test_read_interface_routes(self):
        for kind in ('github', 'gitea'):
            for method, arg, suffix in [('issue', 3, '/issues/3'), ('pull_request', 4, '/pulls/4'),
                                        ('branch', 'feature/a', '/branches/feature%2Fa'),
                                        ('protection', 'main', '/branches/main/protection' if kind == 'github'
                                         else '/branch_protections/main')]:
                p, f = self.make(kind, Response(200, {}, {}))
                getattr(p, method)(arg)
                self.assertTrue(f.calls[0][0].endswith(suffix))
            p, f = self.make(kind, Response(200, [], {}))
            p.comments(3)
            self.assertIn('/issues/3/comments?', f.calls[0][0])
            p, f = self.make(kind, Response(200, [], {}))
            self.assertEqual(p.statuses('abc'), [])

    def test_writes_explicitly_unimplemented_and_no_retry(self):
        for kind in ('github', 'gitea'):
            p, f = self.make(kind)
            for action in ('create_issue', 'create_pull_request', 'comment', 'set_status',
                           'create_branch', 'set_protection'):
                with self.assertRaises(ProviderError) as ctx:
                    p.mutate(action, {'idempotency_key': 'same'})
                self.assertEqual(ctx.exception.code, 'not_implemented')
            self.assertEqual(f.calls, [])

    def test_no_credentials_in_untrusted_execution(self):
        with self.assertRaises(ValueError):
            Provider('github', 'https://host.test', 'o/r', token='secret', trusted=False)

    def test_pagination_rejects_foreign_origin_and_cycles(self):
        for link in ('https://evil.test/page', 'https://host.test/api/repos/o/r/issues?state=open&per_page=100'):
            p, _ = self.make('github', Response(200, [], {'link': f'<{link}>; rel="next"'}))
            with self.assertRaises(ProviderError):
                p.issues()

    def test_gitea_count_header(self):
        p, f = self.make('gitea', Response(200, [{'number': 1}], {'x-pagecount': '2'}),
                        Response(200, [{'number': 2}], {'x-pagecount': '2'}))
        self.assertEqual(len(p.issues()), 2)
        self.assertIn('page=2', f.calls[-1][0])

    def test_github_checks_wrapper_paginates_and_gitea_is_explicit(self):
        p, f = self.make('github', Response(200, {'check_runs': [{'id': 1}]},
            {'link': '<https://host.test/api/repos/o/r/commits/abc/check-runs?page=2>; rel="next"'}),
            Response(200, {'check_runs': [{'id': 2}]}, {}))
        self.assertEqual([r['id'] for r in p.checks('abc')], [1, 2])
        p, f = self.make('gitea')
        with self.assertRaises(ProviderError) as context:
            p.checks('abc')
        self.assertEqual(context.exception.code, 'not_implemented')
        self.assertEqual(f.calls, [])

    def test_bad_payload_and_transport_redacted(self):
        p, _ = self.make('github', Response(200, {'not': 'a list'}, {}))
        with self.assertRaises(ProviderError):
            p.issues()
        def fail(*_):
            raise OSError('secret URL or token')
        p = Provider('github', 'https://host.test', 'o/r', transport=fail, sleep=lambda _: None)
        with self.assertRaises(ProviderError) as ctx:
            p.repository()
        self.assertNotIn('secret', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
